"""Independent normal, rejection and boundary variations for core commands."""

from copy import deepcopy

import pytest

from simulation import engine
from simulation.rules import RuleError, rule_family
from tests.builders import rich_state
from tests.cases import case

pytestmark = pytest.mark.logic


@case(
    "configuration-rejected",
    "Rules §1–3: only implemented rule families and offered configurations",
)
@pytest.mark.parametrize(
    "options",
    [
        pytest.param({"version": "V2"}, id="unknown-rules"),
        pytest.param({"reign_months": 12}, id="unsupported-duration"),
        pytest.param({"opponents": "cheating"}, id="unsupported-opponents"),
    ],
)
def test_invalid_configuration(options):
    """Given unsupported configuration {options}.
    When a new game is requested.
    Then configuration is rejected.
    """
    with pytest.raises(RuleError, match="version" if "version" in options else "configuration"):
        engine.new_state(**options, calendar_version=1, map_version=1, economy_version=1)


@case("configuration-supported", "Rules §1–3: offered durations and passive/active opponents")
@pytest.mark.parametrize("months", [24, 60, 120, 240])
@pytest.mark.parametrize("opponents", ["active", "passive"])
def test_configuration(months, opponents):
    """Given duration {months} and opponent mode {opponents}.
    When a game is created.
    Then nine cities and 9000 people are created with the selected bot policy.
    """
    state = engine.new_state(
        reign_months=months,
        opponents=opponents,
        player_name="Test house",
        calendar_version=1,
        map_version=1,
        economy_version=1,
    )
    assert state["config"]["reign_months"] == months
    assert state["players"]["p1"]["name"] == "Test house"
    assert not state["players"]["p1"]["bot"]
    assert state["players"]["p2"]["bot"] == (opponents == "active")
    assert len(state["cities"]) == 9
    assert sum(c["population"] for c in state["cities"].values()) == 9000


@case(
    "actor-command-rejected",
    "Rules §3: finished reigns and unknown/eliminated actors cannot command",
)
@pytest.mark.parametrize("variation", ["finished", "unknown", "eliminated"])
def test_actor_cannot_command(variation):
    """Given an actor in the {variation} condition.
    When a wall order is confirmed.
    Then authorization fails without changing state.
    """
    state = rich_state()
    actor = "missing" if variation == "unknown" else "p1"
    if variation == "finished":
        state["status"] = "finished"
    if variation == "eliminated":
        state["players"][actor]["eliminated"] = True
    before = deepcopy(state)
    with pytest.raises(
        RuleError, match="règne est terminé" if variation == "finished" else "Prétendant"
    ):
        engine.confirm_order(state, actor, {"kind": "walls", "cities": ["c1"]}, "new")
    assert state == before


@case("contributions-rejected", "Rules §5–7: military contributions are nonnegative integer pairs")
@pytest.mark.parametrize(
    "entries",
    [
        pytest.param(None, id="null"),
        pytest.param("c1", id="string"),
        pytest.param({"c1": True}, id="boolean"),
        pytest.param({"c1": 1.5}, id="fraction"),
        pytest.param({"c1": "20"}, id="numeric-string"),
        pytest.param({"c1": -1}, id="negative"),
        pytest.param([["c1"]], id="short-pair"),
        pytest.param([["c1", 1, 2]], id="long-pair"),
        pytest.param([None], id="non-pair"),
    ],
)
def test_invalid_contributions(entries):
    """Given invalid military contributions {entries}.
    When a raid is confirmed.
    Then the input is rejected without changing state.
    """
    state = rich_state()
    before = deepcopy(state)
    message = (
        "contributions militaires" if entries is None or isinstance(entries, str) else "effectifs"
    )
    with pytest.raises(RuleError, match=message):
        engine.confirm_order(
            state, "p1", {"kind": "raid", "target": "c4", "contributions": entries}, "bad"
        )
    assert state == before


@case("zero-contribution-ignored", "Rules §5–7: zero contributions reserve no troops")
def test_zero_contribution():
    """Given an origin offering zero people.
    When contributions are normalized.
    Then only the positive contribution remains.
    """
    assert engine.normalized_contributions([["c1", 0], ["c3", 20]]) == {"c3": 20}


