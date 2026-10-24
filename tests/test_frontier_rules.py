"""Independent contracts for the approved reciprocal-frontier increment."""

from copy import deepcopy

import pytest

from simulation import engine
from simulation.projections import player_view
from simulation.rules import RuleError
from simulation.tactics import field_result
from tests.cases import case

pytestmark = pytest.mark.logic
REQ = "Owner October 24: paid intelligence, local integration and reciprocal field encounters"


def realm():
    return engine.new_state(opponents="passive", strategy_version=2)


def seal(state, actor, target, origin, men, kind="capture", identity=None):
    return engine.confirm_order(
        state,
        actor,
        {"kind": kind, "target": target, "contributions": {origin: men}},
        identity or actor + target,
    )


@case("frontier-field-arithmetic", REQ)
@pytest.mark.parametrize(
    "first,second,expected",
    [
        pytest.param(100, 100, (6, 6, False, False, "contested"), id="equal"),
        pytest.param(124, 100, (6, 6, False, False, "contested"), id="below-decisive"),
        pytest.param(125, 100, (2, 12, True, False, "decisive"), id="decisive-boundary"),
        pytest.param(100, 125, (12, 2, False, True, "decisive"), id="reverse-decisive"),
        pytest.param(199, 100, (2, 12, True, False, "decisive"), id="below-overwhelming"),
        pytest.param(200, 100, (0, 4, True, False, "overwhelming"), id="overwhelming-boundary"),
        pytest.param(100, 200, (4, 0, False, True, "overwhelming"), id="reverse-overwhelming"),
    ],
)
def test_field_arithmetic(first, second, expected):
    """Given two marching forces with strengths {first} and {second} and 100 troops each.
    When their shared road encounter is resolved.
    Then losses and continuation equal the independently specified {expected}.
    """
    assert field_result(100, first, 100, second) == expected


@case("frontier-tiny-raid", REQ)
def test_tiny_raid():
    """Given 300 soldiers meeting twenty raiders with ordinary equipment.
    When the overwhelmingly stronger army wins the road encounter.
    Then it continues without casualties while the small force loses only one soldier.
    """
    assert field_result(300, 30000, 20, 2000) == (0, 1, True, False, "overwhelming")


@case("frontier-field-positive", REQ)
@pytest.mark.parametrize("values", [(0, 1, 1, 1), (1, 0, 1, 1), (1, 1, 0, 1), (1, 1, 1, 0)])
def test_positive_forces(values):
    """Given a road encounter with nonpositive input {values}.
    When the arithmetic contract is called.
    Then it rejects a force that cannot participate in battle.
    """
    with pytest.raises(ValueError):
        field_result(*values)


@case("frontier-defaults", REQ)
def test_defaults():
    """Given a request for a current new game.
    When the native aggregate is created.
    Then the saved strategy marker selects the approved frontier rules.
    """
    assert engine.new_state()["strategy_version"] == 2
    assert engine.new_state(economy_version=3)["strategy_version"] == 1


@case("frontier-marker-rejected", REQ)
def test_marker_rejected():
    """Given an unsupported strategic rule version.
    When a new game is requested.
    Then creation rejects the unsupported configuration.
    """
    with pytest.raises(RuleError):
        engine.new_state(strategy_version=9)


@case("frontier-route-stable", REQ)
def test_route_stable():
    """Given an army supplied by three connected friendly cities.
    When an expedition is sealed toward Sefra.
    Then its frontier departure city is Namar and no hidden commitment changes that route.
    """
    state = realm()
    order = seal(state, "p1", "c4", "c1", 80)
    assert order["launch_city"] == "c3"
    seal(state, "p2", "c3", "c4", 80)
    engine.advance_month(state, "route")
    assert state["expeditions"][0]["launch_city"] == "c3"


