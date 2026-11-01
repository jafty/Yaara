"""Independent contracts for exclusive targets and automatic occupation."""

from copy import deepcopy

import pytest

from simulation import engine
from simulation.projections import player_view
from simulation.rules import RuleError
from tests.cases import case

pytestmark = pytest.mark.logic
REQ = "Owner November 1: exclusive military targets and three-Moon automatic consolidation"


def realm(strategy=3):
    return engine.new_state(opponents="passive", strategy_version=strategy)


def seal(state, actor, target, contributions, identity="capture", kind="capture"):
    return engine.confirm_order(
        state,
        actor,
        {"kind": kind, "target": target, "contributions": contributions},
        identity,
    )


def tick(state):
    return engine.advance_month(state, "consolidation-contract")


def capture(
    *, strategy=3, contributions=None, existing_work=False, early_origin_loss=False, origin_forge=0
):
    state = realm(strategy)
    for city in state["cities"].values():
        city["fideles"] = 0
    contributions = {"c3": 81} if contributions is None else contributions
    for origin, count in contributions.items():
        state["cities"][origin]["fideles"] = max(100, count)
        state["cities"][origin]["forge"] = origin_forge
    if existing_work:
        engine.confirm_order(state, "p2", {"kind": "irrigation", "cities": ["c4"]}, "old-work")
    seal(state, "p1", "c4", contributions)
    tick(state)
    if early_origin_loss:
        state["links"].append(["c3", "c5"])
        state["cities"]["c5"].update(fideles=1000, stock=2_400_000)
        seal(state, "p2", "c3", {"c5": 1000}, "early-origin-loss")
    tick(state)
    if early_origin_loss:
        tick(state)
    return state


def occupier(state, actor="p1"):
    return next(
        mission
        for mission in state["expeditions"]
        if mission["kind"] == "occupation" and mission["actor"] == actor
    )


def lose_origin(state):
    state["links"].append(["c3", "c5"])
    state["cities"]["c5"].update(fideles=1000, stock=2_400_000)
    seal(state, "p2", "c3", {"c5": 1000}, "origin-loss")
    tick(state)
    tick(state)


@case("consolidation-default-version", REQ)
@pytest.mark.parametrize(
    "economy,expected",
    [pytest.param(4, 3, id="current-economy"), pytest.param(3, 1, id="historical-economy")],
)
def test_default_version(economy, expected):
    """Given a request to create a game with saved economy {economy}.
    When the native aggregates are initialized.
    Then the saved strategy marker is {expected} without rebasing historical economies.
    """
    assert engine.new_state(economy_version=economy)["strategy_version"] == expected


@case("consolidation-target-conflict", REQ)
@pytest.mark.parametrize("first", ["raid", "capture"])
@pytest.mark.parametrize("second", ["raid", "capture"])
@pytest.mark.parametrize("rival", [False, True], ids=["same-house", "different-house"])
def test_target_conflict(first, second, rival):
    """Given a committed {first} and a funded competing {second} from another troop pool.
    When the second confirmation attempts to reserve the same city.
    Then the original commitment remains and the rejected attempt changes no state.
    """
    state = realm()
    state["cities"]["c5"]["owner"] = "p3"
    seal(state, "p1", "c4", {"c3": 80}, "first", first)
    before = deepcopy(state)
    with pytest.raises(RuleError, match="déjà"):
        seal(state, "p3" if rival else "p1", "c4", {"c5" if rival else "c1": 80}, "second", second)
    assert state == before
    assert engine.active_targets(state) == {"c4": "first"}


