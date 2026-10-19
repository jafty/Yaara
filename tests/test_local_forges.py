"""City forges are versioned so existing reigns retain their accepted rules."""

import json
from copy import deepcopy

import pytest

from simulation import engine
from simulation.narration import completed_work_phrase, work_effect, work_phrase
from simulation.projections import player_view
from simulation.rules import RuleError
from tests.cases import case
from tests.stubs import FixedRandom

pytestmark = pytest.mark.logic


@pytest.fixture
def local_state(monkeypatch):
    monkeypatch.setattr(engine, "random_stream", FixedRandom())
    state = engine.new_state(opponents="passive", map_version=1)
    for city in state["cities"].values():
        city["stock"] = 2_400_000
    return state


@case("local-forge-new-reign", "Owner UX decision: new reigns have an independent forge per city")
def test_new_reign(local_state):
    """Given a newly created reign.
    When its initial infrastructure is inspected.
    Then every city has an ordinary local forge and the version is explicit.
    """
    assert local_state["forge_version"] == 2
    assert all(city["forge"] == 0 for city in local_state["cities"].values())


@case(
    "local-forge-quote", "Local forge decision: one third of former minimum, local population price"
)
@pytest.mark.parametrize(
    "level,population,cost,duration",
    [
        (0, 500, 600_000, 8),
        (0, 1000, 600_000, 8),
        (0, 1500, 900_000, 8),
        (1, 500, 1_400_000, 14),
        (1, 1000, 1_400_000, 14),
        (1, 1500, 2_100_000, 14),
    ],
    ids=[
        "first-floor",
        "first-equal",
        "first-population",
        "second-floor",
        "second-equal",
        "second-population",
    ],
)
def test_quote(local_state, level, population, cost, duration):
    """Given a city with forge level {level} and population {population}.
    When its next forge is quoted.
    Then the immutable quote costs {cost} Measures and takes {duration} Moons.
    """
    local_state["cities"]["c1"].update(forge=level, population=population)
    before = deepcopy(local_state)
    order = engine.prepare_order(local_state, "p1", {"kind": "forge", "cities": ["c1"]}, "f")
    assert (order["cost"], order["tasks"][0]["duration"]) == (cost, duration)
    assert order["tasks"][0]["level"] == level + 1
    assert sum(order["funding"].values()) == cost
    assert local_state == before


@case(
    "local-forge-rejection",
    "Local forges obey ownership, team, level, version and atomic funding rules",
)
@pytest.mark.parametrize(
    "variation,reason",
    [
        ("v0", "V1"),
        ("legacy", "règne"),
        ("realm-equipment", "cité"),
        ("empty", "Choisissez"),
        ("duplicate", "Choisissez"),
        ("foreign", "autorité"),
        ("maximum", "maximal"),
        ("reserved", "équipes"),
        ("active", "équipes"),
        ("unaffordable-batch", "dépense"),
    ],
    ids=[
        "v0",
        "legacy",
        "realm-equipment",
        "empty",
        "duplicate",
        "foreign",
        "maximum",
        "reserved",
        "active",
        "unaffordable-batch",
    ],
)
def test_rejection(local_state, variation, reason):
    """Given a local forge request with condition {variation}.
    When the request is confirmed.
    Then it is rejected for {reason} without any mutation or partial reservation.
    """
    spec = {"kind": "forge", "cities": ["c1"]}
    if variation == "v0":
        local_state["rules"] = "V0"
    elif variation == "legacy":
        local_state.pop("forge_version")
    elif variation == "realm-equipment":
        spec = {"kind": "equipment"}
    elif variation == "empty":
        spec["cities"] = []
    elif variation == "duplicate":
        spec["cities"] = ["c1", "c1"]
    elif variation == "foreign":
        spec["cities"] = ["c4"]
    elif variation == "maximum":
        local_state["cities"]["c1"]["forge"] = 2
    elif variation in ("reserved", "active"):
        engine.confirm_order(local_state, "p1", {"kind": "storage", "cities": ["c1"]}, "s")
        if variation == "active":
            engine.advance_month(local_state, "fixed")
    else:
        spec["cities"] = ["c1", "c2"]
        for city in engine.owned_cities(local_state, "p1"):
            city["stock"] = 300_000
    before = deepcopy(local_state)
    with pytest.raises(RuleError, match=reason):
        engine.confirm_order(local_state, "p1", spec, "f")
    assert local_state == before


