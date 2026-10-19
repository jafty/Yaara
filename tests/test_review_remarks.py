"""Owner feedback: recoverable decrees, clear costs and predictable calendar boundaries."""

import re
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest
from django.test import Client
from django.urls import reverse

from simulation import engine, services
from simulation.models import CommandReceipt
from simulation.projections import player_view
from simulation.rules import RuleError
from tests.cases import case


@pytest.mark.logic
@case("remarks-empty-granaries", "Owner: a 30-person raid costs 95000, split exactly by origin")
@pytest.mark.parametrize("stocks", [(0, 0, 0), (31667, 31667, 31666)])
def test_empty_granaries(stocks):
    """Given ten warriors from each city and local stocks of {stocks}.
    When their combined raid is prepared.
    Then the exact 95000-Measure allocation is required without mutating the state.
    """
    state = engine.new_state(opponents="passive")
    for city, stock in zip(("c1", "c2", "c3"), stocks):
        state["cities"][city]["stock"] = stock
    before = deepcopy(state)
    spec = {"kind": "raid", "target": "c4", "contributions": {"c1": 10, "c2": 10, "c3": 10}}
    if stocks[0] == 0:
        with pytest.raises(RuleError, match="Qasr.*31\u202f667"):
            engine.prepare_order(state, "p1", spec, "empty")
    else:
        order = engine.prepare_order(state, "p1", spec, "exact")
        assert order["cost"] == 95000
        assert order["funding"] == {"c1": 31667, "c2": 31667, "c3": 31666}
    assert state == before