@case(
    "construction-rejected",
    "Rules §18: work requires owned unique cities, permitted levels and sound walls",
)
@pytest.mark.parametrize(
    "variation",
    [
        "missing-cities",
        "string-cities",
        "duplicate-city",
        "unknown-city",
        "enemy-city",
        "v0-storage",
        "v0-repair",
        "v0-upgrade",
        "v1-max-level",
        "damaged-upgrade",
        "repair-no-walls",
        "repair-sound-walls",
        "unknown-order",
    ],
)
def test_construction_rejected(variation):
    """Given the invalid construction condition {variation}.
    When a work order is confirmed.
    Then the relevant restriction rejects it without changing state.
    """
    state = rich_state("V0" if variation.startswith("v0") else "V1")
    spec = {"kind": "walls", "cities": ["c1"]}
    if variation == "missing-cities":
        spec.pop("cities")
    elif variation == "string-cities":
        spec["cities"] = "c1"
    elif variation == "duplicate-city":
        spec["cities"] = ["c1", "c1"]
    elif variation == "unknown-city":
        spec["cities"] = ["missing"]
    elif variation == "enemy-city":
        spec["cities"] = ["c4"]
    elif variation in ("v0-storage", "v0-repair"):
        spec["kind"] = variation[3:]
    elif variation in ("v0-upgrade", "v1-max-level"):
        state["cities"]["c1"]["walls"] = 1 if variation == "v0-upgrade" else 2
    elif variation == "damaged-upgrade":
        state["cities"]["c1"].update(walls=1, damaged=True)
    elif variation.startswith("repair"):
        spec["kind"] = "repair"
        state["cities"]["c1"]["walls"] = int(variation == "repair-sound-walls")
    else:
        spec["kind"] = "unknown"
    before = deepcopy(state)
    message = {
        "missing-cities": "Choisissez au moins",
        "string-cities": "Choisissez au moins",
        "duplicate-city": "Choisissez au moins",
        "unknown-city": "autorité",
        "enemy-city": "autorité",
        "v0-storage": "V1",
        "v0-repair": "V1",
        "v0-upgrade": "niveau maximal",
        "v1-max-level": "niveau maximal",
        "damaged-upgrade": "réparer",
        "repair-no-walls": "aucune réparation",
        "repair-sound-walls": "aucune réparation",
        "unknown-order": "pas reconnu",
    }[variation]
    with pytest.raises(RuleError, match=message):
        engine.confirm_order(state, "p1", spec, "bad")
    assert state == before


@case("unknown-work-spec-rejected", "Rules §18: only specified construction kinds can be quoted")
def test_unknown_work():
    """Given a work kind outside the rules.
    When a quote is requested.
    Then the unknown work is rejected.
    """
    state = engine.new_state(calendar_version=1, map_version=1, economy_version=1)
    with pytest.raises(RuleError, match="n’existe pas"):
        engine.work_spec(state, state["cities"]["c1"], "unknown")


@case(
    "expedition-rejected",
    "Rules §5–7: valid enemy target, reachable origins, available troops and minima",
)
@pytest.mark.parametrize(
    "variation",
    [
        "unknown-target",
        "own-target",
        "unknown-origin",
        "enemy-origin",
        "unreachable-origin",
        "too-many-troops",
        "reserved-troops",
        "raid-below-minimum",
        "capture-below-minimum",
    ],
)
def test_expedition_rejected(variation):
    """Given the invalid expedition condition {variation}.
    When a raid or capture is confirmed.
    Then the target, frontier, availability or minimum restriction rejects it without changing state.
    """
    state = rich_state()
    spec = {"kind": "raid", "target": "c4", "contributions": {"c3": 45}}
    if variation == "unknown-target":
        spec["target"] = "missing"
    elif variation == "own-target":
        spec["target"] = "c1"
    elif variation in ("unknown-origin", "enemy-origin"):
        spec["contributions"] = {"missing" if variation == "unknown-origin" else "c4": 45}
    elif variation == "unreachable-origin":
        state["cities"]["c2"]["owner"] = "p2"
        spec["contributions"] = {"c1": 45}
    elif variation == "too-many-troops":
        spec["contributions"] = {"c3": 101}
    elif variation == "reserved-troops":
        engine.confirm_order(state, "p1", spec, "first")
        spec = {"kind": "raid", "target": "c9", "contributions": {"c3": 60}}
    else:
        kind = "capture" if variation.startswith("capture") else "raid"
        spec.update(kind=kind, contributions={"c3": 79 if kind == "capture" else 19})
    before = deepcopy(state)
    message = {
        "unknown-target": "cité ennemie",
        "own-target": "cité ennemie",
        "unknown-origin": "frontière",
        "enemy-origin": "frontière",
        "unreachable-origin": "frontière",
        "too-many-troops": "déjà promis",
        "reserved-troops": "déjà promis",
        "raid-below-minimum": "au moins 20",
        "capture-below-minimum": "au moins 80",
    }[variation]
    with pytest.raises(RuleError, match=message):
        engine.confirm_order(state, "p1", spec, "bad")
    assert state == before


@case("expedition-minimum-accepted", "Rules §5–7: raid/capture minima are inclusive")
@pytest.mark.parametrize("kind,count,cost", [("raid", 20, 70000), ("capture", 80, 2340000)])
def test_minimum_expedition(kind, count, cost):
    """Given a {kind} with exactly {count} people.
    When the order is confirmed.
    Then the inclusive minimum is accepted at cost {cost} for departure in month one.
    """
    state = rich_state()
    order = engine.confirm_order(
        state, "p1", {"kind": kind, "target": "c4", "contributions": {"c3": count}}, "min"
    )
    assert (order["cost"], order["contributions"], order["execute_month"]) == (
        cost,
        {"c3": count},
        1,
    )