@case("consolidation-preview-no-priority", REQ)
def test_preview_no_priority():
    """Given an unsealed quote toward a city whose target is still available.
    When another house seals first and the original quote is reviewed again.
    Then quotes reserve nothing and the original house cannot displace the committed order.
    """
    state = realm()
    state["cities"]["c5"]["owner"] = "p3"
    spec = {"kind": "capture", "target": "c4", "contributions": {"c3": 80}}
    before = deepcopy(state)
    assert engine.prepare_order(state, "p1", spec, "preview")["cost"] == 210_000
    assert state == before
    seal(state, "p3", "c4", {"c5": 80}, "winner")
    before = deepcopy(state)
    assert engine.prepare_order(state, "p1", spec, "preview")["cost"] == 210_000
    with pytest.raises(RuleError, match="déjà"):
        engine.confirm_order(state, "p1", spec, "preview")
    assert state == before


@case("consolidation-idempotent-confirmation", REQ)
def test_confirmation_idempotent():
    """Given a successful confirmation that already owns its target reservation.
    When its original request identifier is delivered again.
    Then the existing order is returned without self-conflict or another resource reservation.
    """
    state = realm()
    order = seal(state, "p1", "c4", {"c3": 80})
    before = deepcopy(state)
    assert seal(state, "p1", "c4", {"c3": 80}) is order
    assert state == before


@case("consolidation-cancel-releases-target", REQ)
def test_cancel_releases_target():
    """Given a sealed attack whose target is exclusively reserved.
    When its owner cancels before departure and another house confirms.
    Then the new house acquires the target while the first army and its entire fee stay home.
    """
    state = realm()
    state["cities"]["c5"]["owner"] = "p3"
    seal(state, "p1", "c4", {"c3": 80})
    engine.cancel_order(state, "p1", "capture")
    seal(state, "p3", "c4", {"c5": 80}, "replacement")
    assert engine.active_targets(state) == {"c4": "replacement"}
    assert state["cities"]["c3"]["stock"] == 900_000
    assert state["cities"]["c3"]["fideles"] == 100
    assert engine.reservations(state)[0]["c3"] == 0
    assert engine.reservations(state)[1]["c3"] == 0


@case("consolidation-outbound-target-lock", REQ)
def test_outbound_target_lock():
    """Given an attack that has departed but has not resolved combat.
    When another funded house attempts to confirm toward its target.
    Then the target remains locked even though the first order has spent its resources.
    """
    state = realm()
    state["cities"]["c5"]["owner"] = "p3"
    seal(state, "p1", "c4", {"c3": 80})
    tick(state)
    before = deepcopy(state)
    with pytest.raises(RuleError, match="déjà"):
        seal(state, "p3", "c4", {"c5": 80}, "second")
    assert state == before


@case("consolidation-combat-releases-target", REQ)
def test_combat_releases_target():
    """Given an attack repelled at a city whose army is still returning.
    When another house confirms an attack after combat resolution.
    Then the completed combat releases the target without waiting for the first army to return.
    """
    state = realm()
    state["cities"]["c5"]["owner"] = "p3"
    seal(state, "p1", "c4", {"c3": 80})
    tick(state)
    tick(state)
    assert state["orders"][0]["status"] == "returning"
    assert engine.active_targets(state) == {}
    seal(state, "p3", "c4", {"c5": 80}, "second")
    assert engine.active_targets(state) == {"c4": "second"}


@case("consolidation-invalidation-releases-target", REQ)
def test_invalidation_releases_target():
    """Given an accepted attack whose contributing city changes ownership before departure.
    When the departure is invalidated and another house confirms toward its target.
    Then the invalid order releases the target and none of its quoted price is spent.
    """
    state = realm()
    state["cities"]["c5"]["owner"] = "p3"
    seal(state, "p1", "c4", {"c3": 80})
    state["cities"]["c3"]["owner"] = "p2"
    tick(state)
    assert state["orders"][0]["status"] == "invalidated"
    assert state["cities"]["c3"]["stock"] == 900_000
    seal(state, "p3", "c4", {"c5": 80}, "second")
    assert engine.active_targets(state) == {"c4": "second"}


