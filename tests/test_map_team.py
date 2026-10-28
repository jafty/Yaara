"""The map shows only an owned city's existing crew commitment."""

import re
from copy import deepcopy

import pytest

from simulation import engine
from tests.cases import case
from tests.test_map_workspace import open_board

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case("map-busy-team", "Owner: mark reserved/active owned teams; omit available and enemy teams")
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("phase", ["free", "reserved", "active", "cancelled", "completed", "enemy"])
def test_busy_team(user, language, phase):
    game, client, url = open_board(user, language)
    if phase != "free":
        actor, city = ("p2", "c4") if phase == "enemy" else ("p1", "c1")
        order = engine.confirm_order(
            game.state, actor, {"kind": "irrigation", "cities": [city]}, "map-team"
        )
        if phase == "cancelled":
            engine.cancel_order(game.state, actor, order["id"])
        for _ in range(4 if phase == "completed" else int(phase == "active")):
            engine.advance_month(game.state, "map-team")
    game.save()
    before = deepcopy(game.state)
    html = client.get(url).content.decode()
    busy = phase in ("reserved", "active")
    assert re.findall(r'data-busy-city="([^"]+)"', html) == (["c1"] if busy else [])
    city_link = re.search(r'<a class="map-city[^>]*city=c1[^>]*>', html).group()
    label = "Équipe occupée" if language == "fr" else "Crew occupied"
    assert (label in city_link) == busy
    assert 'data-busy-city="c4"' not in html
    game.refresh_from_db()
    assert game.state == before
