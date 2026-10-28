"""Owner's map-art and navigation variations, specified before implementation."""

import re

import pytest
from django.test import Client
from django.urls import reverse

from simulation import services
from tests.cases import case
from tests.test_map_workspace import open_board

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]
REQ = "Owner October 27: schematic fortifications, header navigation, fluid contextual tabs"


@case("map-organic-layout", "Owner: spread cities organically without changing saved connections")
@pytest.mark.parametrize("version", [1, 2, 3])
def test_organic_layout(user, version):
    game = services.create_game(user, "Organic layout", opponents="passive", map_version=version)
    client = Client()
    client.force_login(user)
    response = client.get(reverse("game", args=[game.id]))
    cities = response.context["view"]["cities"]
    assert [(c["x"], c["y"]) for c in cities] == [
        (135, 220),
        (90, 75),
        (275, 120),
        (440, 70),
        (590, 185),
        (515, 300),
        (445, 390),
        (260, 435),
        (125, 360),
    ]
    graph = response.context["map_graph"]
    assert {tuple(edge) for edge in graph["links"]} == {tuple(edge) for edge in game.state["links"]}
    assert 'class="map-marker"' not in response.content.decode()
    assert 'class="map-inner"' not in response.content.decode()


@case("map-selected-roads", "Owner: only the selected city's saved connections are emphasized")
@pytest.mark.parametrize("selected,roads", [(None, 0), ("c1", 3), ("c2", 2), ("c4", 3)])
def test_selected_roads(user, selected, roads):
    _, client, url = open_board(user)
    html = client.get(url, {"city": selected} if selected else {}).content.decode()
    assert html.count('class="map-connection selected-road"') == roads
    assert re.search(
        r'<path class="map-connection[^" ]*(?: selected-road)?"[^>]* d="M [^"]+ Q [^"]+"', html
    )


@case("map-header-navigation", REQ)
@pytest.mark.parametrize("tab", ["map", "mail", "domain"])
def test_header_navigation(user, tab):
    _, client, url = open_board(user)
    html = client.get(url, {"tab": tab}).content.decode()
    assert 'class="bookmarks"' not in html
    header = re.search(r'<header class="reign-header">.*?</header>', html, re.S).group()
    assert len(re.findall(r'data-section="', header)) == 3
    assert f'href="{reverse("home")}"' in header
    assert "#turn-page" in header
    assert f'data-section="{tab}" aria-current="page"' in header


@case(
    "map-fixed-activity-tabs",
    "Owner: city action sheets retain resources and return to the city without tabs",
)
@pytest.mark.parametrize("action", ["works", "accounts", "convoy"])
def test_fixed_tabs(user, action):
    _, client, url = open_board(user)
    html = client.get(url, {"city": "c1", "action": action}).content.decode()
    assert 'class="city-activities"' not in html
    assert 'class="city-resources"' in html and "data-focus-action" in html
    assert 'class="panel-close" href="?tab=map&amp;city=c1"' in html


@case("map-public-fortification-art", REQ)
@pytest.mark.parametrize(
    "economy,level,tile",
    [(4, 0, 0), (4, 1, 1), (4, 2, 2), (4, 3, 3), (1, 0, 0), (1, 1, 4), (1, 2, 5)],
)
def test_fortification_art(user, economy, level, tile):
    game, client, url = open_board(user)
    game.state["economy_version"] = economy
    game.state["cities"]["c4"]["walls"] = level
    game.state["cities"]["c4"]["stock"] = 1234567
    game.save()
    response = client.get(url)
    city = next(c for c in response.context["view"]["cities"] if c["id"] == "c4")
    assert city["settlement_viewbox"] == f"{tile % 3 * 512} {tile // 3 * 512} 512 512"
    html = response.content.decode()
    assert html.count('class="city-art"') == 9
    city_links = "".join(re.findall(r'<a class="map-city .*?</a>', html, re.S))
    assert city_links.count('class="city-flag owned-flag"') == 3
    assert city_links.count('class="city-flag enemy-flag"') == 6
    assert "1234567" not in html


@case("map-curved-public-geography", REQ)
@pytest.mark.parametrize("version,roads", [(1, 9), (2, 15), (3, 12)])
def test_curved_geography(user, version, roads):
    game = services.create_game(user, "Geography", opponents="passive", map_version=version)
    client = Client()
    client.force_login(user)
    url = reverse("game", args=[game.id])
    response = client.get(url)
    html = response.content.decode()
    assert html.count('<path class="map-territory"') == 9
    assert html.count('<path class="map-connection') == roads
    shared_edges = {}
    for city in response.context["view"]["cities"]:
        assert "C " in city["territory_path"]
        assert city["territory_path"].endswith(" Z")

        segments = city["territory_path"].removesuffix(" Z").split(" C ")
        start = tuple(map(float, segments[0][2:].split()))
        for segment in segments[1:]:
            numbers = list(map(float, segment.split()))
            first_control, second_control, end = (
                tuple(numbers[:2]),
                tuple(numbers[2:4]),
                tuple(numbers[4:]),
            )
            edge = (start, end)
            if (end, start) in shared_edges:
                assert shared_edges[(end, start)] == (second_control, first_control)
            shared_edges[edge] = (first_control, second_control)
            start = end


@case(
    "map-moon-control",
    "Manual games provide a direct review link; scheduled games retain their calendar",
)
@pytest.mark.parametrize("mode", ["manual", "scheduled"])
def test_moon_control(user, mode):
    game = services.create_game(user, "Calendar access", mode=mode, opponents="passive")
    client = Client()
    client.force_login(user)
    url = reverse("game", args=[game.id])
    header = re.search(
        r'<header class="reign-header">.*?</header>', client.get(url).content.decode(), re.S
    ).group()
    assert ('class="harvest-link moon-close-link"' in header) == (mode == "manual")
    controls = client.get(url, {"tab": "domain"}).content.decode()
    assert 'id="turn-page"' in controls
    if mode == "manual":
        assert f'action="{reverse("advance", args=[game.id])}"' in controls
    else:
        assert f'action="{reverse("start", args=[game.id])}"' in controls


@case("map-army-details-label", "Army preparation identifies the equipment details in each city")
@pytest.mark.parametrize(
    "language,label", [("fr", "Consulter l’équipement"), ("en", "View equipment")], ids=["fr", "en"]
)
def test_army_details_label(user, language, label):
    _, client, url = open_board(user, language)
    html = client.get(url, {"tab": "map", "city": "c4", "action": "expedition"}).content.decode()
    assert re.search(r'<details class="origin-details">\s*<summary>' + label, html)
