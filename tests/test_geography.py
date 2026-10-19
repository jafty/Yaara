"""New reigns use a mesh while saved roads remain authoritative."""

import pytest

from simulation import engine
from simulation.projections import player_view
from tests.cases import case

pytestmark = pytest.mark.logic


@case("geography-mesh-frontiers", "Owner: new geography has interior routes and wider frontiers")
@pytest.mark.parametrize(
    "actor,expected",
    [
        ("p1", {"c4", "c5", "c7", "c8", "c9"}),
        ("p2", {"c1", "c2", "c3", "c7", "c8"}),
        ("p3", {"c1", "c2", "c4", "c5", "c6"}),
    ],
)
def test_mesh_frontiers(actor, expected):
    """Given a new reign with the mesh geography.
    When {actor} considers its initial frontiers.
    Then five rival cities are reachable and all three friendly origins can contribute.
    """
    state = engine.new_state(economy_version=1, map_version=2)
    assert state["map_version"] == 2
    assert len(state["links"]) == 15
    assert len({tuple(sorted(link)) for link in state["links"]}) == 15
    owned = {city["id"] for city in engine.owned_cities(state, actor)}
    targets = {city for city in state["cities"] if engine.eligible_origins(state, actor, city)}
    assert targets == expected
    assert all(engine.eligible_origins(state, actor, city) == owned for city in targets)
    assert max(sum(city in link for link in state["links"]) for city in state["cities"]) == 4
    assert {target["id"] for target in player_view(state, actor)["attack_targets"]} == expected


@case("geography-legacy-ring", "Compatibility: legacy roads are read unchanged without a marker")
def test_legacy_roads():
    """Given a saved reign with the original ring and no geography marker.
    When its frontier is projected.
    Then only its original two enemy neighbours are reachable and roads stay unchanged.
    """
    state = engine.new_state(map_version=1, economy_version=1)
    state.pop("map_version")
    roads = [link[:] for link in state["links"]]
    assert {target["id"] for target in player_view(state, "p1")["attack_targets"]} == {"c4", "c9"}
    assert state["links"] == roads
