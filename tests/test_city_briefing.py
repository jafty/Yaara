"""City inspection keeps local commitments visible before choosing an order."""

import pytest

from simulation import engine
from tests.cases import case
from tests.test_map_workspace import open_board

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case(
    "city-briefing-commitment",
    "Owner: city panel shows its crew and local deadlines without unrelated commitments",
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("stage", ["free", "sealed", "active", "other-city"])
def test_local_commitments(user, language, stage):
    game, client, url = open_board(user, language)
    order = None
    if stage != "free":
        order = engine.confirm_order(
            game.state,
            "p1",
            {"kind": "irrigation", "cities": ["c2" if stage == "other-city" else "c1"]},
            "briefing-work",
        )
        if stage == "active":
            engine.advance_month(game.state, "briefing-start")
    game.save()
    response = client.get(url, {"city": "c1"})
    html = response.content.decode()
    assert 'class="city-briefing"' in html
    assert "data-city-deadlines" in html
    briefing = html.split('<section class="city-briefing"', 1)[1].split("</section>", 1)[0]
    assert "harvest-accounts" not in briefing
    assert 'id="city-briefing-stats"' in briefing
    assert response.context["selected"]["wall_label"] not in briefing
    actions = html.split('<nav class="city-actions"', 1)[1].split("</nav>", 1)[0]
    assert ("Convois" if language == "fr" else "Convoys") in actions
    assert "<h2>Échéances</h2>" not in briefing
    busy = stage in ("sealed", "active")
    assert f'data-team-state="{"occupied" if busy else "available"}"' in html
    if stage in ("sealed", "other-city"):
        assert (order["id"] in html) == busy
    if stage == "active":
        assert "#work-c1-0" in html
    assert ("data-crew-phase=" in html) == busy
    if busy:
        assert (
            "Rigoles et petites digues" if language == "fr" else "Channels and small dikes"
        ) in briefing
        assert ("Construire Rigoles" if language == "fr" else "Build Channels") not in briefing
        assert "<li>" not in briefing
    if busy:
        assert response.context["city_schedule"][0]["moon"] < 12
    else:
        assert len(response.context["city_schedule"]) == 1


@case(
    "city-briefing-movement",
    "Owner: only movements involving the inspected city appear in its deadlines",
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("kind", ["raid", "convoy"])
@pytest.mark.parametrize("phase", ["sealed", "active"])
def test_local_movements(user, language, kind, phase):
    game, client, url = open_board(user, language)
    spec = (
        {"kind": "raid", "target": "c4", "contributions": {"c3": 20}}
        if kind == "raid"
        else {"kind": "convoy", "origin": "c1", "target": "c2", "cargo": 100000}
    )
    engine.confirm_order(game.state, "p1", spec, "briefing-move")
    if phase == "active":
        engine.advance_month(game.state, "briefing-departure")
    game.save()
    involved = "c3" if kind == "raid" else "c1"
    other = "c1" if kind == "raid" else "c3"
    events = client.get(url, {"city": involved}).context["city_schedule"]
    assert any(
        event["anchor"].startswith(
            "order-" if phase == "sealed" else "mission-" if kind == "raid" else "convoy-"
        )
        for event in events
    )
    unrelated = client.get(url, {"city": other}).context["city_schedule"]
    assert [event["anchor"] for event in unrelated] == ["harvest-accounts"]
