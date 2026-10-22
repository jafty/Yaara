"""Independent state-transition contracts for the October 22 increment."""

from copy import deepcopy

import pytest

from simulation import engine
from simulation.rules import RuleError
from tests.cases import case

pytestmark = pytest.mark.logic


def realm():
    return engine.new_state(opponents="passive", economy_version=4)


@case("strategy-local-fees", "Prompt C: one shared fixed fee with exact local debits")
def test_local_fees():
    """Given three origins each providing twenty Faithful for one raid.
    When the decree is sealed and departs.
    Then 65000 Measures are paid once with the indivisible fee assigned by city order.
    """
    state = realm()
    order = engine.confirm_order(
        state,
        "p1",
        {"kind": "raid", "target": "c4", "contributions": {"c1": 20, "c2": 20, "c3": 20}},
        "raid",
    )
    assert order["funding"] == {"c1": 21667, "c2": 21667, "c3": 21666}
    engine.advance_month(state, "fees")
    assert [state["cities"][key]["stock"] for key in ("c1", "c2", "c3")] == [878333, 878333, 878334]


@case(
    "strategy-work-horizon",
    "Prompt B: finish at the configured end is allowed, beyond it is rejected atomically",
)
@pytest.mark.parametrize("moon,allowed", [(21, True), (22, False)])
def test_work_horizon(moon, allowed):
    """Given a 24-Moon reign at Moon {moon} and a three-Moon irrigation project.
    When the decree is sealed.
    Then acceptance is {allowed} and a rejected decree changes no state.
    """
    state = realm()
    state["config"]["reign_months"] = 24
    state["month"] = moon
    before = deepcopy(state)
    if allowed:
        assert (
            engine.confirm_order(state, "p1", {"kind": "irrigation", "cities": ["c1"]}, "late")[
                "cost"
            ]
            == 300000
        )
    else:
        with pytest.raises(RuleError, match="règne"):
            engine.confirm_order(state, "p1", {"kind": "irrigation", "cities": ["c1"]}, "late")
        assert state == before


@case("strategy-repair-quote", "Prompt F/H: repairs restore existing assets using the local team")
@pytest.mark.parametrize(
    "kind,level,cost,duration",
    [
        ("repair_watch", 1, 24000, 2),
        ("repair_watch", 2, 72000, 2),
        ("repair_shelter", 1, 30000, 2),
        ("repair_shelter", 2, 90000, 2),
        ("repair", 0, 20000, 2),
        ("repair", 1, 40000, 3),
        ("repair", 2, 180000, 6),
        ("repair", 3, 480000, 8),
    ],
)
def test_repair(kind, level, cost, duration):
    """Given damaged {kind} at built level {level} and free local workers.
    When its {cost}-Measure repair completes after {duration} Moons.
    Then the built level is preserved and its full effectiveness is restored.
    """
    state = realm()
    city = state["cities"]["c1"]
    family = "walls" if kind == "repair" else kind.removeprefix("repair_")
    city[family] = level
    if family == "walls":
        city.update(integrity=50, damaged=True)
    else:
        city["damaged_works"] = [family]
    order = engine.confirm_order(state, "p1", {"kind": kind, "cities": ["c1"]}, "repair")
    assert (order["cost"], order["tasks"][0]["duration"]) == (cost, duration)
    assert "c1" in engine.busy_cities(state)
    for _ in range(duration + 1):
        engine.advance_month(state, "repair")
    assert city[family] == level
    assert city["integrity"] == 100
    assert not city["damaged_works"]
    assert "c1" not in engine.busy_cities(state)


