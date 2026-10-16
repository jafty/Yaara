"""Fixed-state behavioral contracts for monthly phases and their boundaries."""

from copy import deepcopy

import pytest

from simulation import engine
from simulation.projections import player_view
from simulation.rules import RuleError
from tests.builders import rich_state
from tests.cases import case
from tests.stubs import FixedRandom

pytestmark = pytest.mark.logic


@pytest.fixture
def fixed_draws(monkeypatch):
    monkeypatch.setattr(engine, "random_stream", FixedRandom())


@case(
    "departure-invalidated",
    "Rules §5–7,18: revalidate funding, frontier and works at departure without charging",
)
@pytest.mark.parametrize(
    "variation",
    [
        "lost-funding-city",
        "missing-funds",
        "lost-frontier",
        "missing-troops",
        "new-raid-protection",
        "lost-work-city",
        "new-wall-damage",
    ],
)
def test_departure_invalidated(variation):
    """Given an accepted order whose departure condition changes to {variation}.
    When departure is processed.
    Then the order is invalidated with a reason and all reservations released without charging cities.
    """
    state = rich_state()
    military = variation in ("lost-frontier", "missing-troops", "new-raid-protection")
    spec = (
        {"kind": "raid", "target": "c4", "contributions": {"c3": 45}}
        if military
        else {"kind": "walls", "cities": ["c1"]}
    )
    order = engine.confirm_order(state, "p1", spec, "order")
    if variation == "lost-funding-city":
        state["cities"]["c2"]["owner"] = "p2"
    elif variation == "missing-funds":
        state["cities"]["c2"]["stock"] = 0
    elif variation == "lost-frontier":
        state["cities"]["c3"]["owner"] = "p2"
    elif variation == "missing-troops":
        state["cities"]["c3"]["fideles"] = 44
    elif variation == "new-raid-protection":
        state["cities"]["c4"]["raid_protected_until"] = 12
    elif variation == "lost-work-city":
        state["cities"]["c1"]["owner"] = "p2"
    else:
        state["cities"]["c1"]["damaged"] = True
    before = deepcopy(state["cities"])
    state["month"] = 1
    events = []
    engine.depart_orders(state, events)
    assert order["status"] == "invalidated"
    assert state["cities"] == before
    assert state["expeditions"] == state["works"] == []
    assert not any(engine.reservations(state)[0].values())
    assert not any(engine.reservations(state)[1].values())
    assert events[0]["recipient"] == "p1"
    assert events[0]["title"] == "Ordre invalidé"
    message = {
        "lost-funding-city": "financement",
        "missing-funds": "financement",
        "lost-frontier": "frontière",
        "missing-troops": "frontière",
        "new-raid-protection": "protection",
        "lost-work-city": "travaux",
        "new-wall-damage": "travaux",
    }[variation]
    assert message in events[0]["body"]


@case(
    "equipment-completion",
    "Rules §18: forge price is frozen and equipment applies only on completion",
)
@pytest.mark.parametrize("level", [1, 2])
def test_equipment_completion(level, fixed_draws):
    """Given a forge upgrading to level {level}.
    When population changes after confirmation and the work reaches completion.
    Then the accepted price stays fixed and equipment changes only on completion.
    """
    state = rich_state()
    state["players"]["p1"]["equipment"] = level - 1
    order = engine.confirm_order(state, "p1", {"kind": "equipment"}, "forge")
    cost = 1800000 if level == 1 else 4200000
    duration = 8 if level == 1 else 14
    # Subsequent demographic changes cannot reprice an accepted order.
    state["cities"]["c1"]["population"] += 100
    engine.advance_month(state, "fixed")
    assert order["cost"] == cost
    assert sum(c["stock"] for c in engine.owned_cities(state, "p1")) == 7200000 - cost
    state["month"] = duration
    events = []
    engine.finish_works(state, events)
    assert state["players"]["p1"]["equipment"] == level - 1
    assert engine.equipment_busy(state, "p1")
    state["month"] += 1
    engine.finish_works(state, events)
    assert state["players"]["p1"]["equipment"] == level
    assert not engine.equipment_busy(state, "p1")
    assert order["status"] == "completed"
    assert events[0]["recipient"] == "p1"


@pytest.fixture
def outbound_raid(fixed_draws):
    state = rich_state()
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c3": 45}}, "raid"
    )
    engine.advance_month(state, "fixed")
    return state


