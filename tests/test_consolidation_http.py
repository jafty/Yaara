"""Persisted target admission, retry safety and the narrow busy-target disclosure."""

import uuid
from copy import deepcopy

import pytest
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.db import connection
from django.test import Client
from django.urls import reverse

from simulation import engine, services
from simulation.models import CommandReceipt, Participant, TargetEngagement
from simulation.rules import RuleError
from tests.cases import case
from tests.test_application import concurrent_calls

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]
REQ = "Owner November 1: strategy three admits one sealed military order per target"
BUSY = "Une autre expédition est déjà engagée vers cette cité. Aucun moyen n’a été réservé."
COMBINATIONS = [
    pytest.param("raid", "raid", id="raid-raid"),
    pytest.param("raid", "capture", id="raid-capture"),
    pytest.param("capture", "raid", id="capture-raid"),
    pytest.param("capture", "capture", id="capture-capture"),
]


@pytest.fixture
def target_game(user):
    game = services.create_game(
        user, "Consolidation boundary", opponents="passive", strategy_version=3
    )
    game.kind = "multiplayer"
    game.lobby_status = "running"
    for city in game.state["cities"].values():
        city.update(stock=2_400_000, fideles=500)
    # Two different houses have a direct route to the same p2 city.
    game.state["cities"]["c5"]["owner"] = "p3"
    game.save()
    rival = get_user_model().objects.create_user("consolidation-rival")
    Participant.objects.create(game=game, user=rival, actor="p3")
    return game, rival


def military_spec(kind, actor="p1"):
    return {
        "kind": kind,
        "target": "c4",
        "contributions": {"c3" if actor == "p1" else "c5": 50 if kind == "raid" else 80},
    }


def logged_client(user, language="fr"):
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    return client


def preview(client, game, kind, actor="p1"):
    origin = "c3" if actor == "p1" else "c5"
    return client.post(
        reverse("preview", args=[game.pk]),
        {"kind": kind, "target": "c4", f"men_{origin}": 50 if kind == "raid" else 80},
    )


@case("consolidation-target-race", REQ)
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("first_kind,second_kind", COMBINATIONS)
@pytest.mark.parametrize("same_actor", [False, True], ids=["different-houses", "same-house"])
def test_target_race(user, target_game, first_kind, second_kind, same_actor):
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL row locks")
    game, rival = target_game
    second_actor = "p1" if same_actor else "p3"
    results = concurrent_calls(
        [
            lambda: services.confirm(user, game.pk, military_spec(first_kind), uuid.uuid4(), 1),
            lambda: services.confirm(
                user if same_actor else rival,
                game.pk,
                military_spec(second_kind, second_actor),
                uuid.uuid4(),
                1,
            ),
        ]
    )
    errors = [result for result in results if isinstance(result, RuleError)]
    assert len(errors) == 1 and str(errors[0]) == BUSY
    game.refresh_from_db()
    assert len(game.state["orders"]) == 1
    winner = game.state["orders"][0]
    assert winner in results
    assert winner["status"] == "confirmed"
    assert winner["cost"] == (55_000 if winner["kind"] == "raid" else 210_000)
    assert CommandReceipt.objects.filter(game=game).count() == 1
    engagement = TargetEngagement.objects.get(game=game)
    assert (engagement.city_id, engagement.order_id) == ("c4", winner["id"])
    assert all(city["stock"] == 2_400_000 for city in game.state["cities"].values())
    funds, people = engine.reservations(game.state)
    assert sum(funds.values()) == winner["cost"]
    assert sum(people.values()) == (50 if winner["kind"] == "raid" else 80)
    engine.assert_invariants(game.state)


@case("consolidation-stale-target-preview", REQ)
@pytest.mark.django_db
@pytest.mark.parametrize("first_kind,second_kind", COMBINATIONS)
def test_stale_target_preview(user, target_game, first_kind, second_kind):
    game, rival = target_game
    client = logged_client(rival)
    quoted = preview(client, game, second_kind, "p3")
    assert quoted.status_code == 200
    game.refresh_from_db()
    assert not game.state["orders"]
    assert not TargetEngagement.objects.filter(game=game).exists()
    services.confirm(user, game.pk, military_spec(first_kind), uuid.uuid4(), 1)
    game.refresh_from_db()
    before = deepcopy(game.state)
    revision = game.revision
    response = client.post(
        reverse("confirm", args=[game.pk]), {"payload": quoted.context["payload"]}
    )
    assert response.status_code == 302
    assert [str(item) for item in get_messages(response.wsgi_request)] == [BUSY]
    game.refresh_from_db()
    assert game.state == before and game.revision == revision
    assert CommandReceipt.objects.filter(game=game).count() == 1
    assert TargetEngagement.objects.filter(game=game).count() == 1