@case(
    "strategy-repair-rejections",
    "Prompt F/H: intact repairs and damaged upgrades are rejected without reservations",
)
@pytest.mark.parametrize(
    "kind,damage",
    [
        ("repair", False),
        ("repair_watch", False),
        ("repair_shelter", False),
        ("watch", True),
        ("shelter", True),
        ("walls", True),
    ],
)
def test_repair_rejections(kind, damage):
    """Given an asset with damage {damage} for action {kind}.
    When the incompatible repair or upgrade is requested.
    Then the decree is rejected without changing people, money or team reservations.
    """
    state = realm()
    city = state["cities"]["c1"]
    city.update(
        watch=1,
        shelter=1,
        walls=1,
        integrity=50 if damage else 100,
        damaged=damage,
        damaged_works=["watch", "shelter"] if damage else [],
    )
    before = deepcopy(state)
    with pytest.raises(RuleError):
        engine.confirm_order(state, "p1", {"kind": kind, "cities": ["c1"]}, "bad")
    assert state == before


@case("strategy-convoy-fees", "Prompt I: cargo plus ceiling-rounded transport fees, arrival N+2")
@pytest.mark.parametrize(
    "level,cargo,fee", [(0, 101, 11), (1, 101, 8), (2, 101, 6), (0, 500000, 50000)]
)
def test_convoy(level, cargo, fee):
    """Given transport {level} and a convoy of {cargo} Measures between friendly connected cities.
    When the convoy departs and arrives two Moons later.
    Then only the cargo arrives and the additional fee is exactly {fee}.
    """
    state = realm()
    state["cities"]["c1"]["transport"] = level
    order = engine.confirm_order(
        state, "p1", {"kind": "convoy", "origin": "c1", "target": "c2", "cargo": cargo}, "convoy"
    )
    assert order["cost"] == cargo + fee
    engine.advance_month(state, "convoy")
    assert state["cities"]["c1"]["stock"] == 900000 - cargo - fee
    assert state["cities"]["c2"]["stock"] == 900000
    engine.advance_month(state, "convoy")
    assert state["cities"]["c2"]["stock"] == 900000
    engine.advance_month(state, "convoy")
    assert state["cities"]["c2"]["stock"] == 900000 + cargo
    assert order["status"] == "completed"


@case(
    "strategy-convoy-invalid",
    "Prompt I: reject invalid endpoints, cargo, route and funds atomically",
)
@pytest.mark.parametrize(
    "change",
    [
        "zero",
        "negative",
        "too-large",
        "boolean",
        "fraction",
        "foreign-origin",
        "foreign-target",
        "same-city",
        "missing-origin",
        "missing-target",
        "disconnected",
        "poor",
        "legacy",
        "duplicate",
    ],
)
def test_invalid_convoy(change):
    """Given a convoy request with defect {change}.
    When that request is confirmed.
    Then a rule rejection leaves the complete state unchanged.
    """
    state = realm()
    spec = {"kind": "convoy", "origin": "c1", "target": "c2", "cargo": 100000}
    if change in ("zero", "negative", "too-large", "boolean", "fraction"):
        spec["cargo"] = {
            "zero": 0,
            "negative": -1,
            "too-large": 500001,
            "boolean": True,
            "fraction": 1.5,
        }[change]
    elif change == "foreign-origin":
        spec["origin"] = "c4"
    elif change == "foreign-target":
        spec["target"] = "c4"
    elif change == "same-city":
        spec["target"] = "c1"
    elif change == "missing-origin":
        spec["origin"] = "missing"
    elif change == "missing-target":
        spec["target"] = "missing"
    elif change == "disconnected":
        state["links"] = []
    elif change == "poor":
        state["cities"]["c1"]["stock"] = 109999
    elif change == "legacy":
        state["economy_version"] = 3
    else:
        engine.confirm_order(state, "p1", spec, "first")
    before = deepcopy(state)
    with pytest.raises(RuleError):
        engine.confirm_order(state, "p1", spec, "invalid")
    assert state == before