@case("consolidation-odd-survivor-split", REQ)
def test_odd_survivor_split():
    """Given eighty-one victorious soldiers from one origin and no battle casualties.
    When their undefended target is captured in Moon two.
    Then forty-one occupy the city and forty return without creating or reattaching people.
    """
    state = capture()
    occupation = occupier(state)
    returning = next(m for m in state["expeditions"] if m["id"] == "capture")
    assert occupation["id"] == "capture:occupation"
    assert occupation["order_id"] == "capture"
    assert occupation["actor"] == "p1"
    assert occupation["status"] == "occupying"
    assert occupation["cohorts"] == {"c3": 41}
    assert returning["cohorts"] == {"c3": 40}
    assert occupation["release_month"] == 6
    assert occupation["return_month"] == 7
    assert state["cities"]["c4"]["consolidation_until"] == 6
    assert state["cities"]["c3"]["population"] == 1000
    assert state["cities"]["c4"]["population"] == 1000
    assert engine.absent(state, "c3") == 81
    assert engine.active_targets(state) == {}
    assert sum(city["population"] for city in state["cities"].values()) == 9000


@case("consolidation-multiple-origin-split", REQ)
def test_multiple_origin_split():
    """Given a victorious army of thirty-one and fifty soldiers from distinct origins.
    When its occupation detachment is proportionally assigned after capture.
    Then sixteen and twenty-five remain while the other forty retain their original cohorts.
    """
    state = capture(contributions={"c1": 31, "c3": 50})
    occupation = occupier(state)
    returning = next(m for m in state["expeditions"] if m["id"] == "capture")
    assert occupation["cohorts"] == {"c1": 16, "c3": 25}
    assert returning["cohorts"] == {"c1": 15, "c3": 25}
    assert engine.absent(state, "c1") == 31
    assert engine.absent(state, "c3") == 50
    assert occupation["cohort_equipment"] == returning["cohort_equipment"]


@case("consolidation-automatic-lifecycle", REQ)
def test_automatic_lifecycle():
    """Given a Moon-two conquest with forty-one occupiers and forty ordinary returnees.
    When five further Moons close without player input.
    Then returnees arrive in three and occupiers depart in six and arrive in seven exactly once.
    """
    state = capture()
    occupation = occupier(state)
    order = next(o for o in state["orders"] if o["id"] == "capture")
    tick(state)
    assert state["cities"]["c3"]["fideles"] == 59
    assert engine.absent(state, "c3") == 41
    assert order["status"] == "returning"
    tick(state)
    tick(state)
    assert occupation["status"] == "occupying"
    assert state["cities"]["c3"]["fideles"] == 59
    tick(state)
    assert occupation["status"] == "returning"
    assert state["cities"]["c3"]["fideles"] == 59
    tick(state)
    assert occupation["status"] == order["status"] == "completed"
    assert state["cities"]["c3"]["fideles"] == 100
    assert engine.absent(state, "c3") == 0
    before = deepcopy(state)
    engine.return_expeditions(state, [])
    assert state == before


@case("consolidation-treasury-rejections", REQ)
@pytest.mark.parametrize("kind", ["irrigation", "convoy", "capture"])
def test_treasury_rejections(kind):
    """Given a newly conquered city with a full treasury and newly available local recruits.
    When it attempts to fund a new {kind} during consolidation.
    Then the action is rejected atomically while the treasury remains available for defense.
    """
    state = capture()
    state["cities"]["c4"]["fideles"] = 80
    spec = (
        {"kind": "convoy", "origin": "c4", "target": "c3", "cargo": 100_000}
        if kind == "convoy"
        else {"kind": "capture", "target": "c5", "contributions": {"c4": 80}}
        if kind == "capture"
        else {"kind": "irrigation", "cities": ["c4"]}
    )
    before = deepcopy(state)
    with pytest.raises(RuleError):
        engine.confirm_order(state, "p1", spec, "frozen")
    assert state == before
    assert state["cities"]["c4"]["stock"] == 900_000


