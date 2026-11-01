"""Independent regressions for occupation witnesses and target-lock disclosure."""

from copy import deepcopy

import pytest

from simulation import engine
from simulation.rules import RuleError
from tests.cases import case

pytestmark = pytest.mark.logic
REQ = "November 1 review: locks disclose only valid conflicts and occupation reports use actual witnesses"


def seal(state, actor, target, origin, men, identity, kind="capture"):
    return engine.confirm_order(
        state,
        actor,
        {"kind": kind, "target": target, "contributions": {origin: men}},
        identity,
    )


def occupied_guard():
    state = engine.new_state(opponents="passive", strategy_version=3)
    for city in state["cities"].values():
        city["fideles"] = 0
    state["cities"]["c3"]["fideles"] = 81
    seal(state, "p1", "c4", "c3", 81, "conquest")
    engine.advance_month(state, "review")
    engine.advance_month(state, "review")
    # The occupied place has no local soldiers or neighboring relief: all
    # witnesses are the actual forty-one occupation survivors.
    state["links"].remove(["c3", "c4"])
    state["cities"]["c5"]["fideles"] = 100
    return state


@case("consolidation-lock-invalid-probe", REQ)
@pytest.mark.parametrize(
    "actor,origin,reason",
    [
        pytest.param("p2", "c4", "cité ennemie", id="own-city"),
        pytest.param("p3", "c7", "rejoindre cette frontière", id="unreachable-enemy"),
        pytest.param("p1", "c1", "grenier", id="unfunded-competing-order"),
    ],
)
def test_invalid_order_does_not_probe_lock(actor, origin, reason):
    """Given a hidden target commitment and an otherwise invalid competing request.
    When an own-city, unreachable or unfunded order attempts final confirmation.
    Then ordinary validation rejects it without revealing the hidden commitment or changing state.
    """
    state = engine.new_state(opponents="passive", strategy_version=3)
    seal(state, "p1", "c4", "c3", 80, "first")
    state["cities"]["c1"]["stock"] = 1
    before = deepcopy(state)
    with pytest.raises(RuleError, match=reason):
        seal(state, actor, "c4", origin, 80, "invalid")
    assert state == before


@case("consolidation-occupation-witnesses", REQ)
def test_occupation_survivors_report_enemy_losses():
    """Given an occupied city defended only by forty-one stationed Faithful.
    When eighty ordinary attackers are repelled in a supplied siege.
    Then the surviving occupation witnesses report observed enemy losses reliably.
    """
    state = occupied_guard()
    seal(state, "p2", "c4", "c5", 80, "counterattack")
    engine.advance_month(state, "review")
    events, audit = engine.advance_month(state, "review")
    assert audit["outcomes"]["counterattack"]["attacker_deaths"] == 2
    letter = next(
        event
        for event in events
        if event["recipient"] == "p1" and event["title"] == "La bataille de Sefra"
    )
    assert "Quelques combattants adverses sont tombés." in letter["body"]
    assert "Nos témoins ne peuvent apprécier" not in letter["body"]


@case("consolidation-ordinary-occupation-observation", REQ)
def test_ordinary_occupation_equipment_observation():
    """Given a city defended only by an occupation contingent with ordinary equipment.
    When a surviving raid army observes the mobilized garrison.
    Then its letter describes ordinary equipment without inventing mixed equipment.
    """
    state = occupied_guard()
    state["cities"]["c4"]["watch"] = 2
    seal(state, "p2", "c4", "c5", 45, "raid", "raid")
    engine.advance_month(state, "review")
    events, audit = engine.advance_month(state, "review")
    assert audit["outcomes"]["raid"]["defender_deaths"] == 1
    letter = next(
        event for event in events if event["recipient"] == "p2" and event["kind"] == "battle"
    )
    assert "équipement ordinaire" in letter["body"]
    assert "équipements variés" not in letter["body"]