@case(
    "consolidation-final-busy-disclosure",
    "Owner November 1: only final admission may disclose generic target occupancy",
)
@pytest.mark.django_db
@pytest.mark.parametrize("language", ["fr", "en"])
def test_final_busy_disclosure(user, target_game, language):
    game, rival = target_game
    client = logged_client(rival, language)
    url = reverse("state", args=[game.pk])
    before = client.get(url).json()
    secret_request = uuid.uuid4()
    order = services.confirm(user, game.pk, military_spec("capture"), secret_request, 1)
    # A rival commitment does not change the recipient's state or polling revision.
    assert client.get(url).json() == before
    quoted = preview(client, game, "raid", "p3")
    assert quoted.status_code == 200
    rendered = quoted.content.decode()
    assert order["id"] not in rendered
    assert "cohort_equipment" not in rendered and "combativity" not in rendered
    response = client.post(
        reverse("confirm", args=[game.pk]), {"payload": quoted.context["payload"]}
    )
    expected = (
        BUSY
        if language == "fr"
        else "Another expedition is already committed to this city. No resources have been reserved."
    )
    assert [str(item) for item in get_messages(response.wsgi_request)] == [expected]
    assert client.get(url).json() == before
    assert not game.reports.filter(recipient="p3", kind="order").exists()
    assert CommandReceipt.objects.filter(game=game).count() == 1


@case(
    "consolidation-concurrent-receipt-retry",
    "Owner November 1: duplicate delivery returns its own order before checking the target lock",
)
@pytest.mark.django_db(transaction=True)
def test_concurrent_receipt_retry(user, target_game):
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL row locks")
    game, _ = target_game
    request_id = uuid.uuid4()
    results = concurrent_calls(
        [
            lambda: services.confirm(user, game.pk, military_spec("capture"), request_id, 1),
            lambda: services.confirm(user, game.pk, military_spec("capture"), request_id, 1),
        ]
    )
    assert results[0] == results[1] and not isinstance(results[0], RuleError)
    game.refresh_from_db()
    assert len(game.state["orders"]) == 1
    assert CommandReceipt.objects.filter(game=game).count() == 1
    assert TargetEngagement.objects.filter(game=game).count() == 1
    funds, people = engine.reservations(game.state)
    assert funds["c3"] == 210_000 and people["c3"] == 80
    assert game.state["cities"]["c3"]["stock"] == 2_400_000


@case("consolidation-cancellation-lock-release", REQ)
@pytest.mark.django_db
def test_cancellation_releases_lock_and_retry_does_not_reacquire(user, target_game):
    game, rival = target_game
    request_id = uuid.uuid4()
    first = services.confirm(user, game.pk, military_spec("capture"), request_id, 1)
    services.cancel(user, game.pk, first["id"])
    assert not TargetEngagement.objects.filter(game=game).exists()
    second = services.confirm(rival, game.pk, military_spec("raid", "p3"), uuid.uuid4(), 1)
    replay = services.confirm(user, game.pk, military_spec("capture"), request_id, 1, -1)
    assert replay["status"] == "cancelled"
    assert TargetEngagement.objects.get(game=game).order_id == second["id"]
    assert CommandReceipt.objects.filter(game=game).count() == 2


@case("consolidation-invalidation-lock-release", REQ)
@pytest.mark.django_db
def test_invalidated_departure_releases_persisted_lock(user, target_game):
    game, rival = target_game
    first = services.confirm(user, game.pk, military_spec("capture"), uuid.uuid4(), 1)
    game.refresh_from_db()
    game.state["cities"]["c3"]["owner"] = "p2"
    game.save()
    services.tick(game.pk, 1)
    game.refresh_from_db()
    assert game.state["orders"][0]["id"] == first["id"]
    assert game.state["orders"][0]["status"] == "invalidated"
    assert not TargetEngagement.objects.filter(game=game).exists()
    second = services.confirm(rival, game.pk, military_spec("raid", "p3"), uuid.uuid4(), 2)
    assert TargetEngagement.objects.get(game=game).order_id == second["id"]


@case(
    "consolidation-combat-lock-release",
    "Owner November 1: combat releases the target while returns and occupation remain active",
)
@pytest.mark.django_db
def test_combat_releases_lock_during_occupation(user, target_game):
    game, rival = target_game
    game.state["cities"]["c4"].update(fideles=0, stock=0)
    game.state["cities"]["c6"]["fideles"] = 0
    game.save()
    first = services.confirm(user, game.pk, military_spec("capture"), uuid.uuid4(), 1)
    services.tick(game.pk, 1)
    assert TargetEngagement.objects.get(game=game).order_id == first["id"]
    services.tick(game.pk, 2)
    game.refresh_from_db()
    assert game.state["cities"]["c4"]["owner"] == "p1"
    assert not TargetEngagement.objects.filter(game=game).exists()
    assert any(mission["status"] != "completed" for mission in game.state["expeditions"])
    second = services.confirm(rival, game.pk, military_spec("capture", "p3"), uuid.uuid4(), 3)
    assert TargetEngagement.objects.get(game=game).order_id == second["id"]


@case(
    "consolidation-target-legacy-two",
    "Owner November 1: persisted strategy two retains nonexclusive secret target admission",
)
@pytest.mark.django_db
def test_strategy_two_still_allows_competing_targets(user, target_game):
    game, rival = target_game
    game.state["strategy_version"] = 2
    game.save()
    services.confirm(user, game.pk, military_spec("capture"), uuid.uuid4(), 1)
    services.confirm(rival, game.pk, military_spec("raid", "p3"), uuid.uuid4(), 1)
    game.refresh_from_db()
    assert len(game.state["orders"]) == 2
    assert CommandReceipt.objects.filter(game=game).count() == 2