@case(
    "order-id-owned-by-other-actor",
    "Rules §22: command identifiers cannot be reused by another actor",
)
def test_foreign_order_id():
    """Given an identifier already used by another actor.
    When confirmation reuses that identifier.
    Then the request is rejected without changing state.
    """
    state = rich_state()
    engine.confirm_order(state, "p1", {"kind": "walls", "cities": ["c1"]}, "same")
    before = deepcopy(state)
    with pytest.raises(RuleError, match="identifiant"):
        engine.confirm_order(state, "p2", {"kind": "walls", "cities": ["c4"]}, "same")
    assert state == before


@case(
    "confirmed-order-replay",
    "Rules §22: retry returns the original command without reserving twice",
)
def test_confirmed_replay():
    """Given an already confirmed wall order.
    When the same request is delivered again.
    Then the original order is returned without additional reservations.
    """
    state = rich_state()
    spec = {"kind": "walls", "cities": ["c1"]}
    original = engine.confirm_order(state, "p1", spec, "same")
    before = deepcopy(state)
    assert engine.confirm_order(state, "p1", spec, "same") == original
    assert state == before


@case("cancellation-rejected", "Rules §22: only one's own confirmed order can be cancelled")
@pytest.mark.parametrize("variation", ["missing", "foreign", "active", "cancelled"])
def test_cancellation_rejected(variation):
    """Given an order in the {variation} condition.
    When cancellation is requested.
    Then the invalid cancellation is rejected without changing state.
    """
    state = rich_state()
    order = engine.confirm_order(state, "p1", {"kind": "walls", "cities": ["c1"]}, "one")
    if variation in ("active", "cancelled"):
        order["status"] = variation
    before = deepcopy(state)
    with pytest.raises(RuleError, match="ne peut plus être annulé"):
        engine.cancel_order(
            state,
            "p2" if variation == "foreign" else "p1",
            "missing" if variation == "missing" else "one",
        )
    assert state == before


@case("equipment-rejected", "Rules §18: V1 forge has one project and two equipment levels")
@pytest.mark.parametrize("variation", ["v0", "maximum", "confirmed", "active"])
def test_equipment_rejected(variation):
    """Given a forge in the {variation} condition.
    When another equipment order is confirmed.
    Then the rule-family, level or busy-project restriction rejects it without changing state.
    """
    state = rich_state("V0" if variation == "v0" else "V1")
    if variation == "maximum":
        state["players"]["p1"]["equipment"] = 2
    if variation in ("confirmed", "active"):
        engine.confirm_order(state, "p1", {"kind": "equipment"}, "first")
        if variation == "active":
            engine.advance_month(state, "fixed")
    before = deepcopy(state)
    with pytest.raises(RuleError, match="V1" if variation == "v0" else "forge"):
        engine.confirm_order(state, "p1", {"kind": "equipment"}, "second")
    assert state == before


@case(
    "equipment-quote", "Rules §18: equipment uses population at confirmation with a minimum price"
)
@pytest.mark.parametrize(
    "level,population,cost,duration",
    [
        pytest.param(0, 500, 1800000, 8, id="first-minimum"),
        pytest.param(0, 1500, 2700000, 8, id="first-population"),
        pytest.param(1, 500, 4200000, 14, id="second-minimum"),
        pytest.param(1, 1500, 6300000, 14, id="second-population"),
    ],
)
def test_equipment_quote(level, population, cost, duration):
    """Given equipment level {level} and population {population} in each owned city.
    When a forge quote is prepared.
    Then the quote costs {cost} for {duration} months without changing state.
    """
    state = rich_state()
    state["players"]["p1"]["equipment"] = level
    for city in engine.owned_cities(state, "p1"):
        city["population"] = population
    before = deepcopy(state)
    quote = engine.prepare_order(state, "p1", {"kind": "equipment"}, "forge")
    assert (quote["level"], quote["cost"], quote["duration"]) == (level + 1, cost, duration)
    assert sum(quote["funding"].values()) == cost
    assert state == before


@case("rule-family-values", "Rules V0/V1: supported features are explicit and immutable")
@pytest.mark.parametrize(
    "version,expected",
    [("V0", (False, False, 1, False, False)), ("V1", (True, True, 2, True, True))],
)
def test_rule_family(version, expected):
    """Given the {version} rule family.
    When its supported features are consulted.
    Then the feature flags and maximum level are {expected}.
    """
    rules = rule_family(version)
    assert (
        rules.siege,
        rules.cancellable,
        rules.max_level,
        rules.storage,
        rules.equipment,
    ) == expected
