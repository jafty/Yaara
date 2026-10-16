from copy import deepcopy

import pytest

from simulation.engine import (
    absent,
    active_targets,
    advance_month,
    cancel_order,
    confirm_order,
    eligible_origins,
    new_state,
    relief_allocations,
    reservations,
)
from simulation.rules import RuleError
from tests.builders import rich_state
from tests.cases import case

pytestmark = pytest.mark.logic


@case(
    "initial-capture-rejected-without-partial-reservations",
    "Design §26.2 Capture initiale impossible: initial funds cannot finance minimum capture",
)
def test_initial_capture_rejected_without_partial_reservations():
    """Given the initial realm and an eighty-person capture order.
    When the unaffordable order is confirmed.
    Then the expense is rejected and the entire state remains unchanged.
    """
    state = new_state(calendar_version=1)
    before = deepcopy(state)
    with pytest.raises(RuleError, match="dépense"):
        confirm_order(
            state, "p1", {"kind": "capture", "target": "c4", "contributions": {"c3": 80}}, "one"
        )
    assert state == before


@pytest.fixture
def reserved_raid():
    state = new_state(calendar_version=1)
    spec = {"kind": "raid", "target": "c4", "contributions": [["c3", 20], ["c3", 25]]}
    confirm_order(state, "p1", spec, "one")
    return state, spec


@case(
    "duplicate-origins-are-normalized",
    "Design orders: repeated origins contribute once after amounts are combined",
)
def test_duplicate_origins_are_normalized(reserved_raid):
    """Given a raid listing the same origin twice for twenty and twenty-five people.
    When the order is confirmed.
    Then forty-five people and 132500 Measures are reserved exactly once.
    """
    state, _ = reserved_raid
    order = state["orders"][0]
    assert order["cost"] == 132500
    assert order["contributions"] == {"c3": 45}
    assert reservations(state)[1]["c3"] == 45


@case(
    "target-exclusivity-rejects-without-mutation",
    "Design §26.2 Cible exclusive: a competing target claim costs nothing",
)
def test_target_exclusivity_rejects_without_mutation(reserved_raid):
    """Given a target already reserved by a raid.
    When another order claims the same target.
    Then the order is rejected without changing state or existing reservations.
    """
    state, spec = reserved_raid
    before = deepcopy(state)
    with pytest.raises(RuleError, match="déjà engagée"):
        confirm_order(state, "p1", spec, "two")
    assert state == before
    assert sum(reservations(state)[0].values()) == 132500


@case(
    "cancellation-releases-reservations",
    "Design §26.2 Cible exclusive: V1 cancellation releases target, funds and people",
)
def test_cancellation_releases_reservations(reserved_raid):
    """Given a confirmed V1 raid.
    When the player cancels it before departure.
    Then the target, funds and people are all released.
    """
    state, _ = reserved_raid
    cancel_order(state, "p1", "one")
    assert active_targets(state) == {}
    assert sum(reservations(state)[0].values()) == 0
    assert sum(reservations(state)[1].values()) == 0


@case(
    "replaying-cancelled-order-cannot-revive-it",
    "Design §26.2 Panne: replaying a cancelled command preserves its result",
)
def test_replaying_cancelled_order_cannot_revive_it(reserved_raid):
    """Given a cancelled raid and its original request identifier.
    When confirmation is retried.
    Then the cancelled result is returned without any state change.
    """
    state, spec = reserved_raid
    cancel_order(state, "p1", "one")
    before = deepcopy(state)
    assert confirm_order(state, "p1", spec, "one")["status"] == "cancelled"
    assert state == before


@case(
    "new-order-can-take-released-target",
    "Design §26.2 Cible exclusive: a new command can claim a released target",
)
def test_new_order_can_take_released_target(reserved_raid):
    """Given a cancelled raid whose target is released.
    When a different request confirms a raid on that target.
    Then the new request owns the target engagement.
    """
    state, spec = reserved_raid
    cancel_order(state, "p1", "one")
    confirm_order(state, "p1", spec, "two")
    assert active_targets(state) == {"c4": "two"}


@case("v0-confirmation-is-final", "Design V0: a sealed order cannot be cancelled")
def test_v0_confirmation_is_final():
    """Given a confirmed V0 wall order.
    When the player attempts cancellation.
    Then the final confirmation is rejected for cancellation.
    """
    state = new_state("V0", calendar_version=1)
    confirm_order(state, "p1", {"kind": "walls", "cities": ["c1"]}, "wall")
    with pytest.raises(RuleError, match="définitive"):
        cancel_order(state, "p1", "wall")


@case(
    "unaffordable-batch-is-atomic",
    "Design §26.2 Stocks locaux: an unaffordable batch has no partial reservations",
)
def test_unaffordable_batch_is_atomic():
    """Given initial reserves and a two-city wall project.
    When the unaffordable batch is confirmed.
    Then the entire request is rejected without state mutation.
    """
    state = new_state(calendar_version=1)
    before = deepcopy(state)
    with pytest.raises(RuleError):
        confirm_order(state, "p1", {"kind": "walls", "cities": ["c1", "c2"]}, "bad")
    assert state == before


