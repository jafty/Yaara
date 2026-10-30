"""Saved public road curves and own travelling commitments share one geometry."""

from copy import deepcopy

import pytest

from simulation import engine
from simulation.cartography import workspace_context
from simulation.projections import player_view
from tests.cases import case

pytestmark = pytest.mark.logic
REQ = "Owner October 28: solid contingents follow dashed saved road curves and destination colors"


def board(state, actor="p1"):
    view = player_view(state, actor)
    return view, workspace_context(view)


@case("route-military-curve", REQ)
@pytest.mark.parametrize("phase", ["sealed", "outbound", "returning"])
def test_military_curve(phase):
    """Given an own raid in the {phase} phase over one saved road.
    When its map presentation is built.
    Then its route follows that road curve and its destination determines the color.
    """
    state = engine.new_state(opponents="passive")
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c3": 20}}, "raid"
    )
    if phase != "sealed":
        engine.advance_month(state, "departure")
    if phase == "returning":
        engine.advance_month(state, "battle")
    before = deepcopy(state)
    view, context = board(state)
    march = context["marches"][0]
    assert march["state"] == phase
    assert march["friendly"] == (phase == "returning")
    assert " Q " in march["path"] and " L " not in march["path"]
    if phase != "returning":
        road = next(
            e for e in view["links"] if {e["first"]["id"], e["second"]["id"]} == {"c3", "c4"}
        )
        assert march["path"] == road["path"]
    else:
        assert march["path"] == "M 420 130 Q 346.30 142.40 275 120"
    assert state == before


@case("route-multi-city-return", REQ)
def test_multi_city_return():
    """Given a returning raid whose contingent belongs to a rear city.
    When its map route is built.
    Then it follows both saved road curves through its owned frontier city.
    """
    state = engine.new_state(opponents="passive")
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c1": 20}}, "raid"
    )
    engine.advance_month(state, "departure")
    engine.advance_month(state, "battle")
    _, context = board(state)
    march = context["marches"][0]
    assert march["target"]["id"] == "c1"
    assert march["friendly"]
    assert march["path"] == ("M 420 130 Q 346.30 142.40 275 120 Q 217.00 186.80 135 220")


@case("route-convoy-curve", REQ)
@pytest.mark.parametrize("phase", ["sealed", "outbound", "returning"])
def test_convoy_curve(phase):
    """Given an own convoy in the {phase} phase.
    When its map route is built.
    Then its actual friendly destination and saved road curve are displayed.
    """
    state = engine.new_state(opponents="passive")
    engine.confirm_order(
        state, "p1", {"kind": "convoy", "origin": "c1", "target": "c2", "cargo": 1000}, "convoy"
    )
    if phase != "sealed":
        engine.advance_month(state, "departure")
    if phase == "returning":
        state["cities"]["c2"]["owner"] = "p2"
        engine.advance_month(state, "transit")
        engine.advance_month(state, "diversion")
    _, context = board(state)
    march = context["marches"][0]
    assert march["state"] == phase
    assert march["friendly"]
    assert march["origin"]["id"] == ("c2" if phase == "returning" else "c1")
    assert march["target"]["id"] == ("c1" if phase == "returning" else "c2")
    assert " Q " in march["path"] and " L " not in march["path"]
    assert march["anchor"] == ("order-convoy" if phase == "sealed" else "convoy-0")


@case("route-diverted-return", REQ)
def test_diverted_return():
    """Given a surviving contingent diverted from its captured origin to an owned refuge.
    When its map route is built after the diversion.
    Then it starts at the attacked city and follows one saved road to its neighbouring refuge.
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
    _, context = board(state)
    march = context["marches"][0]
    assert (march["origin"]["id"], march["target"]["id"]) == ("c4", "c1")
    assert march["friendly"]
    assert march["path"] == "M 420 130 Q 288.30 209.20 135 220"


@case("route-return-lost-intermediate", REQ)
def test_return_lost_intermediate():
    """Given a returning mission whose intermediate city has been conquered.
    When its map route is built from the still-public saved road graph.
    Then the abstract return remains visible along its original road curves.
    """
    state = engine.new_state(opponents="passive")
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c1": 20}}, "raid"
    )
    engine.advance_month(state, "departure")
    engine.advance_month(state, "battle")
    state["cities"]["c3"]["owner"] = "p2"
    _, context = board(state)
    march = context["marches"][0]
    assert march["friendly"]
    assert march["path"] == ("M 420 130 Q 346.30 142.40 275 120 Q 217.00 186.80 135 220")


@case("route-settled-contingents", REQ)
@pytest.mark.parametrize("state_change", ["arrived", "lost"])
def test_settled_contingents(state_change):
    """Given a return containing a contingent already {state_change}.
    When its authorized map route is built.
    Then that contingent no longer appears as travelling.
    """
    state = engine.new_state(opponents="passive")
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c3": 20}}, "raid"
    )
    engine.advance_month(state, "departure")
    engine.advance_month(state, "battle")
    if state_change == "arrived":
        state["expeditions"][0]["arrived_origins"].append("c3")
    else:
        state["expeditions"][0]["cohorts"]["c3"] = 0
    _, context = board(state)
    assert context["marches"] == []


@case("route-rear-city-launch", REQ)
def test_rear_city_launch():
    """Given a raid gathered entirely from a rear city and launched at the frontier.
    When its outbound map route is built.
    Then its frontier departure curve remains visible despite no local launch contingent.
    """
    state = engine.new_state(opponents="passive")
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c1": 20}}, "raid"
    )
    engine.advance_month(state, "departure")
    _, context = board(state)
    march = context["marches"][0]
    assert (march["origin"]["id"], march["target"]["id"]) == ("c3", "c4")
    assert march["path"] == "M 275 120 Q 346.30 142.40 420 130"
    assert not march["friendly"]


@case("route-sealed-lost-intermediate", REQ)
def test_sealed_lost_intermediate():
    """Given a legacy sealed raid whose only owned road chain has been broken.
    When its route is built before departure revalidation.
    Then it does not invent a path through hostile intermediate cities.
    """
    state = engine.new_state(opponents="passive", strategy_version=1)
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c1": 20}}, "raid"
    )
    state["cities"]["c3"]["owner"] = "p2"
    _, context = board(state)
    assert context["marches"] == []
