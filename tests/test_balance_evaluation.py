"""Behavioral checks for the offline comparison's information and accounting boundaries."""

from collections import Counter
from copy import deepcopy

import pytest

from scripts import evaluate_consolidation as evaluation
from simulation import engine
from simulation.rules import RuleError
from tests.cases import case

pytestmark = pytest.mark.logic


@case(
    "balance-evaluation-private-state-independent",
    "Owner: comparison policies use owned state and public geography rather than hidden opponents",
)
def test_policy_does_not_observe_opponent_resources():
    """Given identical public ownership and own resources but different hidden enemy resources.
    When the comparison constructs the early expansion policy's observation and proposals.
    Then observations and proposed commands are identical and enemy private fields are absent.
    """
    state = engine.new_state(opponents="passive", strategy_version=2)
    changed = deepcopy(state)
    for city in changed["cities"].values():
        if city["owner"] != "p1":
            city.update(stock=1, tax=9000000, fideles=1, population=2000, forge=3, watch=2)
    first = evaluation.observe(state, "p1", [])
    second = evaluation.observe(changed, "p1", [])
    assert first == second
    assert list(evaluation.proposals(first, "early", "same")) == list(
        evaluation.proposals(second, "early", "same")
    )
    assert set(first["public"]["c4"]) == {"owner", "walls"}


@case(
    "balance-evaluation-patient-delay-boundary",
    "Owner: patient counterexpansion is a declared fixed policy rather than an implicit bot threshold",
)
def test_patient_capture_starts_after_two_harvests():
    """Given a patient house with sufficient troops and reserves at Moons twenty-four and twenty-five.
    When the declared patient policy proposes commands on each side of its timing boundary.
    Then it proposes no capture before Moon twenty-five and proposes capture from that Moon.
    """
    state = engine.new_state(opponents="passive", strategy_version=2)
    for city in engine.owned_cities(state, "p1"):
        city["stock"] = 2000000
    state["month"] = 24
    before = list(evaluation.proposals(evaluation.observe(state, "p1", []), "patient", "fixed"))
    state["month"] = 25
    after = list(evaluation.proposals(evaluation.observe(state, "p1", []), "patient", "fixed"))
    assert not any(spec["kind"] == "capture" for spec in before)
    assert any(spec["kind"] == "capture" for spec in after)


@case(
    "balance-evaluation-settled-raid-absence",
    "Owner: raid comparisons debit actual fees and production forgone and wait for settled loot",
)
def test_raid_ledger_tracks_actual_absence_and_settlement():
    """Given sixty raiders departing at Moon ten toward forty defenders guaranteed by surveillance.
    When the evaluator observes monthly absence through the actual return and settles its ledger.
    Then it debits two monthly absences and the paid fee against actually recovered loot.
    """
    state = engine.new_state(opponents="passive", strategy_version=2)
    state["cities"]["c4"]["watch"] = 1
    while state["month"] < 10:
        engine.advance_month(state, "ledger")
    order = engine.confirm_order(
        state,
        "p1",
        {"kind": "raid", "target": "c4", "contributions": {"c1": 60}},
        "observed-raid",
    )
    absence = {}
    for _ in range(3):
        evaluation.record_raid_absence(state, absence)
        engine.advance_month(state, "ledger")
    mission = state["expeditions"][0]
    assert mission["status"] == "completed"
    assert absence["observed-raid"] == 11900
    ledger = evaluation.raid_ledger(state, "p1", absence)
    assert ledger["settled_raids"] == 1
    assert ledger["settled_raid_fees"] == order["cost"] == 65000
    assert ledger["settled_raid_absence"] == 11900
    assert ledger["settled_raid_net_after_absence"] == mission["recovered_loot"] - 76900


@case(
    "balance-evaluation-rotated-paired-comparison",
    "Owner: the baseline and revised comparison rotates each declared policy through every position",
)
def test_comparison_pairs_seeds_and_all_positions():
    """Given one seed and a short legacy-only observation run.
    When the comparison rotates the three declared policies across the three houses twice.
    Then results reproduce exactly and every policy appears once at every house position.
    """
    first = evaluation.compare(seeds=1, scenarios=("baseline",), reign_months=24)
    second = evaluation.compare(seeds=1, scenarios=("baseline",), reign_months=24)
    assert first == second
    assert len(first["runs"]) == 3
    for actor in ("p1", "p2", "p3"):
        assert {run["policies"][actor] for run in first["runs"]} == {
            "early",
            "patient",
            "raider",
        }
    assert all(run["counts"]["capture_target_exclusivity_rejections"] == 0 for run in first["runs"])
    assert all(sum(row["cities"] for row in run["standings"]) == 9 for run in first["runs"])


@case(
    "balance-evaluation-frozen-funding-excluded",
    "Owner: comparison policies respect a captured city's unavailable treasury and inherited troops",
)
def test_consolidating_city_is_not_an_available_funding_source():
    """Given a revised captured city whose treasury and inherited troops are still restricted.
    When the comparison builds an observation and proposes military contributions.
    Then no proposal spends that city's stock or sends its unavailable local men.
    """
    state = engine.new_state(opponents="passive", strategy_version=3)
    city = state["cities"]["c1"]
    city.update(consolidation_until=5, restricted_until=5, restricted_fideles=100)
    view = evaluation.observe(state, "p1", [])
    assert view["owned"]["c1"]["funds"] == 0
    assert view["owned"]["c1"]["men"] == 0
    assert all(
        "c1" not in proposal.get("contributions", {})
        for proposal in evaluation.proposals(view, "early", "fixed")
    )


@case(
    "balance-evaluation-target-rejection-classification",
    "Owner: comparison distinguishes raid blocking from an already pending capture",
)
@pytest.mark.parametrize("pending_kind,men", [("raid", 20), ("capture", 80)])
def test_target_rejection_classification(pending_kind, men):
    """Given a revised house with an accepted {pending_kind} toward an enemy city.
    When another capture is rejected and the independent observer classifies the rejection.
    Then the report attributes it to the actual pending mission kind and its own house.
    """
    state = engine.new_state(opponents="passive", strategy_version=3)
    engine.confirm_order(
        state,
        "p1",
        {"kind": pending_kind, "target": "c4", "contributions": {"c1": men}},
        "pending",
    )
    proposal = {"kind": "capture", "target": "c4", "contributions": {"c2": 100, "c3": 100}}
    with pytest.raises(RuleError) as caught:
        engine.confirm_order(state, "p1", proposal, "blocked")
    counts = Counter()
    evaluation.record_validation_failure(counts, state, "p1", proposal, caught.value)
    assert counts == {
        "capture_target_exclusivity_rejections": 1,
        "capture_rejections_pending_" + pending_kind: 1,
        "capture_rejections_own_pending": 1,
    }


@case(
    "balance-evaluation-infrequent-seasonal-decision",
    "Owner: optional infrequent decisions anticipate the next seasonal window instead of deleting raids",
)
def test_infrequent_raider_anticipates_next_seasonal_window():
    """Given a seasonal raider deciding at Moon four and next returning three Moons later.
    When it proposes commands for the upcoming decision interval.
    Then it can raid before the seasonal window passes while a per-Moon decision would wait.
    """
    state = engine.new_state(opponents="passive", strategy_version=2)
    state["month"] = 4
    view = evaluation.observe(state, "p1", [])
    frequent = list(evaluation.proposals(view, "raider", "fixed", decision_every=1))
    infrequent = list(evaluation.proposals(view, "raider", "fixed", decision_every=3))
    assert not any(spec["kind"] == "raid" for spec in frequent)
    assert any(spec["kind"] == "raid" for spec in infrequent)