@case(
    "combat-no-longer-valid",
    "Rules §7,17: changed ownership, elimination or protection sends armies home without refund",
)
@pytest.mark.parametrize(
    "variation", ["friendly-target", "eliminated-attacker", "protected-target"]
)
def test_combat_abandoned(outbound_raid, variation):
    """Given an outbound raid affected by {variation}.
    When its combat month is processed.
    Then the army returns with its troops intact and no loot or refund.
    """
    state = outbound_raid
    if variation == "friendly-target":
        state["cities"]["c4"]["owner"] = "p1"
    elif variation == "eliminated-attacker":
        state["players"]["p1"]["eliminated"] = True
    else:
        state["cities"]["c4"]["raid_protected_until"] = 14
    cities = deepcopy(state["cities"])
    state["month"] = 2
    events = []
    engine.resolve_combats(state, "fixed", events)
    assert state["cities"] == cities
    assert state["expeditions"][0]["status"] == "returning"
    assert state["orders"][0]["status"] == "returning"
    assert state["expeditions"][0]["cohorts"] == {"c3": 45}
    assert state["expeditions"][0]["loot"] == 0
    assert events[0]["recipient"] == "p1"
    assert "sans remboursement" in events[0]["body"]


@case(
    "raid-engine-outcome",
    "Rules §17: apply failed and undefended raid results to real state, stocks and protection",
)
@pytest.mark.parametrize(
    "defenders,outcome,attacker_dead,defender_dead,destroyed,loot",
    [
        pytest.param(0, "success", 0, 0, 120000, 225000, id="undefended"),
        pytest.param(200, "defeat", 4, 2, 30000, 0, id="defeat"),
        pytest.param(300, "rout", 9, 1, 0, 0, id="rout"),
    ],
)
def test_raid_engine_outcome(
    outbound_raid, defenders, outcome, attacker_dead, defender_dead, destroyed, loot
):
    """Given an outbound raid encountering {defenders} defenders.
    When combat resolves with the prescribed draw.
    Then outcome {outcome} produces {attacker_dead} attacker deaths, {defender_dead} defender deaths, {destroyed} destroyed Measures and {loot} loot.
    """
    state = outbound_raid
    target = state["cities"]["c4"]
    target["fideles"] = defenders
    state["month"] = 2
    events = []
    engine.resolve_combats(state, "fixed", events)
    mission = state["expeditions"][0]
    assert mission["cohorts"] == {"c3": 45 - attacker_dead}
    assert mission["loot"] == loot
    assert target["fideles"] == defenders - defender_dead
    assert target["stock"] == 2400000 - loot - destroyed
    assert target["raid_protected_until"] == (14 if outcome == "success" else 0)
    assert state["cities"]["c3"]["military_deaths"] == attacker_dead
    assert target["military_deaths"] == defender_dead


@case(
    "capture-engine-outcome",
    "Rules §9,16: capture/siege outcomes apply local food, casualties and sovereignty",
)
@pytest.mark.parametrize(
    "variation,expected",
    [
        pytest.param("held", ("p2", 10, 2, 0, 500000), id="held"),
        pytest.param("shortage", ("p1", 4, 8, 2, 499999), id="shortage"),
        pytest.param("defeat", ("p2", 12, 6, 0, 0), id="defeat"),
        pytest.param("rout", ("p2", 25, 6, 0, 0), id="rout"),
        pytest.param("damaged-wall", ("p1", 8, 12, 0, 0), id="damaged-wall"),
        pytest.param("surrender", ("p1", 1, 1, 0, 0), id="surrender"),
        pytest.param("undefended", ("p1", 0, 0, 0, 0), id="undefended"),
    ],
)
def test_capture_engine_outcome(variation, expected, fixed_draws):
    """Given a capture under the {variation} defense condition.
    When combat resolves with the prescribed draw.
    Then owner, attacker deaths, defender deaths, civilian deaths and food used match {expected}.
    """
    state = rich_state()
    target = state["cities"]["c4"]
    # Isolate local defense; separate relief tests exercise connected garrisons.
    state["links"] = [["c3", "c4"]]
    target.update(fideles=100, walls=2)
    if variation in ("held", "shortage"):
        state["players"]["p1"]["equipment"] = 1
        target["stock"] = 500000 if variation == "held" else 499999
    elif variation == "defeat":
        target.update(fideles=200, walls=0)
    elif variation == "rout":
        target.update(fideles=300, walls=0)
    elif variation == "damaged-wall":
        state["players"]["p1"]["equipment"] = 2
        target.update(walls=1, damaged=True)
    elif variation == "surrender":
        target.update(fideles=50, walls=0)
    else:
        target.update(fideles=0, walls=0)
    engine.confirm_order(
        state, "p1", {"kind": "capture", "target": "c4", "contributions": {"c3": 100}}, "capture"
    )
    engine.advance_month(state, "fixed")
    stock = target["stock"]
    state["month"] = 2
    events = []
    engine.resolve_combats(state, "fixed", events)
    owner, attacker_dead, defender_dead, civilian_dead, food = expected
    assert target["owner"] == owner
    assert state["cities"]["c3"]["military_deaths"] == attacker_dead
    assert target["military_deaths"] == defender_dead
    assert target["civilian_deaths"] == civilian_dead
    assert target["stock"] == stock - food
    assert len([e for e in events if e["kind"] == "sovereignty"]) == (3 if owner == "p1" else 0)


