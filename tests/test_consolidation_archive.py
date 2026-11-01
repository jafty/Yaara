"""Compact recipient archives retain optional consolidation observations."""

import json
from copy import deepcopy

import pytest

from simulation import engine
from simulation.archives import chronicle_accounts, condense_archive
from tests.cases import case

pytestmark = pytest.mark.logic
REQ = "Owner November 1: compact archives preserve recorded own-city consolidation facts"
OPTIONAL = {"consolidating", "consolidation_until", "occupying_fideles", "defense_stock"}


def archive_for(cities, *, later_cities=None, strategy_version=3):
    account = {"owned_cities": cities, "orders": [], "missions": []}
    final = account if later_cities is None else {**account, "owned_cities": later_cities}
    accounts = [{"moon": 3, "houses": {"p1": account}}]
    if later_cities is not None:
        accounts.append({"moon": 6, "houses": {"p1": final}})
    return {
        "game": {"id": "completed-reign", "title": "Consolidation", "final_moon": 6},
        "scope": "player",
        "language": "fr",
        "rule_versions": {"strategy_version": strategy_version},
        "coverage": {"missing_account_moons": [1, 2, 4, 5]},
        "ranking": [],
        "reports": [],
        "accounts": accounts,
        "final_accounts": {"p1": final},
    }


@case("consolidation-compact-observations", REQ)
def test_optional_observations_survive_compaction():
    """Given recorded city accounts during and after consolidation
    When the already authorized archive is condensed
    Then optional facts survive in deltas and final accounts without changing history
    """
    first = {
        "id": "c4",
        "stock": 600_000,
        "available_stock": 0,
        "consolidating": True,
        "consolidation_until": 6,
        "occupying_fideles": 40,
        "defense_stock": 600_000,
    }
    later = {**first, "available_stock": 600_000, "consolidating": False, "occupying_fideles": 0}
    archive = archive_for([first], later_cities=[later])
    before = deepcopy(archive)
    compact = condense_archive(archive)
    assert {key: compact["city_changes"][0]["set"][key] for key in OPTIONAL} == {
        "consolidating": True,
        "consolidation_until": 6,
        "occupying_fideles": 40,
        "defense_stock": 600_000,
    }
    assert compact["city_changes"][1]["set"] == {
        "available_stock": 600_000,
        "consolidating": False,
        "occupying_fideles": 0,
    }
    final = compact["final_accounts"]["p1"]["owned_cities"][0]
    assert {key: final[key] for key in OPTIONAL} == {
        "consolidating": False,
        "consolidation_until": 6,
        "occupying_fideles": 0,
        "defense_stock": 600_000,
    }
    assert compact["schema_version"] == 1 and compact["format"] == "yaara-condensed"
    assert archive == before


@case("consolidation-compact-legacy-absence", REQ)
def test_old_accounts_do_not_invent_consolidation_facts():
    """Given an old city observation without consolidation fields
    When its archive is condensed under the existing schema
    Then historical and final accounts omit unavailable facts instead of inventing defaults
    """
    archive = archive_for([{"id": "c1", "stock": 500_000}], strategy_version=2)
    compact = condense_archive(archive)
    assert not OPTIONAL.intersection(compact["city_changes"][0]["set"])
    assert not OPTIONAL.intersection(compact["final_accounts"]["p1"]["owned_cities"][0])
    assert compact["rule_versions"] == {"strategy_version": 2}
    assert compact["coverage"] == archive["coverage"]


@case("consolidation-compact-missing-observation", REQ)
def test_missing_optional_facts_are_unset():
    """Given two recorded accounts whose later city observation lacks earlier optional facts
    When their compact deltas are generated
    Then missing facts are explicitly unset without inferring release or zero guards
    """
    old = {
        "id": "c1",
        "stock": 500_000,
        "consolidating": True,
        "consolidation_until": 6,
        "occupying_fideles": 40,
        "defense_stock": 500_000,
    }
    compact = condense_archive(archive_for([old], later_cities=[{"id": "c1", "stock": 500_000}]))
    assert compact["city_changes"][1] == {
        "moon": 6,
        "actor": "p1",
        "city": "c1",
        "set": {},
        "unset": sorted(OPTIONAL),
    }


@case("consolidation-compact-recipient-privacy", REQ)
def test_real_recipient_projection_keeps_enemy_private_state_out():
    """Given an actual conquest and a rival city with private consolidation and financial state
    When only the recipient's projected account is condensed
    Then its occupation facts survive without rival accounts or private simulation fields
    """
    state = engine.new_state(opponents="passive", strategy_version=3)
    state["cities"]["c4"].update(fideles=1, stock=600_000)
    state["cities"]["c5"]["fideles"] = 0
    state["cities"]["c6"]["fideles"] = 0
    engine.confirm_order(
        state,
        "p1",
        {"kind": "capture", "target": "c4", "contributions": {"c3": 80}},
        "own-capture",
    )
    engine.advance_month(state, "archive-capture")
    engine.advance_month(state, "archive-capture")
    assert state["cities"]["c4"]["owner"] == "p1"
    state["cities"]["c5"].update(stock=987_654, tax=876_543, consolidation_until=99)
    state["seed"] = "private-seed-never-export"
    own = chronicle_accounts(state)["p1"]
    archive = archive_for(own["owned_cities"])
    archive["accounts"][0]["houses"]["p1"] = own
    archive["final_accounts"]["p1"] = own
    compact = condense_archive(archive)
    captured = next(row["set"] for row in compact["city_changes"] if row["city"] == "c4")
    assert {key: captured[key] for key in OPTIONAL} == {
        "consolidating": True,
        "consolidation_until": 6,
        "occupying_fideles": 40,
        "defense_stock": 600_000,
    }
    assert {row["actor"] for row in compact["city_changes"]} == {"p1"}
    assert {row["city"] for row in compact["city_changes"]} == {"c1", "c2", "c3", "c4"}
    serialized = json.dumps(compact)
    assert not any(
        forbidden in serialized
        for forbidden in (
            "private-seed-never-export",
            "987654",
            "876543",
            "combativity",
            "cohort_equipment",
            "attack_strength",
        )
    )
