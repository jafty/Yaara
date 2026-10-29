"""Returning troops use nearby refuge or join their captured home's Faithful."""

from copy import deepcopy

import pytest

from simulation import engine
from tests.cases import case

pytestmark = pytest.mark.logic


def returning_contingent():
    state = engine.new_state(opponents="passive", economy_version=4)
    state["links"] = [["c1", "c2"], ["c2", "c3"], ["c2", "c4"]]
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c1": 20}}, "return"
    )
    engine.advance_month(state, "departure")
    mission = state["expeditions"][0]
    mission.update(status="returning", loot=10000)
    state["orders"][0]["status"] = "returning"
    engine.detach_absent_contingents(state, "c1")
    state["cities"]["c1"]["owner"] = "p2"
    state["month"] = mission["return_month"]
    return state, mission


@case(
    "return-neighbour-refuge",
    "Owner: only a friendly direct neighbour of the attacked city is refuge",
)
@pytest.mark.parametrize(
    "scenario,destination",
    [
        ("neighbour", "c2"),
        ("reverse-road", "c2"),
        ("distant-friendly-city", "c1"),
        ("road-removed", "c1"),
        ("new-friendly-neighbour", "c3"),
        ("no-friendly-neighbour", "c1"),
    ],
)
def test_neighbour_refuge(scenario, destination):
    """Given a captured home and the attacked city's roads affected by {scenario}.
    When surviving troops return and any one-Moon diversion arrives.
    Then they join {destination} exactly once without crossing distant territory for refuge.
    """
    state, mission = returning_contingent()
    if scenario == "reverse-road":
        state["links"][-1] = ["c4", "c2"]
    elif scenario == "distant-friendly-city":
        state["cities"]["c2"]["owner"] = "p2"
    elif scenario == "road-removed":
        state["links"] = [["c1", "c2"], ["c2", "c3"]]
    elif scenario == "new-friendly-neighbour":
        state["cities"]["c2"]["owner"] = "p2"
        state["links"].append(["c4", "c3"])
    elif scenario == "no-friendly-neighbour":
        state["cities"]["c2"]["owner"] = state["cities"]["c3"]["owner"] = "p2"
    events = []
    engine.return_expeditions(state, events)
    diverted = destination != "c1"
    assert (mission["status"] == "returning") == diverted
    assert (
        any(str(event["title"]) == "Le contingent cherche refuge" for event in events) == diverted
    )
    if diverted:
        assert mission["return_routes"] == {"c1": destination}
        assert state["cities"][destination]["population"] == 1000
        state["month"] += 1
        engine.return_expeditions(state, events)
    assert state["cities"][destination]["fideles"] == (100 if destination == "c1" else 120)
    assert state["cities"][destination]["population"] == (1000 if destination == "c1" else 1020)
    assert mission["recovered_loot"] == (10000 if diverted else 0)
    assert sum(city["population"] for city in state["cities"].values()) == 9000
    assert mission["status"] == "completed" and mission["loot"] == 0
    before = deepcopy(state)
    engine.return_expeditions(state, [])
    assert state == before


@case(
    "return-conquest-restriction",
    "Owner: returning Faithful share the captured city's remaining restriction",
)
@pytest.mark.parametrize(
    "phase", ["active", "expires-now", "expired", "no-restriction", "legacy-strategy"]
)
def test_conquest_restriction(phase):
    """Given no nearby refuge and the captured home's conquest restriction is {phase}.
    When twenty Faithful return to their families under the new owner.
    Then they remain Faithful and can deploy only after any existing restriction expires.
    """
    state, mission = returning_contingent()
    state["cities"]["c2"]["owner"] = "p2"
    home = state["cities"]["c1"]
    if phase != "no-restriction":
        home.update(restricted_fideles=80, restricted_until=state["month"] + 2)
        if phase == "expires-now":
            home["restricted_until"] = state["month"]
        elif phase == "expired":
            home["restricted_until"] = state["month"] - 1
        elif phase == "legacy-strategy":
            state["strategy_version"] = 1
    deadline = home.get("restricted_until")
    events = []
    engine.return_expeditions(state, events)
    assert home["population"] == 1000 and home["fideles"] == 100
    assert engine.deployable_fideles(state, "c1") == (0 if phase == "active" else 100)
    assert home.get("restricted_until") == deadline
    assert "Fidèles du nouveau souverain" in str(events[0]["body"])
    if phase == "active":
        state["month"] = home["restricted_until"]
        assert engine.deployable_fideles(state, "c1") == 100


@case("return-refuge-lost", "Owner: an invalid refuge sends survivors home as Faithful")
@pytest.mark.parametrize("change", ["owner", "road", "saved-distant-refuge", "home-recaptured"])
def test_refuge_lost(change):
    """Given a contingent whose recorded refuge is invalidated through {change}.
    When the contingent reaches its scheduled arrival.
    Then survivors join their original home's new owner and their loot is lost.
    """
    state, mission = returning_contingent()
    engine.return_expeditions(state, [])
    if change in ("owner", "home-recaptured"):
        state["cities"]["c2"]["owner"] = "p3"
        if change == "home-recaptured":
            state["cities"]["c1"]["owner"] = "p1"
    elif change == "road":
        state["links"].remove(["c2", "c4"])
    else:
        mission["return_routes"]["c1"] = "c3"
    state["month"] += 1
    engine.return_expeditions(state, [])
    assert state["cities"]["c1"]["fideles"] == 100
    assert state["cities"]["c1"]["population"] == 1000
    assert state["cities"]["c2"]["population"] == 1000
    assert mission["recovered_loot"] == (10000 if change == "home-recaptured" else 0)
    assert mission["status"] == "completed"
