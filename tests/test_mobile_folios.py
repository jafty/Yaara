"""Public geography and three destinations stay independent of calendar controls."""

import re
import uuid

import pytest
from django.test import Client
from django.urls import reverse

from simulation import engine, services
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case(
    "folio-navigation-three",
    "Owner UX: Council, crossed-blade Expeditions, Works are the only main destinations",
)
@pytest.mark.parametrize(
    "tab,active",
    [
        ("domain", "domain"),
        ("city", "domain"),
        ("letters", "domain"),
        ("decrees", "domain"),
        ("constructions", "constructions"),
        ("wars", "wars"),
    ],
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_navigation(user, tab, active, language):
    game = services.create_game(user, "Navigation", opponents="passive")
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    page = client.get(reverse("game", args=[game.id]), {"tab": tab, "city": "c1"})
    html = page.content.decode()
    nav = re.search(r'<nav class="bookmarks".*?</nav>', html, re.S).group()
    assert len(re.findall(r"<a\b", nav)) == 3
    assert len(re.findall('aria-current="page"', nav)) == 1
    assert f'data-section="{active}" aria-current="page"' in nav
    assert 'data-icon="blades"' in nav
    assert ("Council" if language == "en" else "Conseil") in nav
    ribbon = re.search(r'<div class="resource-ribbon".*?</div>', html, re.S).group()
    assert "turn-page" not in ribbon


@case(
    "folio-public-map",
    "Owner UX: a parchment schematic links public cities and actual roads without private data",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_map(user, language):
    game = services.create_game(user, "Atlas", opponents="passive")
    game.state["cities"]["c4"].update(stock=1234567, fideles=87, forge=2)
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    page = client.get(reverse("game", args=[game.id]), {"tab": "wars"})
    html = page.content.decode()
    atlas = re.search(r'<figure class="realm-map".*?</figure>', html, re.S).group()
    assert atlas.count('class="map-city') == 9
    assert atlas.count('class="map-road"') == 9
    assert "Qasr" in atlas and "Sefra" in atlas
    assert "tab=city&amp;city=c4" in atlas
    assert "1234567" not in html and "1\u00a0234\u00a0567" not in html
    assert all(
        "equipment" not in city for city in page.context["view"]["cities"] if not city["owned"]
    )
    assert "style=" not in atlas


@case(
    "folio-local-forge-http",
    "Local forge: Works exposes a multi-city form and one read-only preview/seal",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_local_forge_http(user, language):
    game = services.create_game(user, "Forges", opponents="passive")
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
    game = services.create_game(user, "Cancellation", opponents="passive")
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
    game = services.create_game(user, "Commitments", opponents="passive")
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
    game = services.create_game(user, "Archive", opponents="passive", forge_version=1)
    game.state.pop("forge_version")
    for city in game.state["cities"].values():
        city.pop("forge")
    game.save()
    client = Client()
    client.force_login(user)
    page = client.get(reverse("game", args=[game.id]), {"tab": "constructions"})
    assert b"action=equipment" in page.content
    assert b'id="work-forge"' not in page.content
    preview = client.post(reverse("preview", args=[game.id]), {"kind": "equipment"})
    assert preview.status_code == 200
    assert preview.context["order"]["cost"] == 1_800_000