@case("consolidation-treasury-boundary", REQ)
@pytest.mark.parametrize("moon,allowed", [(3, False), (5, False), (6, True)])
def test_treasury_boundary(moon, allowed):
    """Given a Moon-two conquest with a consolidation expiry in Moon six.
    When a new irrigation decree is confirmed in Moon {moon}.
    Then acceptance is {allowed} at the exact three-full-Moon boundary.
    """
    state = capture()
    while state["month"] < moon:
        tick(state)
    before = deepcopy(state)
    if allowed:
        order = engine.confirm_order(state, "p1", {"kind": "irrigation", "cities": ["c4"]}, "new")
        assert order["cost"] == 300_000
    else:
        with pytest.raises(RuleError):
            engine.confirm_order(state, "p1", {"kind": "irrigation", "cities": ["c4"]}, "new")
        assert state == before


@case("consolidation-existing-work-and-tax", REQ)
def test_existing_work_and_tax():
    """Given irrigation funded by the former ruler before a Moon-two conquest.
    When the captured city remains under consolidation through Moon five.
    Then work finishes in Moon four and its monthly levy rises without spending captured reserves.
    """
    state = capture(existing_work=True)
    assert state["cities"]["c4"]["stock"] == 600_000
    tick(state)
    tick(state)
    tick(state)
    assert state["cities"]["c4"]["irrigation"] == 1
    assert state["cities"]["c4"]["tax"] == 515_000
    assert state["cities"]["c4"]["stock"] == 600_000
    assert next(w for w in state["works"] if w["order_id"] == "old-work")["status"] == "completed"


@case("consolidation-occupation-opportunity-cost", REQ)
def test_occupation_opportunity_cost():
    """Given forty-one occupiers physically absent from their original producing city.
    When another Moon of levy accrual is processed after ordinary returnees arrive.
    Then their origin produces for nine hundred fifty-nine residents and the target gains no taxpayers.
    """
    state = capture()
    tick(state)
    origin_tax = state["cities"]["c3"]["tax"]
    target_tax = state["cities"]["c4"]["tax"]
    tick(state)
    assert state["cities"]["c3"]["tax"] - origin_tax == 95_900
    assert state["cities"]["c4"]["tax"] - target_tax == 100_000


@case("consolidation-occupation-wall-defense", REQ)
def test_occupation_wall_defense():
    """Given forty-one occupiers behind level-one walls with no inherited local garrison.
    When one hundred ordinary enemies attack the provisioned city.
    Then occupation troops hold behind the walls and siege rations include their physical presence.
    """
    state = capture()
    state["cities"]["c4"]["walls"] = 1
    state["cities"]["c5"]["fideles"] = 100
    seal(state, "p2", "c4", {"c5": 100}, "counter")
    tick(state)
    _, audit = tick(state)
    assert audit["outcomes"]["counter"]["outcome"] == "held"
    assert audit["outcomes"]["counter"]["food_used"] == 520_500
    assert state["cities"]["c4"]["owner"] == "p1"
    assert state["cities"]["c4"]["stock"] == 379_500


@case("consolidation-occupation-frozen-equipment", REQ)
def test_occupation_frozen_equipment():
    """Given occupiers who departed with ordinary gear before their origin's arsenal changes.
    When their origin gains superior gear and one hundred forty-five ordinary enemies attack.
    Then ordinary occupiers suffer an assault instead of receiving their origin's later wall strength.
    """
    state = capture()
    state["cities"]["c3"]["forge"] = 3
    state["cities"]["c5"]["fideles"] = 145
    seal(state, "p2", "c4", {"c5": 145}, "equipment-counter")
    tick(state)
    _, audit = tick(state)
    assert audit["outcomes"]["equipment-counter"]["outcome"] == "assault"
    assert occupier(state)["cohort_equipment"] == {"c3": 100}
    assert state["cities"]["c4"]["owner"] == "p2"