@case("frontier-hidden-seals", REQ)
def test_hidden_seals():
    """Given a defender whose surveillance is fully upgraded.
    When an enemy seals but has not departed and its target has a private respite.
    Then its public map and available attack targets reveal neither commitment nor respite.
    """
    state = realm()
    state["cities"]["c4"]["watch"] = 2
    before = player_view(state, "p2")
    seal(state, "p1", "c4", "c3", 80)
    state["cities"]["c3"]["raid_protected_until"] = 90
    after = player_view(state, "p2")
    assert before["cities"] == after["cities"]
    assert before["attack_targets"] == after["attack_targets"]
    assert not after["owned_cities"][0]["engaged"]


@case("frontier-shared-target", REQ)
def test_shared_target():
    """Given a target already reserved by a hidden hostile expedition.
    When another independently funded army commits toward that same target.
    Then both orders are accepted without disclosing or displacing the first commitment.
    """
    state = realm()
    seal(state, "p1", "c4", "c3", 20, "raid", "one")
    seal(state, "p1", "c4", "c1", 20, "raid", "two")
    engine.advance_month(state, "shared")
    assert len(state["expeditions"]) == 2
    engine.assert_invariants(state)


@case("frontier-paid-warning", REQ)
@pytest.mark.parametrize(
    "watch,damage,level", [(0, [], 0), (1, [], 1), (2, [], 2), (2, ["watch"], 1)]
)
def test_warning(watch, damage, level):
    """Given a defender with watch {watch} and damage {damage}.
    When an eighty-man capture army actually departs toward it.
    Then only paid effective surveillance level {level} reveals an appropriately scoped warning.
    """
    state = realm()
    state["cities"]["c4"].update(watch=watch, damaged_works=damage)
    seal(state, "p1", "c4", "c3", 80)
    letters, _ = engine.advance_month(state, "warning")
    view = player_view(state, "p2")
    target = next(c for c in view["owned_cities"] if c["id"] == "c4")
    assert bool(target["engaged"]) == bool(level)
    assert len(target["incoming_warnings"]) == bool(level)
    warnings = [e for e in letters if e["kind"] == "warning"]
    assert len(warnings) == bool(level)
    if level:
        warning = target["incoming_warnings"][0]
        assert warning["combat_month"] == 2
        assert ("kind" in warning) == (level == 2)
        assert ("force" in warning) == (level == 2)
        assert "men" not in warning and "combativity" not in warning
        state["cities"]["c4"]["damaged_works"] = ["watch"]
        assert (
            player_view(state, "p2")["owned_cities"][0]["incoming_warnings"]
            == target["incoming_warnings"]
        )


@case("frontier-reciprocal-missions", REQ)
@pytest.mark.parametrize(
    "first,second",
    [("raid", "raid"), ("capture", "capture"), ("capture", "raid"), ("raid", "capture")],
)
def test_reciprocal_types(first, second):
    """Given reciprocal {first} and {second} expeditions of equal strength across one road.
    When they meet on their scheduled combat Moon.
    Then one inconclusive field encounter sends both home without city combat or early reinforcement.
    """
    state = realm()
    seal(state, "p1", "c4", "c3", 80, first)
    seal(state, "p2", "c3", "c4", 80, second)
    engine.advance_month(state, "reciprocal")
    letters, audit = engine.advance_month(state, "reciprocal")
    assert len(audit["field_encounters"]) == 1
    assert all(m["status"] == "returning" for m in state["expeditions"])
    assert all(sum(m["cohorts"].values()) == 75 for m in state["expeditions"])
    assert engine.absent(state, "c3") == 75
    assert state["cities"]["c3"]["fideles"] == 20
    assert len([e for e in letters if e["kind"] == "field"]) == 2
    assert not [e for e in letters if e["kind"] == "battle"]
    engine.advance_month(state, "reciprocal")
    assert state["cities"]["c3"]["fideles"] == 95


