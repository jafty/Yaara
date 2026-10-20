"""Approved October 20 catalogue and seasonal raid contracts.

Earlier suites explicitly retain their saved economy to protect compatibility.
These cases exercise the current creation defaults independently.
"""

from copy import deepcopy
from fractions import Fraction

import pytest

from simulation import engine
from simulation.projections import player_view
from simulation.rules import RuleError
from tests.cases import case
from tests.stubs import FixedRandom

pytestmark = pytest.mark.logic

CATALOGUE = [
    ("irrigation", 1, 300000, 3),
    ("irrigation", 2, 400000, 5),
    ("irrigation", 3, 1500000, 10),
    ("storage", 1, 200000, 3),
    ("storage", 2, 420000, 5),
    ("storage", 3, 900000, 8),
    ("forge", 1, 150000, 3),
    ("forge", 2, 450000, 5),
    ("forge", 3, 1000000, 8),
    ("walls", 1, 200000, 5),
    ("walls", 2, 900000, 10),
    ("walls", 3, 2400000, 20),
    ("watch", 1, 120000, 3),
    ("watch", 2, 360000, 5),
    ("shelter", 1, 150000, 3),
    ("shelter", 2, 450000, 5),
    ("transport", 1, 200000, 4),
    ("transport", 2, 600000, 6),
    ("siege", 1, 300000, 5),
    ("siege", 2, 750000, 8),
    ("repair", 1, 40000, 3),
    ("repair", 2, 180000, 6),
    ("repair", 3, 480000, 8),
]


@case(
    "playability-catalogue", "Owner GO: fixed prices, durations and local completion for every tier"
)
@pytest.mark.parametrize("kind,level,cost,duration", CATALOGUE)
def test_catalogue(kind, level, cost, duration):
    """Given a current city ready for {kind} level {level} with exactly {cost} Measures.
    When its work is sealed and all {duration} construction intervals elapse.
    Then the local payment and completion match the approved quote without pausing production.
    """
    state = engine.new_state(opponents="passive")
    city = state["cities"]["c1"]
    city["stock"] = cost
    city["walls" if kind == "repair" else kind] = level if kind == "repair" else level - 1
    city["damaged"] = kind == "repair"
    order = engine.confirm_order(state, "p1", {"kind": kind, "cities": ["c1"]}, "work")
    assert (order["cost"], order["tasks"][0]["duration"]) == (cost, duration)
    assert order["funding"] == {"c1": cost}
    for _ in range(duration):
        engine.advance_month(state, "catalogue")
    assert state["works"][0]["status"] == "active"
    engine.advance_month(state, "catalogue")
    assert state["works"][0]["status"] == "completed"
    assert city["walls" if kind == "repair" else kind] == level
    assert city["damaged"] is False
    assert city["tax"] > 0 or city["stock"] > 0
    view = player_view(state, "p1")
    assert view["owned_cities"][0]["name"] == city["name"]


@case(
    "playability-yield", "Owner GO: new irrigation produces 100/115/130/200 without monthly payment"
)
@pytest.mark.parametrize("level,expected", [(0, 100000), (1, 115000), (2, 130000), (3, 200000)])
def test_yield(level, expected):
    """Given a current city with irrigation {level} and 1000 present residents.
    When its first Moon closes.
    Then {expected} Measures accrue while spendable reserves remain unchanged.
    """
    state = engine.new_state(opponents="passive")
    state["cities"]["c1"]["irrigation"] = level
    engine.advance_month(state, "yield")
    assert state["cities"]["c1"]["tax"] == expected
    assert state["cities"]["c1"]["stock"] == 600000


@case("playability-local-batch", "Owner GO: mixed-tier orders reserve each local price atomically")
@pytest.mark.parametrize("affordable", [True, False])
def test_batch(affordable):
    """Given two cities quote irrigation at different stages and affordability is {affordable}.
    When their shared decree is sealed.
    Then the exact local amounts are reserved or the entire state stays unchanged.
    """
    state = engine.new_state(opponents="passive")
    state["cities"]["c2"]["irrigation"] = 1
    state["cities"]["c2"]["stock"] = 400000 if affordable else 399999
    before = deepcopy(state)
    if affordable:
        order = engine.confirm_order(
            state, "p1", {"kind": "irrigation", "cities": ["c1", "c2"]}, "batch"
        )
        assert order["funding"] == {"c1": 300000, "c2": 400000}
    else:
        with pytest.raises(RuleError):
            engine.confirm_order(
                state, "p1", {"kind": "irrigation", "cities": ["c1", "c2"]}, "batch"
            )
        assert state == before