@case("consolidation-occupation-raid-casualty", REQ)
def test_occupation_raid_casualty():
    """Given forty-one occupation troops defending villages under full surveillance.
    When forty ordinary raiders defeat the twenty-four mobilized occupiers.
    Then one occupier dies from its original population and the captured city's local troops stay zero.
    """
    state = capture()
    state["cities"]["c4"]["watch"] = 2
    state["cities"]["c5"]["fideles"] = 40
    seal(state, "p2", "c4", {"c5": 40}, "raid", "raid")
    tick(state)
    _, audit = tick(state)
    assert audit["outcomes"]["raid"]["defender_deaths"] == 1
    assert occupier(state)["cohorts"] == {"c3": 40}
    assert state["cities"]["c3"]["population"] == 999
    assert state["cities"]["c3"]["military_deaths"] == 1
    assert state["cities"]["c4"]["fideles"] == 0


@case("consolidation-raid-equipment-observation", REQ)
@pytest.mark.parametrize(
    "forge,local,expected",
    [
        pytest.param(0, 0, "équipement ordinaire", id="ordinary-occupation-only"),
        pytest.param(3, 0, "équipement du grand arsenal", id="superior-occupation-only"),
        pytest.param(3, 20, "ensemble d’équipements variés", id="mixed-local-and-occupation"),
    ],
)
def test_raid_equipment_observation(forge, local, expected):
    """Given occupiers with arsenal level {forge} and {local} ordinary native troops.
    When eighty raiders survive a village encounter and report the defenders' equipment.
    Then their recipient letter describes {expected} from the troops actually mobilized.
    """
    state = capture(origin_forge=forge)
    state["cities"]["c4"].update(watch=2, fideles=local)
    state["cities"]["c5"]["fideles"] = 80
    seal(state, "p2", "c4", {"c5": 80}, "equipment-raid", "raid")
    tick(state)
    letters, _ = tick(state)
    attack = next(e for e in letters if e["recipient"] == "p2" and e["kind"] == "battle")
    assert expected in str(attack["body"])
    if local == 0:
        assert "ensemble d’équipements variés" not in str(attack["body"])


@case("consolidation-raid-zero-cohort-observation", REQ)
def test_raid_zero_cohort_observation():
    """Given a mixed eighty-man army whose one superior soldier is assigned to the returning half.
    When raiders encounter the forty ordinary occupiers left in the conquered city's villages.
    Then their letter reports ordinary gear despite the empty superior origin retained in its records.
    """
    state = realm()
    for city in state["cities"].values():
        city["fideles"] = 0
    state["cities"]["c2"].update(fideles=1, forge=3)
    state["cities"]["c3"]["fideles"] = 79
    seal(state, "p1", "c4", {"c2": 1, "c3": 79})
    tick(state)
    tick(state)
    occupation = occupier(state)
    assert occupation["cohorts"] == {"c2": 0, "c3": 40}
    assert occupation["cohort_equipment"] == {"c2": 145, "c3": 100}
    state["cities"]["c4"]["watch"] = 2
    state["cities"]["c5"]["fideles"] = 80
    seal(state, "p2", "c4", {"c5": 80}, "zero-cohort-raid", "raid")
    tick(state)
    letters, _ = tick(state)
    attack = next(e for e in letters if e["recipient"] == "p2" and e["kind"] == "battle")
    assert "équipement ordinaire" in str(attack["body"])
    assert "ensemble d’équipements variés" not in str(attack["body"])


