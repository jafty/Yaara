"""Military outcomes and cash returns remain distinct, recipient-safe accounts."""

import json

import pytest

from simulation import engine
from simulation.messages import render
from tests.cases import case
from tests.stubs import FixedRandom

pytestmark = pytest.mark.logic


@pytest.fixture
def departed_raid(monkeypatch):
    monkeypatch.setattr(engine, "random_stream", FixedRandom())
    state = engine.new_state(opponents="passive", calendar_version=1, map_version=1)
    engine.confirm_order(
        state,
        "p1",
        {"kind": "raid", "target": "c4", "contributions": {"c1": 10, "c2": 10, "c3": 10}},
        "raid",
    )
    engine.advance_month(state, "fixed")
    return state


@case(
    "raid-provisional-balance", "Owner: military success may have a cash deficit, equality or gain"
)
@pytest.mark.parametrize(
    "target_stock,loot,balance",
    [
        (300000, 45000, "déficit de 50\u202f000"),
        (633336, 95000, "nul"),
        (1000000, 150000, "gain de 55\u202f000"),
    ],
    ids=["deficit", "break-even", "gain"],
)
def test_provisional_balance(departed_raid, target_stock, loot, balance):
    """Given a thirty-person raid costing 95000 Measures against an undefended city.
    When its successful combat carries away {loot} Measures.
    Then the attacker sees {balance}, each original payment and a provisional warning.
    """
    state = departed_raid
    state["cities"]["c4"].update(stock=target_stock, fideles=0)
    # Current funds and ownership cannot be used to reconstruct the paid quote.
    state["cities"]["c1"]["stock"] = 0
    state["cities"]["c2"]["owner"] = "p3"
    state["month"] = 2
    events = []
    engine.resolve_combats(state, "fixed", events)
    letter = next(event for event in events if event["recipient"] == "p1")
    assert letter["title"] == "Pillage réussi à Sefra"
    assert "Coût payé pour ce raid : 95\u202f000 Mesures" in letter["body"]
    for name, cost in (
        ("Qasr", "31\u202f667"),
        ("Tamesh", "31\u202f667"),
        ("Namar", "31\u202f666"),
    ):
        assert f"{name} : {cost} Mesures payées" in letter["body"]
    assert f"Solde provisoire : {balance}" in letter["body"]
    assert " ".join(f"Solde provisoire : {balance}".split()) in " ".join(
        letter["body"].split()[:35]
    )
    assert "pertes humaines" in letter["body"] and "prélèvements" in letter["body"]
    assert state["expeditions"][0]["loot"] == loot
    defender = next(event for event in events if event["recipient"] == "p2")
    assert "Coût payé" not in defender["body"]
    assert "Tamesh" not in str(defender["content"])


@case("raid-failed-cost-account", "Owner: a defeated raid still recalls the full paid expense")
def test_failed_cost_account(departed_raid):
    """Given a thirty-person raid against forty encountered defenders.
    When the raid is defeated without loot.
    Then its attacker sees the full 95000-Measure cash deficit without a success claim.
    """
    state = departed_raid
    state["month"] = 2
    events = []
    engine.resolve_combats(state, "fixed", events)
    letter = next(event for event in events if event["recipient"] == "p1")
    assert "réussi" not in letter["title"]
    assert "Solde provisoire : déficit de 95\u202f000" in letter["body"]


@case(
    "raid-final-cash-account",
    "Owner: final raid cash balance uses retained loot after capacity and ownership",
)
@pytest.mark.parametrize(
    "variation,recovered,balance",
    [
        ("gain", 150000, "gain de 55\u202f000"),
        ("overflow", 300, "déficit de 94\u202f700"),
        ("captured-origin", 100000, "gain de 5\u202f000"),
        ("all-origins-captured", 0, "déficit de 95\u202f000"),
        ("annihilated", 0, "déficit de 95\u202f000"),
    ],
    ids=["gain", "overflow", "captured-origin", "all-origins-captured", "annihilated"],
)
def test_final_cash_account(departed_raid, variation, recovered, balance):
    """Given a paid three-origin raid returning under condition {variation}.
    When the return is processed twice.
    Then one attacker account records {balance} from {recovered} retained Measures without duplicate deposits.
    """
    state = departed_raid
    mission = state["expeditions"][0]
    mission.update(status="returning", loot=150000)
    for city_id in ("c1", "c2", "c3"):
        city = state["cities"][city_id]
        city["stock"] = 2400000 - 100 if variation == "overflow" else 0
        if variation == "all-origins-captured" or (
            variation == "captured-origin" and city_id == "c2"
        ):
            city["owner"] = "p3"
    if variation == "annihilated":
        mission.update(cohorts={"c1": 0, "c2": 0, "c3": 0}, loot=0)
    state["month"] = 3
    events = []
    engine.return_expeditions(state, events)
    letters = [event for event in events if event["recipient"] == "p1"]
    assert len(letters) == 1
    letter = letters[0]
    assert f"Solde final des Mesures : {balance}" in letter["body"]
    assert "Qasr : 31\u202f667 Mesures payées" in letter["body"]
    assert "Tamesh : 31\u202f667 Mesures payées" in letter["body"]
    if variation == "annihilated":
        assert letter["title"] == "Une expédition ne reviendra pas"
    for event in events:
        if event["recipient"] != "p1":
            assert "Coût payé" not in str(event) and "31\u202f667" not in str(event)
    stock = sum(city["stock"] for city in engine.owned_cities(state, "p1"))
    assert stock == (7200000 if variation == "overflow" else recovered)
    previous = json.dumps(state, sort_keys=True)
    engine.return_expeditions(state, events)
    assert json.dumps(state, sort_keys=True) == previous
    assert len([event for event in events if event["recipient"] == "p1"]) == 1


@case(
    "raid-legacy-funding-recall",
    "Owner: existing pooled economies recall their saved funding, including non-origin cities",
)
def test_legacy_funding_recall(monkeypatch):
    """Given a legacy raid supplied by one city but funded equally by three granaries.
    When its combat is reported.
    Then all three actual payer shares are recalled without applying new local prices.
    """
    monkeypatch.setattr(engine, "random_stream", FixedRandom())
    state = engine.new_state(
        opponents="passive", calendar_version=1, map_version=1, economy_version=1
    )
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c3": 30}}, "raid"
    )
    engine.advance_month(state, "fixed")
    state["month"] = 2
    events = []
    engine.resolve_combats(state, "fixed", events)
    body = next(event["body"] for event in events if event["recipient"] == "p1")
    assert "Qasr : 31\u202f667 Mesures payées" in body
    assert "Tamesh : 31\u202f667 Mesures payées" in body
    assert "Namar : 31\u202f666 Mesures payées" in body


@case(
    "raid-finance-translation",
    "Owner: stored financial reports render both languages without changing names or amounts",
)
def test_finance_translation(departed_raid):
    """Given a returning raid with a 95000-Measure paid quote and no loot.
    When its stored report is rendered in English and French.
    Then both languages retain the exact original city charges and deficit.
    """
    state = departed_raid
    state["month"] = 3
    events = []
    engine.return_expeditions(state, events)
    content = json.loads(json.dumps(events[0]["content"]["body"]))
    assert "Coût payé pour ce raid : 95\u202f000" in render(content, "fr")
    english = render(content, "en")
    assert "Paid cost of this raid: 95,000" in english
    assert "Tamesh: 31,667 Measures paid" in english
    assert "Final Measures balance: deficit of 95,000" in english
