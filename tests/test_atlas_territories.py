"""Public territories and route-based marker states remain independent of private state."""

from copy import deepcopy

import pytest
from django.test import Client
from django.urls import reverse

from simulation import engine, services
from simulation.projections import player_view
from tests.cases import case


@pytest.mark.logic
@case("atlas-territory-geometry", "Owner: nine stable territories tile the map around their cities")
@pytest.mark.parametrize("map_version", [2, 3])
def test_territory_geometry(map_version):
    """Given the public nine-city world with map version {map_version}.
    When its territory outlines are projected.
    Then each city lies in its own bounded polygon and the territories cover the sheet.
    """
    cities = player_view(engine.new_state(economy_version=1, map_version=map_version), "p1")[
        "cities"
    ]
    area = 0
    for city in cities:
        points = [tuple(map(float, point.split(","))) for point in city["territory"].split()]
        assert len(points) >= 3
        assert all(0 <= x <= 680 and 0 <= y <= 500 for x, y in points)
        edges = list(zip(points, points[1:] + points[:1]))
        cross = [
            (bx - ax) * (city["y"] - ay) - (by - ay) * (city["x"] - ax)
            for (ax, ay), (bx, by) in edges
        ]
        assert all(value >= 0 for value in cross) or all(value <= 0 for value in cross)
        area += abs(sum(ax * by - ay * bx for (ax, ay), (bx, by) in edges)) / 2
    assert area == pytest.approx(680 * 500, abs=2)


@pytest.mark.logic
@case("atlas-route-state", "Owner: map reachability follows each saved network for each viewer")
@pytest.mark.parametrize("map_version", [1, 2])
@pytest.mark.parametrize("actor", ["p1", "p2", "p3"])
def test_route_state(map_version, actor):
    """Given map version {map_version} viewed by {actor}.
    When its atlas is projected.
    Then its reachable markers match the authorized targets without changing the save.
    """
    state = engine.new_state(map_version=map_version, economy_version=1)
    before = deepcopy(state)
    view = player_view(state, actor)
    expected = {
        (1, "p1"): {"c4", "c9"},
        (1, "p2"): {"c3", "c7"},
        (1, "p3"): {"c1", "c6"},
        (2, "p1"): {"c4", "c5", "c7", "c8", "c9"},
        (2, "p2"): {"c1", "c2", "c3", "c7", "c8"},
        (2, "p3"): {"c1", "c2", "c4", "c5", "c6"},
    }[map_version, actor]
    assert {city["id"] for city in view["cities"] if city["reachable"]} == expected
    assert {target["id"] for target in view["attack_targets"]} == expected
    assert all(not city["reachable"] for city in view["cities"] if city["owned"])
    assert state == before


@pytest.mark.logic
@case(
    "atlas-captured-territory",
    "Owner: captured territory keeps its shape and follows its new ruler",
)
def test_captured_territory():
    """Given the city of Ishar changes ruler.
    When the public atlas is read again.
    Then its border stays fixed and its ownership and frontier reflect the new ruler.
    """
    state = engine.new_state(economy_version=1, map_version=2)
    before = player_view(state, "p1")["cities"][4]
    state["cities"]["c5"]["owner"] = "p1"
    after = player_view(state, "p1")["cities"][4]
    assert after["territory"] == before["territory"]
    assert after["owned"] and not after["reachable"]
    assert after["owner"] == "p1" and after["owner_name"] != before["owner_name"]
    assert "stock" not in before


@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@case(
    "atlas-marker-states",
    "Owner: ownership, reachability and commitments are distinct without color",
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize(
    "target,attacker,origin,owned,reachable",
    [("c4", "p1", "c3", 3, 4), ("c3", "p2", "c4", 2, 5)],
    ids=["rival-engaged", "own-city-engaged"],
)
def test_marker_states(user, language, target, attacker, origin, owned, reachable):
    game = services.create_game(
        user, "Territories", opponents="passive", economy_version=1, map_version=2
    )
    engine.confirm_order(
        game.state,
        attacker,
        {"kind": "raid", "target": target, "contributions": {origin: 45}},
        "b2f85c36-1ed0-4191-ab62-82cdbca7bec5",
    )
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    html = client.get(reverse("game", args=[game.id]), {"tab": "wars"}).content.decode()
    assert html.count('class="map-territory"') == 9
    assert html.count('data-map-state="owned"') == owned
    assert html.count('data-map-state="reachable"') == reachable
    assert html.count('data-map-state="engaged"') == 1
    assert html.count('data-map-state="unreachable"') == 1
    assert "Out of reach" in html if language == "en" else "Hors de portée" in html
    assert 'class="map-road"' not in html
