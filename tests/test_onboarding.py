"""Guidance stays outside routine play while cities and confirmation remain discoverable."""

import uuid
from copy import deepcopy

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from simulation import engine, services
from simulation.models import Game
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case(
    "intro-new-game",
    "Owner: each newly created game opens the first manuscript page without replaying creation",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_new_game_intro(user, language):
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    response = client.post(
        reverse("new_game"),
        {
            "title": "A new story",
            "player_name": "Amber",
            "version": "V1",
            "opponents": "passive",
            "reign_months": 120,
            "mode": "manual",
            "interval_minutes": 10,
        },
    )
    game = Game.objects.get(owner=user)
    assert response["Location"] == reverse("game", args=[game.id]) + "?tab=prologue"
    first = client.get(response["Location"])
    assert 'data-prologue-page="1"' in first.content.decode()
    client.get(response["Location"])
    assert Game.objects.filter(owner=user).count() == 1
    game.refresh_from_db()
    assert game.state["month"] == 1 and game.state["orders"] == [] and game.revision == 0


@case(
    "intro-pages-readonly",
    "Owner: novel pages can be traversed, skipped and replayed without affecting the reign",
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("page", [1, 2, 3, 4])
def test_intro_pages(user, language, page):
    game = services.create_game(
        user, "The opening pages", opponents="passive", economy_version=1, map_version=2
    )
    before = deepcopy(game.state)
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    response = client.get(reverse("game", args=[game.id]), {"tab": "prologue", "page": page})
    html = response.content.decode()
    assert response.status_code == 200
    assert f'data-prologue-page="{page}"' in html and "data-prologue-skip" in html
    assert ("data-prologue-next" in html) == (page < 4)
    assert ("data-prologue-previous" in html) == (page > 1)
    assert ("data-prologue-enter" in html) == (page == 4)
    assert ("First steps" if language == "en" else "Premiers pas") in html
    assert "?tab=help" in html
    game.refresh_from_db()
    assert game.state == before and game.revision == 0
    council = client.get(reverse("game", args=[game.id]), {"tab": "domain"})
    assert "data-prologue-page" not in council.content.decode()


@case(
    "intro-invalid-page", "Owner: invalid prologue page requests are rejected without game mutation"
)
@pytest.mark.parametrize("page", ["0", "5", "-1", "not-a-page", "1.5"])
def test_invalid_intro_page(user, page):
    game = services.create_game(
        user, "Pages", opponents="passive", economy_version=1, map_version=2
    )
    client = Client()
    client.force_login(user)
    assert (
        client.get(reverse("game", args=[game.id]), {"tab": "prologue", "page": page}).status_code
        == 404
    )
    game.refresh_from_db()
    assert game.revision == 0 and not game.state["orders"]


@case("guidance-private", "Existing authorization: help and introductory pages require membership")
@pytest.mark.parametrize("tab", ["help", "prologue"])
def test_guidance_private(user, tab):
    other = get_user_model().objects.create_user("guide-stranger")
    game = services.create_game(
        other, "Another realm", opponents="passive", economy_version=1, map_version=2
    )
    client = Client()
    client.force_login(user)
    assert client.get(reverse("game", args=[game.id]), {"tab": tab}).status_code == 403


@case(
    "guide-context",
    "Owner: accessible rules explain victory, resources, orders and actual calendar/rule variants",
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("version", ["V0", "V1"])
@pytest.mark.parametrize("mode", ["manual", "scheduled"])
def test_guide_context(user, language, version, mode):
    game = services.create_game(
        user,
        "Guide",
        version=version,
        mode=mode,
        reign_months=24,
        opponents="passive",
        economy_version=1,
        map_version=2,
    )
    before = deepcopy(game.state)
    deadline = game.deadline
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    html = client.get(reverse("game", args=[game.id]), {"tab": "help"}).content.decode()
    assert all(
        f'id="{section}"' in html
        for section in ("victory", "resources", "orders", "buildings", "expeditions", "calendar")
    )
    assert "data-prologue-replay" in html
    assert ("24 Moons" if language == "en" else "24 lunes") in html
    assert (
        ("Manually close each Moon" if language == "en" else "Clore chaque lune manuellement")
        in html
        if mode == "manual"
        else ("The automatic calendar" if language == "en" else "Le calendrier automatique") in html
    )
    assert (
        ("Confirmation is final" if language == "en" else "La confirmation est définitive") in html
        if version == "V0"
        else ("Withdraw a sealed order" if language == "en" else "Retirer un ordre scellé") in html
    )
    game.refresh_from_db()
    assert game.state == before and game.deadline == deadline and game.revision == 0


@case(
    "intro-scheduled-clock",
    "Owner: reading an automatic game's introduction does not silently pause or restart its clock",
)
def test_scheduled_intro_clock(user):
    game = services.create_game(
        user,
        "Automatic pages",
        mode="scheduled",
        opponents="passive",
        economy_version=1,
        map_version=2,
    )
    deadline = game.deadline
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = "fr"
    html = client.get(reverse("game", args=[game.id]), {"tab": "prologue"}).content.decode()
    assert "La lecture ne suspend pas le calendrier automatique." in html
    assert "data-deadline=" in html
    game.refresh_from_db()
    assert game.deadline == deadline and not game.paused


@case(
    "council-city-ledger",
    "Owner: city accounts distinguish total stock from free stock without a council ledger",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_city_ledger(user, language):
    game = services.create_game(
        user, "Ledger", opponents="passive", economy_version=1, map_version=2
    )
    for city, stock in zip(("c1", "c2", "c3"), (300000, 600000, 900000)):
        game.state["cities"][city]["stock"] = stock
    game.save()
    services.confirm(user, game.id, {"kind": "storage", "cities": ["c1"]}, uuid.uuid4(), 1)
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    response = client.get(reverse("game", args=[game.id]), {"tab": "domain"})
    html = response.content.decode()
    assert 'id="city-ledgers"' not in html
    assert 'id="frontier-notes"' not in html and 'id="standings-heading"' in html
    first = response.context["view"]["owned_cities"][0]
    assert first["stock"] == 300000 and first["available_stock"] == 216667 and first["busy"]
    city_html = client.get(
        reverse("game", args=[game.id]), {"tab": "map", "city": "c1", "action": "accounts"}
    ).content.decode()
    assert ("216\u00a0667" if language == "fr" else "216,667") in city_html
    assert "?tab=help" in html


@case(
    "order-label-boundary",
    "Owner: validating selection opens read-only review; only final confirmation reserves resources",
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("kind", ["storage", "raid", "equipment"])
def test_order_labels(user, language, kind):
    game = services.create_game(
        user,
        "Clear confirmation",
        forge_version=1 if kind == "equipment" else 2,
        opponents="passive",
        economy_version=1,
        map_version=2,
    )
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    query = (
        {"tab": "wars", "action": "expedition"}
        if kind == "raid"
        else {"tab": "constructions", "action": kind}
    )
    html = client.get(reverse("game", args=[game.id]), query).content.decode()
    if kind == "raid":
        assert ("Review the order" if language == "en" else "Vérifier l’ordre") in html
    else:
        assert 'class="primary-action work-review" type="submit"' in html
    assert "Faire relire" not in html
    spec = {"kind": kind}
    if kind == "storage":
        spec["cities"] = ["c1"]
    elif kind == "raid":
        spec.update(target="c4", men_c3=45)
    preview = client.post(reverse("preview", args=[game.id]), spec)
    assert preview.status_code == 200
    assert (
        "Confirm and seal the order" if language == "en" else "Confirmer et sceller l’ordre"
    ) in preview.content.decode()
    game.refresh_from_db()
    assert not game.state["orders"] and not any(engine.reservations(game.state)[0].values())
    client.post(reverse("confirm", args=[game.id]), {"payload": preview.context["payload"]})
    game.refresh_from_db()
    assert len(game.state["orders"]) == 1 and sum(engine.reservations(game.state)[0].values()) > 0