@case("consolidation-raid-unmobilized-occupation-observation", REQ)
def test_raid_unmobilized_occupation_observation():
    """Given one superior occupier surviving beside one hundred ordinary native soldiers.
    When watch posts mobilize forty native soldiers and no occupation troops against eighty raiders.
    Then the raiders report ordinary equipment without learning the unencountered occupier's gear.
    """
    state = capture(origin_forge=3)
    occupier(state)["cohorts"]["c3"] = 1
    state["cities"]["c3"].update(population=960, military_deaths=40)
    state["cities"]["c4"].update(watch=1, fideles=100)
    state["cities"]["c5"]["fideles"] = 80
    seal(state, "p2", "c4", {"c5": 80}, "native-only-raid", "raid")
    tick(state)
    letters, _ = tick(state)
    attack = next(e for e in letters if e["recipient"] == "p2" and e["kind"] == "battle")
    assert "équipement ordinaire" in str(attack["body"])
    assert "ensemble d’équipements variés" not in str(attack["body"])
    assert occupier(state)["cohorts"] == {"c3": 1}
    assert state["cities"]["c3"]["population"] == 960


@case("consolidation-occupation-recapture", REQ)
def test_occupation_recapture():
    """Given forty-one occupation troops and eleven automatic relief troops in a captured city.
    When two hundred forty ordinary enemies force a rapid surrender.
    Then one occupier dies and its forty survivors retreat for next-Moon return without changing house.
    """
    state = capture()
    state["cities"]["c5"]["fideles"] = 120
    state["cities"]["c6"]["fideles"] = 120
    seal(state, "p2", "c4", {"c5": 120, "c6": 120}, "recapture")
    tick(state)
    _, audit = tick(state)
    old = occupier(state)
    assert audit["outcomes"]["recapture"]["outcome"] == "surrender"
    assert state["cities"]["c4"]["owner"] == "p2"
    assert old["actor"] == "p1"
    assert old["cohorts"] == {"c3": 40}
    assert old["status"] == "returning"
    assert old["return_month"] == 5
    assert state["cities"]["c3"]["population"] == 999
    assert state["cities"]["c4"]["fideles"] == 0
    tick(state)
    assert old["status"] == "completed"
    assert state["cities"]["c3"]["fideles"] == 99


@case("consolidation-origin-loss-detaches-occupiers", REQ)
def test_origin_loss_detaches_occupiers():
    """Given forty-one occupiers whose origin is captured while they remain abroad.
    When the origin's present population transfers to the new sovereign.
    Then the occupiers remain with their house and are removed from the origin's attached population once.
    """
    state = capture()
    lose_origin(state)
    occupation = occupier(state)
    assert state["cities"]["c3"]["owner"] == "p2"
    assert occupation["actor"] == "p1"
    assert occupation["cohorts"] == {"c3": 41}
    assert occupation["detached_origins"] == ["c3"]
    assert state["cities"]["c3"]["population"] == 958
    assert engine.displaced_population(state, "p1") == 41
    assert engine.absent(state, "c3") == 0


@case("consolidation-detached-occupation-casualty", REQ)
def test_detached_occupation_casualty():
    """Given occupiers already detached after their original city changed sovereign.
    When a later village raid kills one of those occupiers.
    Then their displaced contingent shrinks without removing another resident of the conquered origin.
    """
    state = capture(early_origin_loss=True)
    assert state["cities"]["c3"]["owner"] == "p2"
    assert engine.displaced_population(state, "p1") == 41
    state["cities"]["c4"]["watch"] = 2
    state["cities"]["c6"]["fideles"] = 40
    seal(state, "p2", "c4", {"c6": 40}, "detached-raid", "raid")
    population = state["cities"]["c3"]["population"]
    tick(state)
    _, audit = tick(state)
    assert audit["outcomes"]["detached-raid"]["defender_deaths"] == 1
    assert state["cities"]["c3"]["population"] == population
    assert occupier(state)["cohorts"] == {"c3": 40}
    assert engine.displaced_population(state, "p1") == 40