@pytest.mark.logic
@case("remarks-frontier-borders", "Owner: every new-world road joins touching city territories")
def test_frontier_borders():
    """Given the twelve-road frontier world with three starting houses.
    When its public city territories are projected.
    Then every saved road joins a shared border and each rival bridge is geographically close.
    """
    state = engine.new_state()
    before = deepcopy(state)
    cities = {city["id"]: city for city in player_view(state, "p1")["cities"]}
    for first, second in state["links"]:
        a, b = cities[first], cities[second]
        points_a = set(a["territory"].split())
        points_b = set(b["territory"].split())
        assert len(points_a & points_b) >= 2, (first, second)
        if a["owner"] != b["owner"]:
            assert (a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2 < 170**2
    assert state == before


@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@case(
    "remarks-failed-preview",
    "Owner: failed decrees return to their action with the selection intact",
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("kind", ["raid", "capture", "storage", "equipment"])
def test_failed_preview(user, language, kind):
    game = services.create_game(user, "Failed order", opponents="passive", forge_version=1)
    for city in game.state["cities"].values():
        city["stock"] = 0
    game.save()
    before = deepcopy(game.state)
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    military = kind in ("raid", "capture")
    spec = (
        {"kind": kind, "target": "c4", "men_c1": 30, "men_c2": 30, "men_c3": 30}
        if military
        else {"kind": kind, "cities": ["c1", "c2"]}
    )
    response = client.post(reverse("preview", args=[game.id]), spec)
    query = parse_qs(urlsplit(response.url).query)
    assert query["tab"] == ["wars" if military else "constructions"]
    assert query["action"] == ["expedition" if military else kind]
    form = client.get(response.url)
    assert form.status_code == 200
    if military:
        html = form.content.decode()
        assert re.search(r'name="men_c1"[^>]*value="30"', html)
        assert form.context["mission_kind"] == kind and form.context["selected"]["id"] == "c4"
    elif kind == "storage":
        assert form.content.decode().count("checked") >= 2
    game.refresh_from_db()
    assert game.state == before and game.revision == 0
    assert not CommandReceipt.objects.filter(game=game).exists()


@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@case("remarks-failed-seal", "Owner: stale confirmation returns to the matching editable form")
@pytest.mark.parametrize("kind", ["raid", "storage"])
def test_failed_seal(user, kind):
    game = services.create_game(user, "Stale", opponents="passive")
    client = Client()
    client.force_login(user)
    spec = (
        {"kind": kind, "cities": ["c1"]}
        if kind == "storage"
        else {"kind": kind, "target": "c4", "men_c1": 30}
    )
    preview = client.post(reverse("preview", args=[game.id]), spec)
    services.confirm(user, game.id, {"kind": "storage", "cities": ["c2"]}, uuid.uuid4(), 1)
    response = client.post(
        reverse("confirm", args=[game.id]), {"payload": preview.context["payload"]}
    )
    query = parse_qs(urlsplit(response.url).query)
    assert query["action"] == ["expedition" if kind == "raid" else kind]
    game.refresh_from_db()
    assert len(game.state["orders"]) == 1


@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@case("remarks-prologue-action-order", "Owner: Continue appears before Begin reign on each leaf")
@pytest.mark.parametrize("page", [1, 2, 3, 4])
def test_prologue_action_order(user, page):
    game = services.create_game(user, "Intro", mode="scheduled", opponents="passive")
    client = Client()
    client.force_login(user)
    html = client.get(
        reverse("game", args=[game.id]), {"tab": "prologue", "page": page}
    ).content.decode()
    assert html.index('class="prologue-navigation"') < html.index(
        f'action="/games/{game.id}/start/"'
    )


@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@case("remarks-report-return", "Owner: every complete report links back to Council")
@pytest.mark.parametrize("language", ["fr", "en"])
def test_report_return(user, language):
    game = services.create_game(user, "Letters", opponents="passive")
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    html = client.get(reverse("game", args=[game.id]), {"tab": "letters"}).content.decode()
    letters = re.findall(r'<article class="letter-entry".*?</article>', html, re.S)
    assert letters
    assert all('href="?tab=domain"' in letter for letter in letters)
    assert ("Retour au conseil" if language == "fr" else "Return to Council") in letters[0]


@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@case(
    "remarks-native-funding",
    "Owner: native expedition retry shows all exact city shares and shortages",
)
def test_native_funding(user):
    game = services.create_game(user, "Empty", opponents="passive")
    for city in game.state["cities"].values():
        city["stock"] = 0
    game.save()
    client = Client()
    client.force_login(user)
    response = client.post(
        reverse("preview", args=[game.id]),
        {
            "kind": "raid",
            "target": "c4",
            "men_c1": 10,
            "men_c2": 10,
            "men_c3": 10,
        },
        follow=True,
    )
    assert response.context["expedition_total"] == 30
    assert response.context["expedition_cost"] == 95000
    assert [city["expedition_charge"] for city in response.context["view"]["owned_cities"]] == [
        31667,
        31667,
        31666,
    ]
    assert all(
        city["expedition_charge"] == city["expedition_shortfall"]
        for city in response.context["view"]["owned_cities"]
    )
    assert not CommandReceipt.objects.filter(game=game).exists()


@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@case("remarks-invalid-men", "Owner: malformed headcounts return to the expedition action")
def test_invalid_men(user):
    game = services.create_game(user, "Invalid men", opponents="passive")
    client = Client()
    client.force_login(user)
    response = client.post(
        reverse("preview", args=[game.id]),
        {"kind": "capture", "target": "c4", "men_c1": "1.5"},
        follow=True,
    )
    assert response.context["tab"] == "wars" and response.context["mission_kind"] == "capture"
    game.refresh_from_db()
    assert game.revision == 0 and not game.state["orders"]


@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@case(
    "remarks-reopen-rejection", "Owner: signed drafts which fail revalidation return to the action"
)
@pytest.mark.parametrize("failure", ["funds", "deadline", "revision"])
def test_reopen_rejection(user, monkeypatch, failure):
    game = services.create_game(user, "Reopen", opponents="passive")
    client = Client()
    client.force_login(user)
    preview = client.post(
        reverse("preview", args=[game.id]), {"kind": "raid", "target": "c4", "men_c1": 30}
    )
    if failure == "funds":
        game.state["cities"]["c1"]["stock"] = 0
    elif failure == "deadline":
        game.deadline = datetime(2026, 1, 1, tzinfo=timezone.utc)
    else:
        game.revision += 1
    game.save()
    response = client.get(
        reverse("preview", args=[game.id]), {"payload": preview.context["payload"]}
    )
    assert parse_qs(urlsplit(response.url).query)["action"] == ["expedition"]
    game.refresh_from_db()
    assert not game.state["orders"]


@pytest.mark.integration
@case("remarks-aligned-start", "Owner: automatic closures fall on five/ten-minute wall-clock marks")
@pytest.mark.parametrize("interval", [5, 10])
@pytest.mark.parametrize("minute,second,microsecond", [(3, 42, 123), (10, 0, 0), (59, 59, 999999)])
def test_aligned_start(user, monkeypatch, interval, minute, second, microsecond):
    now = datetime(2026, 10, 19, 13, minute, second, microsecond, tzinfo=timezone.utc)
    monkeypatch.setattr(services.timezone, "now", lambda: now)
    game = services.create_game(user, "Aligned", mode="scheduled", interval_minutes=interval)
    services.start_calendar(user, game.id)
    game.refresh_from_db()
    assert game.deadline.minute % interval == 0
    assert game.deadline.second == game.deadline.microsecond == 0
    assert now < game.deadline <= now + timedelta(minutes=interval)
    deadline = game.deadline
    services.start_calendar(user, game.id)
    game.refresh_from_db()
    assert game.deadline == deadline and game.state["month"] == 1


@pytest.mark.integration
@case("remarks-aligned-resume", "Owner: aligned calendars keep wall-clock cadence after a pause")
def test_aligned_resume(user, monkeypatch):
    now = datetime(2026, 10, 19, 13, 3, tzinfo=timezone.utc)
    monkeypatch.setattr(services.timezone, "now", lambda: now)
    game = services.create_game(user, "Resume", mode="scheduled", interval_minutes=5)
    services.start_calendar(user, game.id)
    services.toggle_pause(user, game.id)
    now += timedelta(minutes=1)
    services.toggle_pause(user, game.id)
    game.refresh_from_db()
    assert game.deadline == datetime(2026, 10, 19, 13, 10, tzinfo=timezone.utc)