@case(
    "affordable-batch-reserves-total-price",
    "Design §26.3: batch reservations reduce availability without spending stock",
)
def test_affordable_batch_reserves_total_price():
    """Given initial reserves and a two-city granary project.
    When the affordable batch is confirmed.
    Then 1000000 Measures are reserved and total stocks remain 5400000.
    """
    state = new_state(calendar_version=1)
    confirm_order(state, "p1", {"kind": "storage", "cities": ["c1", "c2"]}, "batch")
    assert sum(reservations(state)[0].values()) == 1000000
    assert sum(city["stock"] for city in state["cities"].values()) == 5400000


@case(
    "busy-work-slot-rejects-without-mutation",
    "Design §26.2 Double chantier: one slot per city, rejection without side effects",
)
def test_busy_work_slot_rejects_without_mutation():
    """Given a city whose teams are reserved for a granary.
    When a wall order requests the same teams.
    Then the conflict is rejected without changing the existing state.
    """
    state = new_state(calendar_version=1)
    confirm_order(state, "p1", {"kind": "storage", "cities": ["c1", "c2"]}, "batch")
    before = deepcopy(state)
    with pytest.raises(RuleError, match="équipes"):
        confirm_order(state, "p1", {"kind": "walls", "cities": ["c1"]}, "conflict")
    assert state == before


@case(
    "monthly-tax-and-construction-timing-match-document",
    "Design fiscal example: canals complete after six full months; monthly tax precedes completion",
)
@pytest.mark.parametrize(
    "month,level,tax,stock,realm_stock",
    [
        pytest.param(6, 0, 600000, 0, 0, id="before-completion"),
        pytest.param(7, 1, 700000, 0, 0, id="completion-after-monthly-tax"),
        pytest.param(12, 1, 0, 1700000, 4100000, id="annual-harvest"),
    ],
)
def test_monthly_tax_and_construction_timing_match_document(month, level, tax, stock, realm_stock):
    """Given V0 canals ordered with sufficient funds.
    When the simulation reaches month {month}.
    Then canal level {level}, accrued tax {tax}, local stock {stock} and realm stock {realm_stock} match the fiscal example.
    """
    state = rich_state("V0")
    for city in state["cities"].values():
        city["stock"] = 800000
    confirm_order(state, "p1", {"kind": "irrigation", "cities": ["c1"]}, "canals")
    for _ in range(month):
        advance_month(state, "example")
    city = state["cities"]["c1"]
    assert (city["irrigation"], city["tax"], city["stock"]) == (level, tax, stock)
    assert sum(state["cities"][key]["stock"] for key in ("c1", "c2", "c3")) == realm_stock


@case(
    "disconnected-origins-must-touch-same-frontier",
    "Design frontier: only friendly components adjoining the target can contribute",
)
@pytest.mark.parametrize(
    "target,expected",
    [
        pytest.param("c2", {"c1", "c3"}, id="both-components-touch"),
        pytest.param("c4", {"c3"}, id="one-component-touches"),
    ],
)
def test_disconnected_origins_must_touch_same_frontier(target, expected):
    """Given friendly lands split by an enemy city.
    When origins eligible to attack {target} are requested.
    Then only the components touching that frontier contribute: {expected}.
    """
    state = new_state(calendar_version=1)
    state["cities"]["c2"]["owner"] = "p2"
    assert eligible_origins(state, "p1", target) == expected


@case(
    "relief-allocation",
    "Design §26.2 Secours: split each origin budget once across fronts, capped by threat",
)
@pytest.mark.parametrize("scenario", ["two-fronts", "threat-cap"])
def test_relief_allocation(scenario):
    """Given the prescribed {scenario} capture threats.
    When relief is allocated once from the pre-combat snapshot.
    Then origin budgets are split across fronts and capped by threat without redistribution.
    """
    state = new_state(calendar_version=1)
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
    if scenario == "threat-cap":
        missions = missions[:1]
        missions[0]["cohorts"] = {"c4": 1}
    allocations = relief_allocations(state, missions, sorted(state["cities"]))
    if scenario == "two-fronts":
        assert sum(item["count"] for item in allocations if item["mission"] == "a") == 30
        assert sum(item["count"] for item in allocations if item["mission"] == "c") == 30
        assert sum(item["count"] for item in allocations if item["origin"] == "c2") == 20
    else:
        assert sum(item["count"] for item in allocations) == 1


@case(
    "captured-origin-receives-survivors-and-loot",
    "Design §26.3: survivors and loot return to the origin city under its current owner",
)
def test_captured_origin_receives_survivors_and_loot():
    """Given a raiding origin changes owner before its expedition returns.
    When the return month is resolved.
    Then survivors and loot reach their origin and its current owner receives the report.
    """
    state = new_state("V1", opponents="passive", calendar_version=1)
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


@case(
    "annual-growth-renewal-and-absent-ceiling",
    "Design V1 annual renewal: growth precedes renewal, absent troops count toward the ceiling",
)
def test_annual_growth_renewal_and_absent_ceiling():
    """Given a V1 city whose raid departs in the harvest month.
    When annual growth and Faithful renewal are applied.
    Then population becomes 1005, present plus absent Faithful total 100, and accrued tax is paid.
    """
    state = new_state("V1", opponents="passive", calendar_version=1)
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