@case(
    "strategy-convoy-return",
    "Prompt I: reroute once, verify arrival ownership, never duplicate cargo",
)
@pytest.mark.parametrize(
    "scenario,credited",
    [
        ("destination-lost", "c1"),
        ("origin-lost", "c2"),
        ("no-refuge", None),
        ("refuge-lost-in-transit", None),
        ("route-lost-after-departure", "c2"),
        ("overflow", "c2"),
    ],
)
def test_convoy_return(scenario, credited):
    """Given a departed resource convoy affected by {scenario}.
    When its destination and any one-Moon return are resolved twice.
    Then only {credited} can receive the cargo and no resources are duplicated.
    """
    state = realm()
    target = "c3" if scenario in ("origin-lost", "no-refuge", "refuge-lost-in-transit") else "c2"
    engine.confirm_order(
        state, "p1", {"kind": "convoy", "origin": "c1", "target": target, "cargo": 100000}, "convoy"
    )
    engine.advance_month(state, "route")
    if scenario == "route-lost-after-departure":
        state["links"] = []
    elif scenario == "overflow":
        state["cities"]["c2"]["stock"] = 2399990
    else:
        state["cities"][target]["owner"] = "p2"
        if scenario != "destination-lost":
            state["cities"]["c1"]["owner"] = "p2"
        if scenario == "no-refuge":
            state["cities"]["c2"]["owner"] = "p2"
    engine.advance_month(state, "route")
    engine.advance_month(state, "route")
    if scenario == "refuge-lost-in-transit":
        state["cities"]["c2"]["owner"] = "p2"
    engine.advance_month(state, "route")
    assert state["orders"][0]["status"] == "completed"
    assert state["cities"]["c1"]["stock"] == (890000 if credited == "c1" else 790000)
    assert state["cities"]["c2"]["stock"] == (
        2400000 if scenario == "overflow" else 1000000 if credited == "c2" else 900000
    )
    before = [city["stock"] for city in state["cities"].values()]
    engine.return_convoys(state, [])
    assert [city["stock"] for city in state["cities"].values()] == before


@case(
    "strategy-refuge-return",
    "Prompt J: absent contingents stay with their house or demobilize, never join the enemy army",
)
@pytest.mark.parametrize(
    "scenario",
    [
        "friendly-origin",
        "captured-origin",
        "lost-refuge",
        "recaptured-origin",
        "death-while-detached",
        "isolated-origin",
    ],
)
def test_refuge_return(scenario):
    """Given twenty departing Faithful whose origin is affected by {scenario}.
    When their surviving contingent returns after any diversion.
    Then population is counted once and no returning soldier becomes an available enemy Faithful.
    """
    state = realm()
    if scenario == "isolated-origin":
        state["links"] = [["c1", "c4"]]
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c1": 20}}, "men"
    )
    engine.advance_month(state, "refuge")
    mission = state["expeditions"][0]
    mission.update(status="returning", loot=10000)
    state["orders"][0]["status"] = "returning"
    if scenario != "friendly-origin":
        engine.detach_absent_contingents(state, "c1")
        state["cities"]["c1"]["owner"] = "p2"
        assert state["cities"]["c1"]["population"] == 980
        assert engine.absent(state, "c1") == 0
    if scenario == "recaptured-origin":
        state["cities"]["c1"]["owner"] = "p1"
    if scenario == "death-while-detached":
        engine.lose_attackers(state, mission, 1, sorted(state["cities"]))
    engine.advance_month(state, "refuge")
    engine.advance_month(state, "refuge")
    if scenario == "lost-refuge":
        state["cities"]["c2"]["owner"] = "p2"
    engine.advance_month(state, "refuge")
    expected = 8999 if scenario == "death-while-detached" else 9000
    assert sum(city["population"] for city in state["cities"].values()) == expected
    if scenario in ("friendly-origin", "recaptured-origin"):
        assert state["cities"]["c1"]["fideles"] == 100
    else:
        assert state["cities"]["c1"]["fideles"] == 80
    if scenario in ("captured-origin", "death-while-detached"):
        assert state["cities"]["c2"]["fideles"] == (
            119 if scenario == "death-while-detached" else 120
        )
    assert mission["status"] == "completed"
    assert mission["loot"] == 0
    before = deepcopy(state)
    engine.return_expeditions(state, [])
    assert state == before