@case(
    "playability-seasonal-raid",
    "Owner GO: raids debit exposed accrued harvest and protect two following Moons",
)
@pytest.mark.parametrize(
    "watch,fraction,men,expected_loot",
    [(0, 20, 41, 150000), (1, 20, 41, 150000), (2, 20, 61, 150000)],
)
def test_seasonal_raid(monkeypatch, watch, fraction, men, expected_loot):
    """Given villages with 1200000 accrued Measures at combat and watch level {watch}.
    When {men} equally equipped raiders arrive with a prescribed random draw of {fraction} percent.
    Then crop losses, watch mobilization and the two-Moon respite follow the new rules.
    """
    monkeypatch.setattr(engine, "random_stream", lambda *args: FixedRandom(fraction))
    state = engine.new_state(opponents="passive")
    target = state["cities"]["c4"]
    target["tax"] = 1000000
    target["watch"] = watch
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c1": men}}, "raid"
    )
    engine.advance_month(state, "raid")
    _, audit = engine.advance_month(state, "raid")
    assert audit["encounters"]["raid"] == ([fraction, 40, 60][watch])
    assert target["tax"] == 1000000
    assert target["stock"] == 600000
    assert target["raid_protected_until"] == 5
    assert state["expeditions"][0]["loot"] == expected_loot
    before = target["tax"]
    engine.advance_month(state, "raid")
    assert target["tax"] > before


@case(
    "playability-harvest-raid",
    "Owner GO: the annual crop is raided before payment, never counted twice",
)
def test_harvest_raid(monkeypatch):
    """Given a raid arriving at Moon twelve against a full baseline annual crop.
    When the harvest Moon resolves with a 40-person village defense.
    Then 150000 is carried, 50000 destroyed and only 1000000 enters the victim granary.
    """
    monkeypatch.setattr(engine, "random_stream", lambda *args: FixedRandom(40))
    state = engine.new_state(opponents="passive")
    for _ in range(10):
        engine.advance_month(state, "annual")
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c1": 41}}, "harvest"
    )
    engine.advance_month(state, "annual")
    engine.advance_month(state, "annual")
    assert state["cities"]["c4"]["stock"] == 1600000
    assert state["cities"]["c4"]["tax"] == 0
    assert state["expeditions"][0]["loot"] == 150000


@case(
    "playability-siege-bonus",
    "Owner GO: siege ignores only a share of the wall bonus, never base defense",
)
@pytest.mark.parametrize(
    "wall,damaged,reduction,expected",
    [
        (0, False, Fraction(1, 2), Fraction(1)),
        (3, False, Fraction(1, 2), Fraction(4)),
        (3, True, Fraction(1, 2), Fraction(5, 2)),
        (1, False, Fraction(1, 4), Fraction(7, 4)),
    ],
)
def test_siege_bonus(wall, damaged, reduction, expected):
    """Given fortifications {wall} with damage {damaged} and siege reduction {reduction}.
    When the effective fortification coefficient is calculated.
    Then it equals {expected} and cannot fall below the unfortified defense.
    """
    from simulation.rules import wall_multiplier

    assert wall_multiplier(wall, damaged, reduction, 3) == expected
    assert expected >= 1


@case(
    "playability-starvation",
    "Owner: ×7 walls force siege but cannot prevent capitulation without supplies",
)
@pytest.mark.parametrize(
    "stock,owner,remaining", [(499999, "p1", 0), (500000, "p2", 0), (600000, "p2", 100000)]
)
def test_starvation(stock, owner, remaining):
    """Given 100 defenders behind intact ×7 walls and {stock} Measures for 1000 residents.
    When 200 ordinary attackers arrive with no allied relief.
    Then supplies decide possession as {owner} with {remaining} Measures left despite the walls.
    """
    state = engine.new_state(opponents="passive")
    for origin in ("c1", "c2"):
        state["cities"][origin]["stock"] = 2400000
    target = state["cities"]["c4"]
    target.update(walls=3, stock=stock)
    state["cities"]["c5"]["fideles"] = state["cities"]["c6"]["fideles"] = 0
    engine.confirm_order(
        state,
        "p1",
        {"kind": "capture", "target": "c4", "contributions": {"c1": 100, "c2": 100}},
        "siege",
    )
    engine.advance_month(state, "siege")
    events, _ = engine.advance_month(state, "siege")
    assert target["owner"] == owner
    assert target["stock"] == remaining
    assert target["walls"] == 3
    assert target["damaged"] is False
    assert any(
        "siège" in str(event["title"]).lower() or "pénurie" in str(event["title"]).lower()
        for event in events
    )