@case(
    "return-loot-capacity", "Rules §10,17: local capacity caps returned loot; survivors return once"
)
@pytest.mark.parametrize("free,deposit", [(0, 0), (1000, 1000), (300000, 225000)])
def test_return_capacity(outbound_raid, free, deposit):
    """Given a returning expedition with 225000 loot and {free} local storage space.
    When its return is processed twice.
    Then only {deposit} Measures are deposited and survivors return once.
    """
    state = outbound_raid
    mission = state["expeditions"][0]
    mission.update(status="returning", loot=225000)
    origin = state["cities"]["c3"]
    origin["stock"] = 2400000 - free
    state["month"] = 3
    events = []
    engine.return_expeditions(state, events)
    assert origin["stock"] == 2400000 - free + deposit
    assert origin["fideles"] == 100
    assert mission["loot"] == 0 and mission["status"] == "completed"
    before = deepcopy(state)
    engine.return_expeditions(state, events)
    assert state == before
    assert len(events) == 1


@case(
    "return-no-survivors",
    "Rules §10: an annihilated expedition deposits no loot and reports its loss",
)
def test_no_survivors_return(outbound_raid):
    """Given an expedition with no surviving people.
    When its return is processed.
    Then no troops or loot are deposited and its recipient receives a loss report.
    """
    state = outbound_raid
    state["expeditions"][0].update(cohorts={"c3": 0}, loot=0)
    state["month"] = 3
    events = []
    engine.return_expeditions(state, events)
    assert state["cities"]["c3"]["fideles"] == 55
    assert state["expeditions"][0]["status"] == "completed"
    assert events[-1]["title"] == "Une expédition ne reviendra pas"
    assert events[-1]["recipient"] == "p1"


@case(
    "reign-ends",
    "Rules §1–3: territorial victory or duration seals standings and missions in transit",
)
@pytest.mark.parametrize("variation", ["territorial", "duration"])
def test_reign_ends(outbound_raid, variation):
    """Given a reign reaching its {variation} victory condition with an expedition in transit.
    When the end condition is checked.
    Then standings and transit count are frozen and another month is rejected without mutation.
    """
    state = outbound_raid
    if variation == "territorial":
        for city in state["cities"].values():
            city["owner"] = "p1"
    else:
        state["month"] = 120
    events = []
    engine.check_end(state, events)
    assert state["status"] == "finished"
    assert state["result"]["month"] == state["month"]
    assert state["result"]["expeditions_in_transit"] == 1
    assert len([e for e in events if e["title"] == "Le règne est achevé"]) == 3
    before = deepcopy(state)
    with pytest.raises(RuleError):
        engine.advance_month(state, "fixed")
    assert state == before


@case(
    "elimination-redirects-armies",
    "Rules §3,10: losing the last city recalls outbound armies, once",
)
def test_elimination(outbound_raid):
    """Given a player whose last city has been lost.
    When elimination is checked twice.
    Then outbound armies return and exactly one elimination report is emitted.
    """
    state = outbound_raid
    for city in engine.owned_cities(state, "p1"):
        city["owner"] = "p2"
    events = []
    engine.check_end(state, events)
    assert state["players"]["p1"]["eliminated"]
    assert state["expeditions"][0]["status"] == "returning"
    assert state["orders"][0]["status"] == "returning"
    assert state["status"] == "active"
    engine.check_end(state, events)
    assert len(events) == 1