@case("consolidation-return-fallback", REQ)
def test_return_fallback():
    """Given occupiers whose lost origin has no friendly neighbor of the occupied city for refuge.
    When their occupation ends and their scheduled return arrives.
    Then they return to the origin's new ruler with its remaining restriction and are counted once.
    """
    state = capture()
    lose_origin(state)
    occupation = occupier(state)
    while state["month"] <= 7:
        tick(state)
    assert occupation["status"] == "completed"
    assert state["cities"]["c3"]["owner"] == "p2"
    assert state["cities"]["c3"]["population"] == 999
    assert state["cities"]["c3"]["fideles"] == 99
    assert state["cities"]["c3"]["restricted_fideles"] == 99
    assert engine.displaced_population(state, "p1") == 0
    assert occupation["arrived_origins"] == ["c3"]


@case("consolidation-private-projections", REQ)
def test_private_projections():
    """Given a city under consolidation with a forty-one-man occupation detachment.
    When its owner and a rival read their permitted projections.
    Then only the owner receives occupation counts and treasury deadlines without numerical combativity.
    """
    state = capture()
    own = player_view(state, "p1")
    city = next(c for c in own["owned_cities"] if c["id"] == "c4")
    assert city["stock"] == 900_000
    assert city["available_stock"] == 0
    assert city["consolidation_until"] == 6
    assert city["occupying_fideles"] == 41
    enemy = next(c for c in player_view(state, "p2")["cities"] if c["id"] == "c4")
    assert "consolidation_until" not in enemy
    assert "occupying_fideles" not in enemy
    assert "stock" not in enemy
    assert "combativity" not in repr(own)


@case("consolidation-legacy-capture", REQ)
@pytest.mark.parametrize("strategy", [1, 2])
def test_legacy_capture(strategy):
    """Given a saved game explicitly using strategic version {strategy}.
    When its eighty-one soldiers capture a city.
    Then the entire army returns on the original schedule and captured funds are immediately usable.
    """
    state = capture(strategy=strategy)
    assert len(state["expeditions"]) == 1
    assert state["expeditions"][0]["cohorts"] == {"c3": 81}
    assert "consolidation_until" not in state["cities"]["c4"]
    city = next(c for c in player_view(state, "p1")["owned_cities"] if c["id"] == "c4")
    assert city["available_stock"] == 900_000
    tick(state)
    assert state["cities"]["c3"]["fideles"] == 100
    assert state["orders"][0]["status"] == "completed"


@case("consolidation-active-wall-experiment", REQ)
@pytest.mark.parametrize(
    "strategy,experimental,walls,dead",
    [
        pytest.param(3, True, 0, 3, id="initial-defenses"),
        pytest.param(3, True, 1, 5, id="first-walls"),
        pytest.param(3, True, 2, 6, id="second-walls"),
        pytest.param(3, True, 3, 8, id="third-walls"),
        pytest.param(3, False, 3, 3, id="live-rules-control"),
        pytest.param(2, True, 3, 3, id="legacy-unaffected"),
    ],
)
def test_active_wall_experiment(strategy, experimental, walls, dead):
    """Given a provisioned city at wall level {walls} and experimental defense {experimental}.
    When one hundred fifty ordinary attackers hold a siege under strategy version {strategy}.
    Then attacker losses are {dead} while the city's ration and defender casualties stay unchanged.
    """
    state = realm(strategy)
    state["config"]["experimental_active_walls"] = experimental
    state["cities"]["c3"]["fideles"] = 150
    state["cities"]["c4"]["walls"] = walls
    seal(state, "p1", "c4", {"c3": 150}, "wall-experiment")
    tick(state)
    _, audit = tick(state)
    outcome = audit["outcomes"]["wall-experiment"]
    assert outcome["outcome"] == "held"
    assert outcome["attacker_deaths"] == dead
    assert outcome.get("active_wall_losses", 0) == dead - 3
    assert outcome["defender_deaths"] == 1
    assert outcome["food_used"] == 500_000
    assert state["cities"]["c4"]["stock"] == 400_000
    assert state["cities"]["c4"]["owner"] == "p2"
    assert state["expeditions"][0]["cohorts"] == {"c3": 150 - dead}
