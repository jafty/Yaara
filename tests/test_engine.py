from copy import deepcopy

import pytest

from simulation.engine import (
    absent,
    active_targets,
    advance_month,
    assert_invariants,
    bot_orders,
    cancel_order,
    confirm_order,
    eligible_origins,
    new_state,
    relief_allocations,
    reservations,
)
from simulation.rules import RuleError


def rich_state(version="V1"):
    state = new_state(version, opponents="passive")
    for city in state["cities"].values():
        city["stock"] = 2_400_000
    return state


def test_initial_capture_rejected_without_partial_reservations():
    state = new_state()
    before = deepcopy(state)
    with pytest.raises(RuleError, match="dépense"):
        confirm_order(
            state, "p1", {"kind": "capture", "target": "c4", "contributions": {"c3": 80}}, "one"
        )
    assert state == before


def test_target_exclusivity_cancellation_and_duplicate_delivery():
    state = new_state()
    spec = {"kind": "raid", "target": "c4", "contributions": [["c3", 20], ["c3", 25]]}
    order = confirm_order(state, "p1", spec, "one")
    assert order["cost"] == 132500
    assert order["contributions"] == {"c3": 45}
    assert reservations(state)[1]["c3"] == 45
    with pytest.raises(RuleError, match="déjà engagée"):
        confirm_order(state, "p1", spec, "two")
    assert sum(reservations(state)[0].values()) == 132500
    cancel_order(state, "p1", "one")
    assert active_targets(state) == {}
    assert confirm_order(state, "p1", spec, "one")["status"] == "cancelled"
    confirm_order(state, "p1", spec, "two")
    assert active_targets(state) == {"c4": "two"}


def test_v0_confirmation_is_final():
    state = new_state("V0")
    confirm_order(state, "p1", {"kind": "walls", "cities": ["c1"]}, "wall")
    with pytest.raises(RuleError, match="définitive"):
        cancel_order(state, "p1", "wall")


def test_batch_work_is_atomic_and_slots_are_reserved():
    state = new_state()
    before = deepcopy(state)
    with pytest.raises(RuleError):
        confirm_order(state, "p1", {"kind": "walls", "cities": ["c1", "c2"]}, "bad")
    assert state == before
    confirm_order(state, "p1", {"kind": "storage", "cities": ["c1", "c2"]}, "batch")
    with pytest.raises(RuleError, match="équipes"):
        confirm_order(state, "p1", {"kind": "walls", "cities": ["c1"]}, "conflict")
    assert sum(reservations(state)[0].values()) == 1_000_000


def test_monthly_tax_and_construction_timing_match_document():
    state = rich_state("V0")
    for city in state["cities"].values():
        city["stock"] = 800_000
    confirm_order(state, "p1", {"kind": "irrigation", "cities": ["c1"]}, "canals")
    for _ in range(6):
        advance_month(state, "example")
    assert state["cities"]["c1"]["irrigation"] == 0
    advance_month(state, "example")
    assert state["cities"]["c1"]["irrigation"] == 1
    assert state["cities"]["c1"]["tax"] == 700000
    for _ in range(5):
        advance_month(state, "example")
    assert state["cities"]["c1"]["stock"] == 1_700_000
    assert sum(state["cities"][city_id]["stock"] for city_id in ("c1", "c2", "c3")) == 4_100_000


def test_raid_departure_absence_death_and_return_reconcile():
    state = new_state("V0", opponents="passive")
    state["cities"]["c4"]["stock"] = 1_200_000
    confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c3": 45}}, "raid"
    )
    assert state["cities"]["c3"]["fideles"] == 100
    advance_month(state, "seed")
    assert absent(state, "c3") == 45
    assert state["cities"]["c3"]["tax"] == 100000
    advance_month(state, "seed")
    assert state["cities"]["c3"]["population"] == 999
    assert absent(state, "c3") == 44
    assert active_targets(state) == {}
    assert state["cities"]["c4"]["raid_protected_until"] == 14
    with pytest.raises(RuleError, match="pillage"):
        confirm_order(
            state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c2": 45}}, "protected"
        )
    advance_month(state, "seed")
    assert absent(state, "c3") == 0
    assert state["cities"]["c3"]["fideles"] == 99
    assert state["cities"]["c3"]["tax"] == 291000
    assert state["expeditions"][0]["status"] == "completed"
    assert_invariants(state)


def test_disconnected_origins_must_touch_same_frontier():
    state = new_state()
    state["cities"]["c2"]["owner"] = "p2"
    assert eligible_origins(state, "p1", "c2") == {"c1", "c3"}
    assert eligible_origins(state, "p1", "c4") == {"c3"}


def test_relief_on_two_fronts_and_threat_cap():
    state = new_state()
    missions = [
        {
            "id": "a",
            "kind": "capture",
            "actor": "p2",
            "target": "c1",
            "cohorts": {"c4": 220},
            "combativity": 100,
        },
        {
            "id": "c",
            "kind": "capture",
            "actor": "p3",
            "target": "c3",
            "cohorts": {"c7": 220},
            "combativity": 100,
        },
    ]
    allocations = relief_allocations(state, missions, sorted(state["cities"]))
    assert sum(item["count"] for item in allocations if item["mission"] == "a") == 30
    assert sum(item["count"] for item in allocations if item["origin"] == "c2") == 20
    missions[0]["cohorts"] = {"c4": 1}
    allocations = relief_allocations(state, missions[:1], sorted(state["cities"]))
    assert sum(item["count"] for item in allocations) == 1