@case(
    "local-forge-batch-cancel",
    "Local forges preserve a single atomic multi-city seal and cancellation",
)
def test_batch_cancel(local_state):
    """Given free teams in two cities.
    When their forges are sealed together and then cancelled.
    Then one order reserves both teams and its cancellation releases all resources.
    """
    order = engine.confirm_order(local_state, "p1", {"kind": "forge", "cities": ["c1", "c2"]}, "f")
    assert order["cost"] == 1_200_000
    assert engine.busy_cities(local_state) == {"c1", "c2"}
    assert sum(engine.reservations(local_state)[0].values()) == 1_200_000
    engine.cancel_order(local_state, "p1", "f")
    assert not engine.busy_cities(local_state)
    assert not any(engine.reservations(local_state)[0].values())


@case(
    "local-forge-completion",
    "A forge bonus starts at completion and follows its city through capture",
)
@pytest.mark.parametrize(
    "level,captured", [(1, False), (2, False), (1, True)], ids=["first", "second", "captured"]
)
def test_completion(local_state, level, captured):
    """Given a city upgrading its forge to {level} and captured status {captured}.
    When the frozen-price work reaches its due date.
    Then only that city's equipment changes and its current ruler receives the report.
    """
    city = local_state["cities"]["c1"]
    city["forge"] = level - 1
    order = engine.confirm_order(local_state, "p1", {"kind": "forge", "cities": ["c1"]}, "f")
    cost = 600_000 if level == 1 else 1_400_000
    engine.advance_month(local_state, "fixed")
    assert sum(c["stock"] for c in engine.owned_cities(local_state, "p1")) == 7_200_000 - cost
    city["population"] += 100
    if captured:
        city["owner"] = "p2"
    local_state["month"] = 8 if level == 1 else 14
    engine.finish_works(local_state, [])
    assert city["forge"] == level - 1
    local_state["month"] += 1
    events = []
    engine.finish_works(local_state, events)
    assert city["forge"] == level
    assert local_state["cities"]["c2"]["forge"] == 0
    assert order["cost"] == cost and order["status"] == "completed"
    assert events[0]["recipient"] == city["owner"]
    assert "Qasr" in events[0]["title"]


@case("local-forge-departure", "Expeditions freeze each contributing city's equipment at departure")
def test_departure(local_state):
    """Given a raid combining forty ordinary and twenty reinforced Fidèles.
    When it departs and the origin changes equipment and owner.
    Then the expedition keeps its exact original strength and remains JSON serializable.
    """
    local_state["cities"]["c2"]["forge"] = 1
    engine.confirm_order(
        local_state,
        "p1",
        {"kind": "raid", "target": "c4", "contributions": {"c1": 40, "c2": 20}},
        "r",
    )
    engine.advance_month(local_state, "fixed")
    mission = local_state["expeditions"][0]
    local_state["cities"]["c2"].update(forge=2, owner="p2")
    assert engine.mission_strength(mission) == 6400
    assert mission["cohort_equipment"] == {"c1": 100, "c2": 120}
    json.dumps(local_state)
    local_state["month"] = 2
    events = []
    engine.resolve_combats(local_state, "fixed", events)
    assert "équipements variés" in str(events)
    assert mission["status"] == "returning"


@case(
    "local-forge-defense",
    "City defense uses its own completed forge rather than the realm's equipment",
)
def test_defense(local_state):
    """Given forty raiders and forty encountered defenders with superior local equipment.
    When the raid fights the prescribed encounter.
    Then the local forge repels it despite ordinary realm equipment.
    """
    local_state["cities"]["c4"]["forge"] = 2
    engine.confirm_order(
        local_state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c3": 45}}, "r"
    )
    engine.advance_month(local_state, "fixed")
    events, _ = engine.advance_month(local_state, "fixed")
    assert local_state["expeditions"][0]["loot"] == 0
    assert any("équipement supérieur" in event["body"] for event in events)


@case(
    "local-forge-capture",
    "Local forge equipment affects capture strengths at each origin and target",
)
@pytest.mark.parametrize(
    "side,owner,attacker_dead,defender_dead",
    [
        ("attacker", "p1", 6, 12),
        ("defender", "p2", 10, 3),
    ],
    ids=["superior-attack", "reinforced-defense"],
)
def test_capture(local_state, side, owner, attacker_dead, defender_dead):
    """Given eighty attackers against one hundred defenders and a forge on the {side} side.
    When capture resolves without relief or walls.
    Then ownership is {owner} and the specified losses reflect local equipment.
    """
    local_state["links"] = [["c3", "c4"]]
    local_state["cities"]["c3"]["forge"] = 2 if side == "attacker" else 0
    local_state["cities"]["c4"]["forge"] = 1 if side == "defender" else 0
    engine.confirm_order(
        local_state,
        "p1",
        {
            "kind": "capture",
            "target": "c4",
            "contributions": {"c3": 80},
        },
        "capture",
    )
    engine.advance_month(local_state, "fixed")
    engine.advance_month(local_state, "fixed")
    assert local_state["cities"]["c4"]["owner"] == owner
    assert local_state["cities"]["c3"]["military_deaths"] == attacker_dead
    assert local_state["cities"]["c4"]["military_deaths"] == defender_dead