@case("frontier-occupation", REQ)
def test_occupation():
    """Given a city captured in Moon two with inherited defenders.
    When its new owner attempts departure through the following three Moons.
    Then the locals defend but cannot depart until Moon six.
    """
    state = realm()
    state["cities"]["c3"].update(fideles=500, population=1500)
    seal(state, "p1", "c4", "c3", 400)
    engine.advance_month(state, "occupation")
    engine.advance_month(state, "occupation")
    city = state["cities"]["c4"]
    assert city["owner"] == "p1"
    assert city["restricted_until"] == 6
    assert city["restricted_fideles"] == city["fideles"]
    before = deepcopy(state)
    with pytest.raises(RuleError):
        seal(state, "p1", "c5", "c4", 20, "raid")
    assert state == before
    for _ in range(3):
        engine.advance_month(state, "occupation")
    assert state["month"] == 6
    assert engine.deployable_fideles(state, "c4") == city["fideles"]


@case("frontier-local-pool-loss", REQ)
def test_local_pool_loss():
    """Given sixty restricted and forty free local Faithful during integration.
    When ten local soldiers die and twenty friendly survivors return.
    Then six restricted soldiers die and the returning twenty remain free to depart.
    """
    state = realm()
    city = state["cities"]["c1"]
    city.update(restricted_fideles=60, restricted_until=5)
    engine.lose_local_fideles(state, city, 10)
    city["fideles"] += 20
    assert city["restricted_fideles"] == 54
    assert engine.deployable_fideles(state, "c1") == 56


@case("frontier-away-loss-pool", REQ)
def test_away_loss_pool():
    """Given restricted locals and an independent twenty-man travelling contingent.
    When two absent soldiers die.
    Then their local restricted pool is unchanged and only the absent population falls.
    """
    state = realm()
    city = state["cities"]["c1"]
    city.update(restricted_fideles=60, restricted_until=5)
    mission = {"cohorts": {"c1": 20}}
    engine.lose_attackers(state, mission, 2, sorted(state["cities"]))
    assert (city["fideles"], city["restricted_fideles"], city["population"]) == (100, 60, 998)
    assert mission["cohorts"] == {"c1": 18}


@case("frontier-restricted-relief", REQ)
@pytest.mark.parametrize("restricted,expected", [(100, 0), (60, 8)])
def test_restricted_relief(restricted, expected):
    """Given {restricted} of Qasr's hundred Faithful are locally restricted.
    When automatic relief is allocated to a nearby capture threat.
    Then Qasr exports exactly {expected} unrestricted soldiers.
    """
    state = realm()
    state["cities"]["c1"].update(restricted_fideles=restricted, restricted_until=5)
    seal(state, "p2", "c3", "c4", 80)
    engine.advance_month(state, "relief")
    allocation = engine.relief_allocations(state, state["expeditions"], sorted(state["cities"]))
    assert sum(a["count"] for a in allocation if a["origin"] == "c1") == expected


@case("frontier-disconnected-assembly", REQ)
def test_disconnected_assembly():
    """Given two friendly but disconnected components border the same enemy target.
    When one order attempts to combine troops from both components.
    Then confirmation rejects the impossible common assembly without reservations or spending.
    """
    state = realm()
    state["cities"]["c6"]["owner"] = "p1"
    before = deepcopy(state)
    with pytest.raises(RuleError, match="même cité"):
        engine.confirm_order(
            state,
            "p1",
            {"kind": "raid", "target": "c4", "contributions": {"c3": 20, "c6": 20}},
            "disconnected",
        )
    assert state == before


@case("frontier-route-candidates", REQ)
@pytest.mark.parametrize("third,sixth,expected", [(20, 40, "c6"), (20, 20, "c3")])
def test_route_candidates(third, sixth, expected):
    """Given two friendly frontier candidates contributing {third} and {sixth} soldiers.
    When their combined army is sealed toward their shared neighbor.
    Then the largest local contingent wins the route selection with city-ID ties giving {expected}.
    """
    state = realm()
    state["cities"]["c6"]["owner"] = "p1"
    state["links"].append(["c3", "c6"])
    order = engine.confirm_order(
        state,
        "p1",
        {"kind": "raid", "target": "c4", "contributions": {"c3": third, "c6": sixth}},
        "choice",
    )
    assert order["launch_city"] == expected


