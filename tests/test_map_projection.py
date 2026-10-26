"""Own route metadata remains inside the existing projection privacy boundary."""

import pytest

from simulation import engine
from simulation.projections import player_view
from tests.cases import case

pytestmark = pytest.mark.logic


@case(
    "map-own-route-projection",
    "Owner October 26: only own expedition route metadata is public to its actor",
)
def test_own_route():
    """Given an own sealed raid and a hidden rival raid.
    When both depart and their owners inspect their authorized projections.
    Then the own route and identity are available without exposing the rival mission.
    """
    state = engine.new_state(opponents="passive")
    own = engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c1": 10, "c3": 20}}, "own"
    )
    engine.confirm_order(
        state, "p2", {"kind": "raid", "target": "c7", "contributions": {"c5": 20}}, "other"
    )
    assert player_view(state, "p1")["orders"][0]["launch_city"] == "c3"
    engine.advance_month(state, "departures")
    missions = player_view(state, "p1")["missions"]
    assert len(missions) == 1
    assert missions[0]["id"] == own["id"]
    assert missions[0]["launch_city"] == "c3"
    assert missions[0]["target_id"] == "c4"
    assert missions[0]["origins"] == ["c1", "c3"]