@case(
    "local-forge-relief-observation",
    "Capture reports describe only the equipment of encountered defenders",
)
@pytest.mark.parametrize(
    "local_count,relief_level,description",
    [
        (100, 1, "équipements variés"),
        (0, 2, "équipement supérieur"),
    ],
    ids=["mixed-local-and-relief", "relief-only"],
)
def test_relief_observation(local_state, local_count, relief_level, description):
    """Given {local_count} ordinary local defenders and relief with forge level {relief_level}.
    When an attacking expedition reports the encounter.
    Then the report describes {description} without assuming local equipment for relief.
    """
    local_state["cities"]["c4"]["fideles"] = local_count
    local_state["cities"]["c5"]["forge"] = relief_level
    local_state["cities"]["c6"]["forge"] = relief_level
    engine.confirm_order(
        local_state,
        "p1",
        {
            "kind": "capture",
            "target": "c4",
            "contributions": {"c3": 80},
        },
        "capture",
    )
    engine.advance_month(local_state, "fixed")
    events, _ = engine.advance_month(local_state, "fixed")
    assert any(event["recipient"] == "p1" and description in event["body"] for event in events)


@case(
    "local-forge-relief-cap",
    "Mixed local relief preserves each origin's equipment and the attack-strength cap",
)
@pytest.mark.parametrize("capped", [False, True], ids=["below-cap", "above-cap"])
def test_relief_cap(local_state, capped):
    """Given connected relief cities with different forge levels and capped status {capped}.
    When support is allocated against a capture.
    Then every relief group uses its city's equipment and their combined strength stays capped.
    """
    local_state["cities"]["c5"].update(forge=2, fideles=1000 if capped else 100)
    local_state["cities"]["c6"].update(forge=1, fideles=1000 if capped else 100)
    mission = {
        "id": "m",
        "kind": "capture",
        "target": "c4",
        "actor": "p1",
        "cohorts": {"c3": 80},
        "combativity": 100,
    }
    groups = engine.relief_allocations(local_state, [mission], sorted(local_state["cities"]))
    assert {item["origin"]: item["combativity"] for item in groups} == {"c5": 145, "c6": 120}
    assert sum(item["count"] * item["combativity"] for item in groups) <= 8000
    assert [item["count"] for item in groups] == ([30, 30] if capped else [20, 20])


@case(
    "local-forge-projection",
    "Forge levels and effects are visible only for the player's own cities",
)
@pytest.mark.parametrize("version", ["V0", "V1"])
def test_projection(local_state, version):
    """Given local forges under rules {version}.
    When the player projection is built.
    Then local effects stay private and only V1 offers forge construction.
    """
    local_state["rules"] = version
    local_state["cities"]["c1"]["forge"] = 1
    view = player_view(local_state, "p1")
    assert view["local_forges"]
    assert view["owned_cities"][0]["equipment"] == "Équipement renforcé"
    assert all(
        "forge" not in city and "equipment" not in city
        for city in view["cities"]
        if not city["owned"]
    )
    assert ("forge" in [action["kind"] for action in view["work_actions"]]) == (version == "V1")
    assert not view["equipment_available"] and view["equipment_work"] == []


@case("local-forge-narration", "Local forge previews describe local equipment and completed work")
@pytest.mark.parametrize("level", [1, 2])
def test_narration(level):
    """Given a local forge upgrade to level {level}.
    When its proposal, consequence and completion are narrated.
    Then the wording identifies a local forge and never promises a realm-wide upgrade.
    """
    assert "forge" in work_phrase("forge", level)
    assert "forge" in completed_work_phrase("forge", level)
    assert "cité" in work_effect("forge", level)


@case("local-forge-bot", "Bots build local forges through ordinary city work validation")
def test_bot(local_state):
    """Given a wealthy bot with too few troops for capture.
    When its policy selects infrastructure.
    Then it seals a local forge for one eligible city.
    """
    local_state["month"] = 5
    local_state["players"]["p1"]["bot"] = True
    for city in engine.owned_cities(local_state, "p1"):
        city["fideles"] = 40
    orders = engine.bot_orders(local_state, "fixed")
    assert orders[0]["kind"] == "forge"
    assert orders[0]["tasks"][0]["city"] == "c1"
