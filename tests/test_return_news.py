"""One return account per expedition and recipient, with local figures intact."""

from copy import deepcopy

import pytest

from simulation import engine
from simulation.messages import render
from tests.builders import rich_state
from tests.cases import case

pytestmark = pytest.mark.logic


@pytest.fixture
def returning_army():
    state = rich_state()
    engine.confirm_order(
        state,
        "p1",
        {"kind": "raid", "target": "c4", "contributions": {"c1": 10, "c2": 20, "c3": 30}},
        "raid",
    )
    engine.advance_month(state, "fixed")
    state["month"] = 3
    state["expeditions"][0].update(status="returning", loot=9000)
    for city_id in ("c1", "c2", "c3"):
        state["cities"][city_id]["stock"] = 0
    return state


@case(
    "return-news-grouped", "Owner: multi-city returns produce one letter with every local account"
)
def test_grouped_return(returning_army):
    """Given one returning expedition from three cities with 9000 Measures of loot.
    When the survivors return and return processing is retried.
    Then one letter records all three city accounts and each deposit happens once.
    """
    state = returning_army
    events = []
    engine.return_expeditions(state, events)
    assert len(events) == 1 and events[0]["recipient"] == "p1"
    assert events[0]["kind"] == "return"
    for city_id, count, loot in (("c1", 10, 1500), ("c2", 20, 3000), ("c3", 30, 4500)):
        city = state["cities"][city_id]
        assert city["stock"] == loot and city["fideles"] == 100
        assert f"{count} Fidèles à {city['name']}" in events[0]["body"]
        assert city["name"] in render(events[0]["content"]["body"], "en")
    before = deepcopy(state)
    engine.return_expeditions(state, events)
    assert state == before and len(events) == 1


@case(
    "return-news-recipient-split", "Rules §17: return accounts disclose only the recipient's cities"
)
def test_recipient_split(returning_army):
    """Given one expedition whose middle origin now belongs to another house.
    When its contingents return to their origins.
    Then each owner receives one letter containing only their own local accounts.
    """
    state = returning_army
    state["cities"]["c2"]["owner"] = "p2"
    events = []
    engine.return_expeditions(state, events)
    assert len(events) == 2
    letters = {event["recipient"]: event for event in events}
    for actor, own, hidden in (("p1", ("c1", "c3"), ("c2",)), ("p2", ("c2",), ("c1", "c3"))):
        text = str(letters[actor])
        assert all(state["cities"][city]["name"] in text for city in own)
        assert all(state["cities"][city]["name"] not in text for city in hidden)
        assert state["cities"]["c4"]["name"] not in text
    assert state["cities"]["c2"]["fideles"] == 100
    assert state["cities"]["c2"]["stock"] == 3000


@case(
    "return-news-separate-missions",
    "Owner: distinct expeditions returning together keep distinct letters",
)
def test_separate_missions(returning_army):
    """Given two distinct expeditions due to return in the same Moon.
    When both returns are processed.
    Then two separate expedition letters are emitted to their shared recipient.
    """
    state = returning_army
    second = deepcopy(state["expeditions"][0])
    second["id"] = "second"
    state["expeditions"].append(second)
    state["orders"].append({**deepcopy(state["orders"][0]), "id": "second"})
    for city_id, count in second["cohorts"].items():
        state["cities"][city_id]["fideles"] -= count
    events = []
    engine.return_expeditions(state, events)
    assert len(events) == 2 and all(event["recipient"] == "p1" for event in events)
    assert all(city["fideles"] == 100 for city in engine.owned_cities(state, "p1"))
    assert sum(city["stock"] for city in engine.owned_cities(state, "p1")) == 18000


@case("return-news-empty-origin", "Owner: an origin with no survivors adds no empty return news")
def test_empty_origin(returning_army):
    """Given a returning expedition whose first origin has no survivors.
    When the remaining contingents return.
    Then one letter describes only the two returning contingents and their loot.
    """
    state = returning_army
    state["expeditions"][0]["cohorts"]["c1"] = 0
    events = []
    engine.return_expeditions(state, events)
    assert len(events) == 1
    assert state["cities"]["c1"]["name"] not in str(events)
    assert state["cities"]["c1"]["stock"] == 0
    assert state["cities"]["c1"]["fideles"] == 90
    assert state["cities"]["c2"]["stock"] == 3600
    assert state["cities"]["c3"]["stock"] == 5400