@case(
    "playability-mixed-transport",
    "Owner: surviving origin cohorts retain their own transport and equipment",
)
def test_mixed_transport(monkeypatch):
    """Given two differently equipped origins with transport levels two and zero.
    When their raid loses one person after the origins change equipment in transit.
    Then frozen origin characteristics yield 250000 carried Measures without sharing the best bonus.
    """
    monkeypatch.setattr(engine, "random_stream", lambda *args: FixedRandom(40))
    state = engine.new_state(opponents="passive")
    state["cities"]["c1"].update(transport=2, forge=1, siege=1)
    state["cities"]["c2"].update(transport=0, forge=3, siege=2)
    state["cities"]["c4"]["tax"] = 3800000
    engine.confirm_order(
        state,
        "p1",
        {"kind": "raid", "target": "c4", "contributions": {"c1": 21, "c2": 20}},
        "mixed",
    )
    engine.advance_month(state, "mixed")
    mission = state["expeditions"][0]
    assert engine.siege_reduction(mission) == Fraction(811, 2084)
    state["cities"]["c1"].update(transport=0, forge=0, siege=0)
    state["cities"]["c2"].update(transport=2, forge=0, siege=0)
    engine.advance_month(state, "mixed")
    assert mission["cohorts"] == {"c1": 20, "c2": 20}
    assert mission["cohort_equipment"] == {"c1": 110, "c2": 145}
    assert mission["loot"] == 250000
    assert state["cities"]["c4"]["tax"] == 3560000


@case(
    "playability-empty-crop",
    "Owner: empty or fully sheltered crops do not grant a respite or halt production",
)
@pytest.mark.parametrize("initial_tax,shelter", [(0, 0), (200000, 1), (600000, 2)])
def test_empty_crop(monkeypatch, initial_tax, shelter):
    """Given a crop that remains entirely protected at shelter level {shelter}.
    When a victorious raid encounters no exposed resources.
    Then it carries nothing, grants no respite and leaves production running.
    """
    monkeypatch.setattr(engine, "random_stream", lambda *args: FixedRandom(20))
    state = engine.new_state(opponents="passive")
    target = state["cities"]["c4"]
    target.update(tax=initial_tax, shelter=shelter)
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c1": 41}}, "empty"
    )
    engine.advance_month(state, "empty")
    engine.advance_month(state, "empty")
    assert target["tax"] == initial_tax + 200000
    assert target["raid_protected_until"] == 0
    assert state["expeditions"][0]["loot"] == 0


@case(
    "playability-respite-arrival",
    "Owner: a raid may be prepared only when its arrival is outside both protected Moons",
)
@pytest.mark.parametrize("moon,allowed", [(8, False), (9, True), (10, True)])
def test_respite_arrival(moon, allowed):
    """Given villages pillaged at Moon seven and a new order in Moon {moon}.
    When a raid is prepared for arrival one Moon later.
    Then eligibility is {allowed} and a rejected order reserves nothing.
    """
    state = engine.new_state(opponents="passive")
    state["month"] = moon
    state["cities"]["c4"]["raid_protected_until"] = 10
    before = deepcopy(state)
    spec = {"kind": "raid", "target": "c4", "contributions": {"c1": 41}}
    if allowed:
        engine.confirm_order(state, "p1", spec, "again")
        engine.advance_month(state, "again")
        assert state["expeditions"][0]["combat_month"] == moon + 1
        assert state["orders"][0]["status"] == "active"
    else:
        with pytest.raises(RuleError):
            engine.confirm_order(state, "p1", spec, "again")
        assert state == before


@case(
    "playability-work-effect", "Owner: every current building tier describes its exact consequence"
)
@pytest.mark.parametrize("kind,level,cost,duration", CATALOGUE)
def test_work_effect(kind, level, cost, duration):
    """Given the approved {kind} work at level {level}.
    When its decree consequence is rendered.
    Then the description identifies an actual benefit rather than a legacy tier.
    """
    from simulation.narration import work_effect, work_phrase

    assert str(work_effect(kind, level, 3))
    assert str(work_phrase(kind, level, 3))