@case("frontier-lost-assembly", REQ)
def test_lost_assembly():
    """Given a sealed expedition whose own assembly route subsequently disappears.
    When the departure Moon closes.
    Then the order is invalidated with no expenditure and no marching troops.
    """
    state = realm()
    order = seal(state, "p1", "c4", "c1", 80)
    state["links"] = []
    engine.advance_month(state, "lost-route")
    assert order["status"] == "invalidated"
    assert state["cities"]["c1"]["stock"] == 900000
    assert state["expeditions"] == []


@case("frontier-warning-bands", REQ)
@pytest.mark.parametrize(
    "men,phrase",
    [(20, "Moins de 50"), (50, "50 et 99"), (100, "100 et 199"), (200, "Au moins 200")],
)
def test_warning_bands(men, phrase):
    """Given a watched frontier and a departing force of {men} raiders.
    When level-two surveillance records the departure.
    Then the defender learns the coarse band {phrase} without an exact troop field.
    """
    state = realm()
    state["cities"]["c3"]["fideles"] = 250
    state["cities"]["c4"]["watch"] = 2
    seal(state, "p1", "c4", "c3", men, "raid")
    engine.advance_month(state, "bands")
    warning = player_view(state, "p2")["owned_cities"][0]["incoming_warnings"][0]
    assert phrase in str(warning["force"])
    assert "men" not in warning


@case("frontier-warning-idempotency", REQ)
def test_warning_idempotency():
    """Given a watched departure with a warning already recorded.
    When detection is repeated at the same level and then upgraded within that departure phase.
    Then the first warning is not duplicated and one richer immutable warning is added.
    """
    state = realm()
    state["cities"]["c4"]["watch"] = 1
    seal(state, "p1", "c4", "c3", 80)
    events = []
    engine.depart_orders(state, events)
    engine.detect_departures(state, events)
    engine.detect_departures(state, events)
    state["cities"]["c4"]["watch"] = 2
    engine.detect_departures(state, events)
    assert [w["level"] for w in state["expeditions"][0]["warnings"]] == [1, 2]
    assert len([e for e in events if e["kind"] == "warning"]) == 2


@case("frontier-new-owner-intelligence", REQ)
def test_new_owner_intelligence():
    """Given intelligence recorded for the original owner of an attacked city.
    When a third house takes that city before arrival.
    Then the new owner does not inherit the original owner's warning record.
    """
    state = realm()
    state["cities"]["c4"]["watch"] = 2
    seal(state, "p1", "c4", "c3", 80)
    engine.advance_month(state, "ownership")
    state["cities"]["c4"]["owner"] = "p3"
    city = next(c for c in player_view(state, "p3")["owned_cities"] if c["id"] == "c4")
    assert city["incoming_warnings"] == []
    assert not city["engaged"]


@case("frontier-friendly-departure-warning", REQ)
def test_friendly_departure_warning():
    """Given a watched target that becomes friendly after an army leaves.
    When departure detection is evaluated again.
    Then the friendly army creates no enemy threat warning.
    """
    state = realm()
    seal(state, "p1", "c4", "c3", 80)
    engine.depart_orders(state, [])
    state["cities"]["c4"].update(owner="p1", watch=2)
    events = []
    engine.detect_departures(state, events)
    assert events == []


@case("frontier-legacy-without-marker", REQ)
def test_legacy_without_marker():
    """Given a historical save with no strategic-version marker.
    When an army is sealed toward a city already targeted by an expedition.
    Then its original exclusive reservation and free engagement projection remain intact.
    """
    state = realm()
    del state["strategy_version"]
    seal(state, "p1", "c4", "c3", 20, "raid", "one")
    assert player_view(state, "p2")["owned_cities"][0]["engaged"]
    with pytest.raises(RuleError, match="déjà engagée"):
        seal(state, "p1", "c4", "c1", 20, "raid", "two")


