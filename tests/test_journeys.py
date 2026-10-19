from copy import deepcopy

import pytest

from simulation.engine import (
    absent,
    active_targets,
    advance_month,
    assert_invariants,
    bot_orders,
    confirm_order,
    new_state,
)
from simulation.rules import RuleError
from tests.builders import rich_state
from tests.cases import case

pytestmark = pytest.mark.journey


@case(
    "raid-departure-absence-death-and-return-reconcile",
    "Design §26.2–26.3: additional journey — raid departure absence death and return reconcile",
)
def test_raid_departure_absence_death_and_return_reconcile():
    state = new_state(
        "V0", opponents="passive", calendar_version=1, map_version=1, economy_version=1
    )
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


@case(
    "capture-retains-tax-work-and-transfers-local-survivors",
    "Design §26.2–26.3: additional journey — capture retains tax work and transfers local survivors",
)
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


@case(
    "relief-keeps-its-command-when-both-frontier-origins-are-captured",
    "Design §26.2–26.3: additional journey — relief keeps its command when both frontier origins are captured",
)
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


@case(
    "raid-resource-conservation-including-loot-in-transit",
    "Design §26.2–26.3: additional journey — raid resource conservation including loot in transit",
)
def test_raid_resource_conservation_including_loot_in_transit():
    state = new_state(
        "V0", opponents="passive", calendar_version=1, map_version=1, economy_version=1
    )
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


@case(
    "upgrade-keeps-damage-and-repair-restores-existing-level",
    "Design §26.2–26.3: additional journey — upgrade keeps damage and repair restores existing level",
)
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


@case(
    "full-reigns-are-deterministic-and-conserve-population",
    "Design §26.2–26.3: additional journey — full reigns are deterministic and conserve population",
)
@pytest.mark.parametrize("version", ["V0", "V1"])
@pytest.mark.parametrize("seed", ["desert", "oasis", "clay"])
def test_full_reigns_are_deterministic_and_conserve_population(version, seed):
    state = new_state(version, calendar_version=1, map_version=1, economy_version=1)
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