@case(
    "playability-bot-reserve",
    "Owner: active rivals develop the new catalogue without exhausting opening local funds",
)
@pytest.mark.parametrize("moon", [1, 5, 8, 11, 13])
def test_bot_reserve(moon):
    """Given current active rivals with their initial local reserves at Moon {moon}.
    When they choose ordinary validated orders.
    Then their works leave at least 100000 free Measures locally and early raids are avoided.
    """
    state = engine.new_state()
    state["month"] = moon
    orders = engine.bot_orders(state, "policy")
    assert orders
    for order in orders:
        if order["tasks"]:
            for city, charge in order["funding"].items():
                assert state["cities"][city]["stock"] - charge >= 100000
        if moon == 1:
            assert order["kind"] != "raid"
    engine.assert_invariants(state)


@case(
    "playability-ram-assault",
    "Owner: rams lower only the wall bonus and an assault damages rather than erases walls",
)
def test_ram_assault():
    """Given 50 defenders behind ×7 walls facing 250 attackers equipped with rams.
    When the attackers assault with no relief defenders.
    Then their reduced ×4 opposition falls and captured walls retain a ×4 damaged coefficient.
    """
    from simulation.rules import wall_multiplier

    state = engine.new_state(opponents="passive")
    for origin in ("c1", "c2", "c3"):
        state["cities"][origin].update(stock=2400000, siege=2)
    target = state["cities"]["c4"]
    target.update(walls=3, fideles=50)
    state["cities"]["c5"]["fideles"] = state["cities"]["c6"]["fideles"] = 0
    engine.confirm_order(
        state,
        "p1",
        {"kind": "capture", "target": "c4", "contributions": {"c1": 100, "c2": 100, "c3": 50}},
        "rams",
    )
    engine.advance_month(state, "rams")
    engine.advance_month(state, "rams")
    assert target["owner"] == "p1" and target["walls"] == 3 and target["damaged"]
    assert wall_multiplier(3, True, economy_version=3) == 4
    assert engine.work_spec(state, target, "repair")["cost"] == 480000


@case(
    "playability-bot-private-state",
    "Owner: seasonal rival decisions never consult hidden enemy resources or infrastructure",
)
@pytest.mark.parametrize("moon", [1, 5, 8, 11])
def test_current_bot_privacy(moon):
    """Given otherwise identical current reigns with different private player resources.
    When active rivals choose their orders in Moon {moon}.
    Then all accepted orders remain identical.
    """
    state = engine.new_state()
    state["month"] = moon
    other = deepcopy(state)
    for city in other["cities"].values():
        if city["owner"] == "p1":
            city.update(stock=0, fideles=999, forge=3, watch=2, shelter=2, tax=5000000)
    assert engine.bot_orders(state, "private") == engine.bot_orders(other, "private")


@case(
    "playability-bot-constrained",
    "Owner: seasonal rivals cannot raid without troops or spend reserves they lack",
)
@pytest.mark.parametrize("constraint", ["no-troops", "no-funds", "no-targets"])
def test_bot_constrained(constraint):
    """Given a current rival with the {constraint} constraint during raid season.
    When it chooses a validated order.
    Then it makes no impossible military commitment and never changes state without an accepted order.
    """
    state = engine.new_state()
    state["month"] = 5
    state["players"]["p3"]["bot"] = False
    for city in engine.owned_cities(state, "p2"):
        if constraint == "no-troops":
            city["fideles"] = 0
        if constraint == "no-funds":
            city["stock"] = 0
    if constraint == "no-targets":
        state["links"] = []
    before = deepcopy(state)
    orders = engine.bot_orders(state, "constraint")
    if constraint == "no-funds":
        assert orders == [] and state == before
    else:
        assert orders and all(order["kind"] not in ("raid", "capture") for order in orders)


@case(
    "playability-repair-choice",
    "Owner: damaged walls retain half their bonus and the repair quote explains what is restored",
)
@pytest.mark.parametrize(
    "level,before,after,cost,duration",
    [(1, 50, 100, 40000, 3), (2, 150, 300, 180000, 6), (3, 300, 600, 480000, 8)],
)
def test_repair_choice(level, before, after, cost, duration):
    """Given damaged fortifications at level {level}.
    When their owner considers a repair.
    Then the quote exposes restoration from bonus {before} to {after}, cost {cost} and duration {duration}.
    """
    state = engine.new_state(opponents="passive")
    state["cities"]["c1"].update(walls=level, damaged=True)
    action = next(
        row for row in player_view(state, "p1")["work_actions"] if row["kind"] == "repair"
    )
    quote = action["cities"][0]
    assert quote["cost"] == cost and quote["duration"] == duration
    assert str(quote["benefit"]) == f"Bonus défensif local restauré : +{before} % → +{after} %."
    assert state["cities"]["c1"]["damaged"] and state["cities"]["c1"]["stock"] == 600000