@case("frontier-equipped-victor-continues", REQ)
def test_equipped_victor_continues():
    """Given eighty superior-equipped capturers meeting eighty ordinary capturers.
    When the superior army wins decisively and falls below the original launch minimum.
    Then its seventy-eight survivors still reach the city and resolve a separate assault.
    """
    state = realm()
    state["cities"]["c3"]["forge"] = 3
    seal(state, "p1", "c4", "c3", 80)
    seal(state, "p2", "c3", "c4", 80)
    engine.advance_month(state, "equipped")
    _, audit = engine.advance_month(state, "equipped")
    assert audit["field_encounters"][0]["losses"] == [2, 10]
    assert audit["outcomes"]["p1c4"]["outcome"] == "assault"
    assert state["cities"]["c4"]["owner"] == "p1"
    assert sum(state["expeditions"][0]["cohorts"].values()) == 72


@case("frontier-aggregate-road", REQ)
def test_aggregate_road():
    """Given two forty-man raids facing one eighty-man raid on the opposite road.
    When all three expeditions meet during the same Moon.
    Then there is one encounter and each side loses five soldiers in total.
    """
    state = realm()
    seal(state, "p1", "c4", "c3", 40, "raid", "one")
    seal(state, "p1", "c4", "c3", 40, "raid", "two")
    seal(state, "p2", "c3", "c4", 80, "raid", "three")
    engine.advance_month(state, "aggregate")
    _, audit = engine.advance_month(state, "aggregate")
    assert audit["field_encounters"] == [
        {"road": ["c3", "c4"], "outcome": "contested", "losses": [5, 5]}
    ]
    assert sum(sum(m["cohorts"].values()) for m in state["expeditions"][:2]) == 75


@case("frontier-separate-marching", REQ)
@pytest.mark.parametrize("variation", ["one-sided", "different-month", "same-house"])
def test_separate_marching(variation):
    """Given opposing-looking movements with the exception {variation}.
    When encounter eligibility is checked.
    Then no reciprocal hostile road battle occurs.
    """
    state = realm()
    seal(state, "p1", "c4", "c3", 80)
    seal(state, "p2", "c3", "c4", 80)
    engine.depart_orders(state, [])
    missions = state["expeditions"]
    if variation == "one-sided":
        missions = missions[:1]
    elif variation == "different-month":
        missions[1]["departure_month"] += 1
    else:
        missions[1]["actor"] = "p1"
    assert engine.resolve_field_encounters(state, missions, []) == []


@case("frontier-new-recruits-free", REQ)
def test_new_recruits_free():
    """Given sixty inherited Faithful still integrating during the annual harvest.
    When ten existing inhabitants are recruited into the contingent.
    Then the inherited sixty remain restricted and the ten new recruits can depart.
    """
    state = realm()
    state["month"] = 12
    city = state["cities"]["c1"]
    city.update(fideles=60, restricted_fideles=60, restricted_until=14)
    engine.harvest_city(state, city, [])
    assert (city["fideles"], city["restricted_fideles"]) == (70, 60)
    assert engine.deployable_fideles(state, "c1") == 10


@case("frontier-reconquest-restarts", REQ)
def test_reconquest_restarts():
    """Given an enemy city with an inherited restriction from an earlier conquest.
    When another house conquers it in Moon two.
    Then its current surviving local contingent receives a fresh release date of Moon six.
    """
    state = realm()
    state["cities"]["c4"].update(restricted_fideles=1, restricted_until=99)
    state["cities"]["c3"].update(fideles=500, population=1500)
    seal(state, "p1", "c4", "c3", 400)
    engine.advance_month(state, "reconquest")
    engine.advance_month(state, "reconquest")
    city = state["cities"]["c4"]
    assert city["owner"] == "p1"
    assert city["restricted_until"] == 6
    assert city["restricted_fideles"] == city["fideles"] > 1