@case("ranking-tiebreak", "Rules §1: cities first, population second, equal scores share a rank")
@pytest.mark.parametrize(
    "variation,order,ranks",
    [
        ("equal", ["p1", "p2", "p3"], [1, 1, 1]),
        ("population", ["p2", "p1", "p3"], [1, 2, 2]),
        ("cities", ["p2", "p3", "p1"], [1, 2, 3]),
    ],
)
def test_ranking(variation, order, ranks):
    """Given standings with the {variation} score condition.
    When players are ranked.
    Then city count then population produce actor order {order} and shared ranks {ranks}.
    """
    state = engine.new_state()
    if variation == "population":
        state["cities"]["c4"]["population"] += 1
    if variation == "cities":
        state["cities"]["c1"].update(owner="p2", population=1)
    rows = engine.standings(state)
    assert [r["actor"] for r in rows] == order
    assert [r["rank"] for r in rows] == ranks


@case(
    "projection-own-orders",
    "Rules §11: own orders are visible, rival orders stay private and V0 actions stay unavailable",
)
@pytest.mark.parametrize("version", ["V0", "V1"])
def test_projection_orders(version):
    """Given own and rival wall orders under {version} rules.
    When the player projection is built.
    Then only own orders appear with the permitted cancellation and construction actions.
    """
    state = rich_state(version)
    engine.confirm_order(state, "p1", {"kind": "walls", "cities": ["c1"]}, "own")
    engine.confirm_order(state, "p2", {"kind": "walls", "cities": ["c4"]}, "rival")
    view = player_view(state, "p1")
    assert [o["id"] for o in view["orders"]] == ["own"]
    assert view["orders"][0]["can_cancel"] == (version == "V1")
    assert [a["kind"] for a in view["work_actions"]] == (
        ["irrigation", "storage", "walls", "repair"] if version == "V1" else ["irrigation", "walls"]
    )


@case(
    "projection-active-work", "Rules §11,18: player sees own active construction and forge progress"
)
def test_projection_active_work(fixed_draws):
    """Given a granary and forge in progress.
    When the player reads month three.
    Then the granary is half complete and the busy forge has its original finish month.
    """
    state = rich_state()
    engine.confirm_order(state, "p1", {"kind": "storage", "cities": ["c1"]}, "store")
    engine.confirm_order(state, "p1", {"kind": "equipment"}, "forge")
    engine.advance_month(state, "fixed")
    state["month"] = 3
    view = player_view(state, "p1")
    city = next(c for c in view["cities"] if c["id"] == "c1")
    assert city["works"][0]["progress"] == 50
    assert view["equipment_work"] == [{"finish_month": 9}]
    assert not view["equipment_available"]
    assert view["orders"][0]["destination"] == "Toutes vos possessions"


@case(
    "projection-mission-lifecycle",
    "Rules §11: only own unfinished missions appear with their current return status",
)
@pytest.mark.parametrize("month,expected", [(1, False), (2, True), (3, None)])
def test_projection_missions(outbound_raid, month, expected):
    """Given an expedition at month {month}.
    When the player projection is built.
    Then only own unfinished missions appear with returning status {expected}.
    """
    state = outbound_raid
    for _ in range(month - 1):
        engine.advance_month(state, "fixed")
    view = player_view(state, "p1")
    assert len(view["missions"]) == (0 if expected is None else 1)
    if expected is not None:
        assert view["missions"][0]["returning"] is expected
    assert player_view(state, "p2")["missions"] == []


@case(
    "projection-final-result",
    "Rules §1,11: finished projections use frozen standings and disclose transit count only",
)
def test_projection_result(outbound_raid):
    """Given a finished reign with an expedition in transit.
    When the final player projection is built.
    Then frozen standings, the transit count and the final calendar are shown without opponent population.
    """
    state = outbound_raid
    state["month"] = 120
    engine.check_end(state, [])
    view = player_view(state, "p1")
    assert view["finished"] and view["epilogue_missions"] == 1
    assert (view["year"], view["year_month"], view["remaining"]) == (10, 12, 0)
    assert all("population" not in r for r in view["ranking"])
