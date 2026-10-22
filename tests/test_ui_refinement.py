"""Presentation contracts for compact preparation and discoverable commitments."""

import re

import pytest
from django.test import Client
from django.urls import reverse

from simulation import engine, services
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@pytest.fixture
def desk(user):
    game = services.create_game(user, "Clear ledgers", opponents="passive")
    client = Client()
    client.force_login(user)
    return game, client, reverse("game", args=[game.id])


@case("ui-compact-origins", "Owner: optional origin details keep price and siege warnings visible")
@pytest.mark.parametrize("language", ["fr", "en"])
def test_compact_origins(desk, language):
    game, client, url = desk
    game.state["cities"]["c1"]["stock"] = 50000
    game.save()
    client.cookies["django_language"] = language
    text = client.get(url, {"tab": "wars", "city": "c4", "men_c1": 50}).content.decode()
    assert text.count('class="origin-details"') == 3
    assert not re.search(r'<details class="origin-details"[^>]*\bopen', text)
    details = re.findall(r'<details class="origin-details">.*?</details>', text, re.S)
    assert all("data-origin-means" in detail for detail in details)
    assert all(
        "origin-funding" not in detail and "data-origin-warning" not in detail for detail in details
    )
    assert 'for="men-c1"' in text and 'id="men-c1"' in text
    assert "reserve-warning" in text


@case("ui-loot-capacity", "Owner: preparation shows transport ceiling without inventing enemy loot")
@pytest.mark.parametrize("language", ["fr", "en"])
def test_loot_capacity(desk, language):
    game, client, url = desk
    game.state["cities"]["c2"]["transport"] = 2
    game.save()
    client.cookies["django_language"] = language
    response = client.get(url, {"tab": "wars", "city": "c4", "men_c1": 20, "men_c2": 10})
    assert response.context["expedition_capacity"] == 175000
    text = response.content.decode()
    assert "data-carry-limit" in text and "data-raid-break-even" in text
    assert ("Plunder" if language == "en" else "Piller") in text
    assert (
        "Actual loot remains unknown" if language == "en" else "Le butin réel reste inconnu"
    ) in text


@case(
    "ui-selected-routes",
    "Owner: selected-city routes explain illustrative borders using saved roads",
)
@pytest.mark.parametrize("map_version", [1, 2, 3])
def test_selected_routes(desk, map_version):
    game, client, url = desk
    game.state = engine.new_state(map_version=map_version)
    game.save()
    text = client.get(url, {"tab": "wars", "city": "c3"}).content.decode()
    expected = {1: {"c2", "c4"}, 2: {"c2", "c4"}, 3: {"c1", "c2", "c4"}}[map_version]
    routes = re.findall(r'class="map-connection" data-first="(c\d)" data-second="(c\d)"', text)
    assert {other for edge in routes for other in edge if other != "c3"} == expected
    assert all("c3" in edge for edge in routes)
    assert "c6" not in {city for edge in routes for city in edge}
    assert 'class="map-neighbors"' in text
    assert 'class="map-connection"' not in client.get(url, {"tab": "wars"}).content.decode()


@case("ui-works-first", "Owner: active works identify cities before the works catalogue")
@pytest.mark.parametrize("language", ["fr", "en"])
def test_works_first(desk, language):
    game, client, url = desk
    engine.confirm_order(game.state, "p1", {"kind": "irrigation", "cities": ["c1", "c2"]}, "work")
    engine.advance_month(game.state, "start")
    game.save()
    client.cookies["django_language"] = language
    text = client.get(url, {"tab": "constructions"}).content.decode()
    assert text.index('id="active-works"') < text.index('class="work-choices"')
    active = text.split('id="active-works"', 1)[1].split("</section>", 1)[0]
    assert "Qasr" in active and "Tamesh" in active
    assert "city=c1" in active and "city=c2" in active
    assert "4" in active
