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


@case("map-own-convoy-projection", "Owner October 28: own convoy routes use stable city identities")
def test_own_convoy_route():
    """Given own and rival convoys with cities sharing an identical name.
    When the owner reads sealed and departed routes.
    Then only the own convoy's stable identities are exposed with unchanged destinations.
    """
    state = engine.new_state(opponents="passive")
    state["cities"]["c2"]["name"] = state["cities"]["c1"]["name"]
    own = engine.confirm_order(
        state, "p1", {"kind": "convoy", "origin": "c1", "target": "c2", "cargo": 1000}, "own"
    )
    engine.confirm_order(
        state, "p2", {"kind": "convoy", "origin": "c4", "target": "c5", "cargo": 1000}, "other"
    )
    order = player_view(state, "p1")["orders"][0]
    assert (order["origin_id"], order["target_id"]) == ("c1", "c2")
    engine.advance_month(state, "departure")
    convoys = player_view(state, "p1")["convoys"]
    assert len(convoys) == 1
    assert (convoys[0]["id"], convoys[0]["origin_id"], convoys[0]["target_id"]) == (
        own["id"],
        "c1",
        "c2",
    )


@case(
    "map-own-return-projection",
    "Owner October 28: returned cohorts and actual refuges identify own travel",
)
def test_own_return_projection():
    """Given an own contingent diverted from a conquered origin.
    When its owner reads the returning route metadata.
    Then the owned refuge and per-origin arrival state are available only to that owner.
    """
    state = engine.new_state(opponents="passive")
    state["links"].append(["c1", "c4"])
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c3": 20}}, "raid"
    )
    engine.advance_month(state, "departure")
    engine.advance_month(state, "battle")
    state["cities"]["c3"]["owner"] = "p2"
    engine.advance_month(state, "diversion")
    own = player_view(state, "p1")["missions"][0]
    assert own["return_routes"] == {"c3": "c1"}
    assert own["arrived_origins"] == []
    assert own["cohorts"]["c3"] > 0
    assert player_view(state, "p2")["missions"] == []