@case(
    "strategy-departure-revalidation",
    "Prompt B/I: routes, damage and reign end are rechecked before debit",
)
@pytest.mark.parametrize("change", ["route", "horizon", "damage"])
def test_departure_revalidation(change):
    """Given a sealed decree whose departure prerequisites change through {change}.
    When its scheduled Moon closes.
    Then the order is invalidated and all local funds and teams are released without debit.
    """
    state = realm()
    spec = (
        {"kind": "convoy", "origin": "c1", "target": "c2", "cargo": 100000}
        if change == "route"
        else {"kind": "watch", "cities": ["c1"]}
    )
    order = engine.confirm_order(state, "p1", spec, "revalidate")
    if change == "route":
        state["links"] = []
    elif change == "horizon":
        state["config"]["reign_months"] = 2
    else:
        state["cities"]["c1"].update(watch=1, damaged_works=["watch"])
    engine.advance_month(state, "revalidate")
    assert order["status"] == "invalidated"
    assert state["cities"]["c1"]["stock"] == 900000
    assert not state["works"] and not state["convoys"]
    assert engine.reservations(state)[0]["c1"] == 0


@case(
    "strategy-mixed-return",
    "Prompt J: separate origins settle on their own arrival date without double counting",
)
def test_mixed_return():
    """Given a two-origin expedition with one captured origin and 20000 Measures of loot.
    When one contingent returns normally and the other reaches its refuge one Moon later.
    Then their forty survivors and loot are credited exactly once despite the split return.
    """
    state = realm()
    engine.confirm_order(
        state,
        "p1",
        {"kind": "raid", "target": "c4", "contributions": {"c1": 20, "c2": 20}},
        "mixed",
    )
    engine.advance_month(state, "mixed")
    mission = state["expeditions"][0]
    mission.update(status="returning", loot=20000)
    state["orders"][0]["status"] = "returning"
    engine.detach_absent_contingents(state, "c1")
    state["cities"]["c1"]["owner"] = "p2"
    engine.advance_month(state, "mixed")
    engine.advance_month(state, "mixed")
    assert state["cities"]["c2"]["fideles"] == 100
    assert engine.absent(state, "c2") == 0
    engine.advance_month(state, "mixed")
    assert state["cities"]["c2"]["fideles"] == 120
    assert state["cities"]["c2"]["stock"] == 897500
    assert sum(city["population"] for city in state["cities"].values()) == 9000
    assert mission["recovered_loot"] == 20000


@case(
    "strategy-upgrade-damaged-in-progress",
    "Prompt F: damage does not cancel an active upgrade or grant free repair",
)
def test_damaged_upgrade():
    """Given a watch upgrade already paid and underway.
    When the existing watch is damaged before the upgrade finishes.
    Then completion increases the built level but retains the damage until a separate repair.
    """
    state = realm()
    city = state["cities"]["c1"]
    city["watch"] = 1
    engine.confirm_order(state, "p1", {"kind": "watch", "cities": ["c1"]}, "upgrade")
    engine.advance_month(state, "upgrade")
    city["damaged_works"] = ["watch"]
    for _ in range(5):
        engine.advance_month(state, "upgrade")
    assert city["watch"] == 2 and city["damaged_works"] == ["watch"]
    assert state["works"][0]["status"] == "completed"


@case(
    "strategy-opening-stock",
    "Owner October 22: more opening choices with historical balances preserved",
)
@pytest.mark.parametrize("economy,stock", [(3, 600000), (4, 900000)])
def test_opening_stock(economy, stock):
    """Given a new reign using saved economic rules {economy}.
    When its starting resources are initialized.
    Then every city has {stock} Measures and no accrued levy or committed order.
    """
    state = engine.new_state(economy_version=economy)
    assert all(city["stock"] == stock and city["tax"] == 0 for city in state["cities"].values())
    assert state["orders"] == []
