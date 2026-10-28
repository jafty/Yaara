"""Public geography and three destinations stay independent of calendar controls."""

import re
import uuid
from copy import deepcopy

import pytest
from django.test import Client
from django.urls import reverse

from simulation import engine, services
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case(
    "folio-navigation-map-mail-reign",
    "Owner October 27: Map, Mail and Reign are the three main destinations",
)
@pytest.mark.parametrize(
    "tab,active",
    [
        ("domain", "domain"),
        ("city", "domain"),
        ("letters", "mail"),
        ("decrees", "domain"),
        ("help", "domain"),
        ("prologue", "domain"),
        ("constructions", "domain"),
        ("wars", "domain"),
    ],
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_navigation(user, tab, active, language):
    game = services.create_game(
        user, "Navigation", opponents="passive", economy_version=1, map_version=2
    )
    before = deepcopy(game.state)
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    url = reverse("game", args=[game.id])
    page = client.get(url, {"tab": tab, "city": "c1"})
    assert page.status_code == 200
    html = page.content.decode()
    nav = re.search(r'<div class="realm-identity".*?</div>', html, re.S).group()
    # Home is separate from the three in-game destinations.
    assert len(re.findall(r"<a\b", nav)) == 4
    assert f'<a class="book-world" href="{reverse("home")}">Yaara</a>' in nav
    destinations = re.findall(r'<a\b[^>]+data-section="([a-z]+)"[^>]*>', nav)
    assert destinations == ["map", "domain", "mail"]
    for section in destinations:
        assert re.search(rf'<a\b[^>]+href="{re.escape(url)}\?tab={section}"', nav)
    assert len(re.findall('aria-current="page"', nav)) == (1 if active else 0)
    if active:
        assert f'data-section="{active}" aria-current="page"' in nav
    assert 'data-icon="envelope"' in nav
    assert ("Map" if language == "en" else "Carte") in nav
    ribbon = re.search(r'<div class="resource-ribbon[^"]*".*?</div>', html, re.S).group()
    # Manual closure opens a read-only review; advancing still requires its POST form.
    assert f'href="{url}?tab=domain#turn-page"' in ribbon
    assert ("Close the Moon…" if language == "en" else "Clore la lune…") in ribbon
    assert "<form" not in ribbon
    review = client.get(url, {"tab": "domain"}).content.decode()
    assert 'id="turn-page"' in review
    assert f'<form method="post" action="{reverse("advance", args=[game.id])}"' in review
    game.refresh_from_db()
    assert game.state == before


@case(
    "folio-public-map",
    "Owner UX: a schematic opens city context without roads or private data",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_map(user, language):
    game = services.create_game(
        user, "Atlas", opponents="passive", economy_version=1, map_version=2
    )
    game.state["cities"]["c4"].update(stock=1234567, fideles=87, forge=2)
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    page = client.get(reverse("game", args=[game.id]), {"tab": "wars"})
    html = page.content.decode()
    atlas = re.search(r'<figure class="realm-map".*?</figure>', html, re.S).group()
    assert atlas.count('class="map-city') == 9
    assert 'class="map-road"' not in atlas
    assert "Qasr" in atlas and "Sefra" in atlas
    assert "tab=wars&amp;city=c4#map-context" in atlas
    assert "1234567" not in html and "1\u00a0234\u00a0567" not in html
    assert all(
        "equipment" not in city for city in page.context["view"]["cities"] if not city["owned"]
    )
    # Marker placement is public presentation data; no private values enter styles.
    assert re.findall(r'style="([^"]*)"', atlas) == [
        f"--map-x: {city['x']}; --map-y: {city['y']}" for city in page.context["view"]["cities"]
    ]


@case(
    "folio-map-house-emblems",
    "Owner map revision: distinct house emblems replace Roman numerals and match the legend",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_map_house_emblems(user, language):
    game = services.create_game(user, "Seals", opponents="passive", economy_version=3)
    # A captured city bears its current owner's emblem.
    game.state["cities"]["c1"]["owner"] = "p2"
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    html = client.get(reverse("game", args=[game.id])).content.decode()
    atlas = re.search(r'<figure class="realm-map".*?</figure>', html, re.S).group()
    for owner, emblem in (("p1", "sun"), ("p2", "lotus"), ("p3", "palm")):
        cities = re.findall(rf'<a class="map-city house-{owner} [^"]+".*?</a>', atlas, re.S)
        assert cities
        assert all(f'data-house-emblem="{emblem}"' in city for city in cities)
        legend = re.search(rf'<div class="map-house house-{owner}">.*?</div>', html, re.S).group()
        assert f'data-house-emblem="{emblem}"' in legend
        assert 'aria-hidden="true"' in legend
    assert 'class="map-sigil"' not in atlas


@case(
    "folio-local-forge-http",
    "Local forge: Works exposes a multi-city form and one read-only preview/seal",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_local_forge_http(user, language):
    game = services.create_game(
        user, "Forges", opponents="passive", economy_version=1, map_version=2
    )
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    url = reverse("game", args=[game.id])
    page = client.get(url, {"tab": "constructions"})
    assert b'id="work-forge"' in page.content
    preview = client.post(
        reverse("preview", args=[game.id]), {"kind": "forge", "cities": ["c1", "c2"]}
    )
    assert preview.status_code == 200
    assert preview.context["order"]["cost"] == 1_200_000
    game.refresh_from_db()
    assert not game.state["orders"]
    client.post(reverse("confirm", args=[game.id]), {"payload": preview.context["payload"]})
    game.refresh_from_db()
    assert len(game.state["orders"]) == 1
    assert engine.busy_cities(game.state) == {"c1", "c2"}
    assert sum(engine.reservations(game.state)[0].values()) == 1_200_000


@case("folio-cancel-destination", "Cancellation returns only to an allowed local folio")
@pytest.mark.parametrize(
    "destination,expected",
    [("constructions", "constructions"), ("https://example.com", "decrees")],
    ids=["same-folio", "reject-external"],
)
def test_cancel_destination(user, destination, expected):
    game = services.create_game(
        user, "Cancellation", opponents="passive", economy_version=1, map_version=2
    )
    order_id = uuid.uuid4()
    services.confirm(user, game.id, {"kind": "forge", "cities": ["c1"]}, order_id, 1)
    client = Client()
    client.force_login(user)
    response = client.post(reverse("cancel", args=[game.id, order_id]), {"return_tab": destination})
    assert response["Location"] == f"/games/{game.id}/?tab={expected}"
    game.refresh_from_db()
    assert not any(engine.reservations(game.state)[0].values())


@case(
    "folio-orders-context",
    "Council shows all orders while Works and Expeditions show their own commitments",
)
@pytest.mark.parametrize(
    "tab,kinds",
    [
        ("domain", {"forge", "raid"}),
        ("constructions", {"forge"}),
        ("wars", {"raid"}),
    ],
    ids=["council", "works", "expeditions"],
)
def test_orders_context(user, tab, kinds):
    game = services.create_game(
        user, "Commitments", opponents="passive", economy_version=1, map_version=2
    )
    for spec in (
        {"kind": "forge", "cities": ["c1"]},
        {"kind": "raid", "target": "c4", "contributions": {"c3": 45}},
    ):
        services.confirm(user, game.id, spec, uuid.uuid4(), 1)
    client = Client()
    client.force_login(user)
    response = client.get(reverse("game", args=[game.id]), {"tab": tab})
    assert {order["kind"] for order in response.context["section_orders"]} == kinds


@case("folio-legacy-forge-http", "Existing reigns retain realm equipment and their signed orders")
def test_legacy_forge_http(user):
    game = services.create_game(
        user, "Archive", opponents="passive", forge_version=1, economy_version=1, map_version=2
    )
    game.state.pop("forge_version")
    for city in game.state["cities"].values():
        city.pop("forge")
    game.save()
    client = Client()
    client.force_login(user)
    page = client.get(
        reverse("game", args=[game.id]), {"tab": "constructions", "action": "equipment"}
    )
    assert b'id="work-equipment"' in page.content
    assert b'name="kind" value="equipment"' in page.content
    assert b'id="work-forge"' not in page.content
    preview = client.post(reverse("preview", args=[game.id]), {"kind": "equipment"})
    assert preview.status_code == 200
    assert preview.context["order"]["cost"] == 1_800_000


@case("folio-map-context", "Owner UX: city selection keeps the atlas and offers only valid actions")
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("city", [None, "c1", "c4", "c6"])
def test_map_context(user, language, city):
    game = services.create_game(
        user, "Atlas context", opponents="passive", economy_version=1, map_version=2
    )
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    query = {"tab": "wars"}
    if city:
        query["city"] = city
    page = client.get(reverse("game", args=[game.id]), query)
    html = page.content.decode()
    assert ('id="map-context"' in html) == (city is not None)
    assert html.count('class="map-city') == 9
    assert 'class="map-road"' not in html
    assert 'class="primary-action" href="?tab=wars' not in html
    assert ('type="radio" name="kind" value="raid"' in html) == (city == "c4")
    assert ('type="radio" name="kind" value="capture"' in html) == (city == "c4")
    if city == "c1":
        assert "tab=city&amp;city=c1" in html
    if city == "c6":
        assert ("beyond our borders" if language == "en" else "hors de nos frontières") in html


@case("folio-map-order", "Owner UX: contextual raid or capture preselects target and kind natively")
@pytest.mark.parametrize("kind", ["raid", "capture"])
def test_map_order(user, kind):
    game = services.create_game(
        user, "Atlas order", opponents="passive", economy_version=1, map_version=2
    )
    client = Client()
    client.force_login(user)
    response = client.get(
        reverse("game", args=[game.id]),
        {"tab": "wars", "city": "c4", "action": "expedition", "mission": kind},
    )
    html = response.content.decode()
    assert f'value="{kind}" checked' in html
    assert 'id="mission-target" value="c4"' in html
    assert 'class="map-sheet"' in html


@case("folio-map-unavailable", "Owner UX: engaged or paused targets offer no expedition command")
@pytest.mark.parametrize("unavailable", ["engaged", "paused", "finished", "eliminated"])
def test_map_unavailable(user, unavailable):
    game = services.create_game(
        user, "Unavailable", opponents="passive", economy_version=1, map_version=2
    )
    if unavailable == "engaged":
        engine.confirm_order(
            game.state,
            "p1",
            {"kind": "raid", "target": "c4", "contributions": {"c3": 45}},
            str(uuid.uuid4()),
        )
    elif unavailable == "paused":
        game.paused = True
    elif unavailable == "finished":
        game.state["month"] = 120
        engine.advance_month(game.state, game.seed)
    else:
        for city in game.state["cities"].values():
            city["owner"] = "p2"
    game.save()
    client = Client()
    client.force_login(user)
    html = client.get(
        reverse("game", args=[game.id]), {"tab": "wars", "city": "c4"}
    ).content.decode()
    assert 'type="radio" name="kind"' not in html