def test_captured_origin_receives_survivors_and_loot():
    state = new_state("V1", opponents="passive")
    confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c3": 45}}, "raid"
    )
    advance_month(state, "seed")
    advance_month(state, "seed")
    state["cities"]["c3"]["owner"] = "p2"
    stock = state["cities"]["c3"]["stock"]
    loot = state["expeditions"][0]["loot"]
    events, _ = advance_month(state, "seed")
    assert state["cities"]["c3"]["fideles"] == 99
    assert state["cities"]["c3"]["stock"] == stock + loot
    assert any(event["recipient"] == "p2" and event["kind"] == "return" for event in events)


def test_capture_retains_tax_work_and_transfers_local_survivors():
    state = rich_state()
    state["cities"]["c4"]["walls"] = 1
    confirm_order(state, "p2", {"kind": "storage", "cities": ["c4"]}, "store")
    confirm_order(
        state,
        "p1",
        {"kind": "capture", "target": "c4", "contributions": {"c1": 80, "c2": 80, "c3": 60}},
        "attack",
    )
    advance_month(state, "seed")
    advance_month(state, "seed")
    city = state["cities"]["c4"]
    assert city["owner"] == "p1"
    assert city["tax"] == 200000
    assert city["damaged"]
    assert city["fideles"] == 88
    assert sum(state["expeditions"][0]["cohorts"].values()) == 202
    for _ in range(3):
        advance_month(state, "seed")
    assert city["storage"] == 1


def test_annual_growth_renewal_and_absent_ceiling():
    state = new_state("V1", opponents="passive")
    for _ in range(11):
        advance_month(state, "seed")
    confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c3": 45}}, "late"
    )
    advance_month(state, "seed")
    city = state["cities"]["c3"]
    assert city["population"] == 1005
    assert city["fideles"] + absent(state, "c3") == 100
    assert city["tax"] == 0


def test_relief_keeps_its_command_when_both_frontier_origins_are_captured():
    state = rich_state("V0")
    confirm_order(
        state,
        "p2",
        {"kind": "capture", "target": "c3", "contributions": {"c4": 80, "c5": 80, "c6": 60}},
        "east",
    )
    confirm_order(
        state,
        "p3",
        {"kind": "capture", "target": "c1", "contributions": {"c7": 80, "c8": 80, "c9": 60}},
        "west",
    )
    advance_month(state, "two-fronts")
    events, trace = advance_month(state, "two-fronts")
    assert state["cities"]["c1"]["owner"] == "p3"
    assert state["cities"]["c3"]["owner"] == "p2"
    assert all(item["actor"] == "p1" for item in trace["relief"])
    assert sum(item["count"] for item in trace["relief"] if item["mission"] == "east") == 30
    assert sum(item["count"] for item in trace["relief"] if item["mission"] == "west") == 30
    # 80 locals fight, 20 are abroad; two locals die. All 20 relief survive
    # and join the new owner only after both battles have been resolved.
    assert state["cities"]["c1"]["fideles"] == 98
    assert state["cities"]["c3"]["fideles"] == 98
    assert state["cities"]["c2"]["fideles"] == 100
    assert sum(event["recipient"] == "p1" and event["kind"] == "battle" for event in events) == 2


def test_raid_resource_conservation_including_loot_in_transit():
    state = new_state("V0", opponents="passive")
    initial = sum(city["stock"] for city in state["cities"].values())
    confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c3": 45}}, "raid"
    )
    assert sum(city["stock"] for city in state["cities"].values()) == initial
    advance_month(state, "conservation")
    assert sum(city["stock"] for city in state["cities"].values()) == initial - 132500
    advance_month(state, "conservation")
    # 25% exposed, 20% of that destroyed: 30,000. Loot is merely moved.
    assert (
        sum(city["stock"] for city in state["cities"].values()) + state["expeditions"][0]["loot"]
        == initial - 132500 - 30000
    )
    advance_month(state, "conservation")
    assert sum(city["stock"] for city in state["cities"].values()) == initial - 132500 - 30000


def test_upgrade_keeps_damage_and_repair_restores_existing_level():
    state = rich_state()
    state["cities"]["c1"].update({"walls": 1, "storage": 2, "stock": 6_000_000})
    confirm_order(state, "p1", {"kind": "walls", "cities": ["c1"]}, "great-wall")
    advance_month(state, "walls")
    state["cities"]["c1"]["damaged"] = True
    for _ in range(20):
        advance_month(state, "walls")
    assert state["cities"]["c1"]["walls"] == 2
    assert state["cities"]["c1"]["damaged"]
    confirm_order(state, "p1", {"kind": "repair", "cities": ["c1"]}, "repair")
    for _ in range(7):
        advance_month(state, "walls")
    assert not state["cities"]["c1"]["damaged"]
    assert state["cities"]["c1"]["walls"] == 2


@pytest.mark.parametrize("version", ["V0", "V1"])
@pytest.mark.parametrize("seed", ["desert", "oasis", "clay"])
def test_full_reigns_are_deterministic_and_conserve_population(version, seed):
    state = new_state(version)
    state["players"]["p1"]["bot"] = True
    replica = deepcopy(state)
    for game in (state, replica):
        previous_population = 9000
        previous_deaths = 0
        for _ in range(120):
            if game["status"] == "finished":
                break
            bot_orders(game, seed)
            advance_month(game, seed)
            deaths = sum(
                city["military_deaths"] + city["civilian_deaths"]
                for city in game["cities"].values()
            )
            population = sum(city["population"] for city in game["cities"].values())
            if version == "V0" or game["month"] % 12:
                assert population == previous_population - (deaths - previous_deaths)
            previous_population, previous_deaths = population, deaths
        assert game["status"] == "finished"
        frozen = deepcopy(game)
        with pytest.raises(RuleError):
            advance_month(game, seed)
        assert game == frozen
    assert state == replica
