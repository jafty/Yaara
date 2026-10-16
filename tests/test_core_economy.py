"""Explicit prices, financing, annual accounts and recruitment boundaries."""

import pytest

from simulation import engine
from tests.builders import rich_state
from tests.cases import case

pytestmark = pytest.mark.logic


@case(
    "work-quote",
    "Rules §18: construction and repair have fixed prices, durations and resulting levels",
)
@pytest.mark.parametrize(
    "kind,current,cost,duration",
    [
        ("irrigation", 0, 2400000, 6),
        ("irrigation", 1, 4800000, 12),
        ("storage", 0, 500000, 4),
        ("storage", 1, 1200000, 8),
        ("walls", 0, 1200000, 8),
        ("walls", 1, 9600000, 20),
        ("repair", 1, 240000, 3),
        ("repair", 2, 1920000, 6),
    ],
)
def test_work_quote(kind, current, cost, duration):
    """Given a {kind} work at current level {current}.
    When its next work is quoted.
    Then the cost is {cost} and duration is {duration} with the appropriate resulting level.
    """
    state = rich_state()
    city = state["cities"]["c1"]
    city["walls" if kind == "repair" else kind] = current
    city["damaged"] = kind == "repair"
    quote = engine.work_spec(state, city, kind)
    assert quote == {
        "city": "c1",
        "kind": kind,
        "level": current if kind == "repair" else current + 1,
        "cost": cost,
        "duration": duration,
    }


@case("local-storage-capacity", "Rules §18: each storage level has its own local capacity")
@pytest.mark.parametrize("level,capacity", [(0, 2400000), (1, 3600000), (2, 6000000)])
def test_storage_capacity(level, capacity):
    """Given a city with storage level {level}.
    When its local capacity is consulted.
    Then it can hold {capacity} Measures.
    """
    city = engine.new_state(calendar_version=1)["cities"]["c1"]
    city["storage"] = level
    assert engine.capacity(city) == capacity


@case(
    "pooled-funding-proportional",
    "Decisions: local available stocks fund orders proportionally across disconnected holdings",
)
def test_pooled_funding():
    """Given disconnected holdings with 600000 and 400000 free Measures.
    When a 500000-Measure granary is confirmed.
    Then funding reserves 300000 and 200000 without spending the stocks.
    """
    state = engine.new_state(calendar_version=1)
    state["cities"]["c1"]["stock"] = 600000
    state["cities"]["c2"].update(owner="p2", stock=0)
    state["cities"]["c3"]["stock"] = 400000
    order = engine.confirm_order(state, "p1", {"kind": "storage", "cities": ["c1"]}, "store")
    assert order["funding"] == {"c1": 300000, "c3": 200000}
    assert state["cities"]["c1"]["stock"] == 600000
    assert state["cities"]["c3"]["stock"] == 400000


@case(
    "annual-overflow",
    "Rules §4,13,18: annual tax stays local, stops at capacity and discards overflow",
)
@pytest.mark.parametrize(
    "stock,tax,expected",
    [
        pytest.param(0, 0, 100000, id="room"),
        pytest.param(2300000, 0, 2400000, id="exact-capacity"),
        pytest.param(2399999, 0, 2400000, id="overflow"),
        pytest.param(2400000, 0, 2400000, id="already-full"),
    ],
)
def test_annual_overflow(stock, tax, expected):
    """Given local stock {stock} and accrued tax {tax} at harvest.
    When annual tax is collected.
    Then local stock becomes {expected} and overflow is discarded without moving it to another city.
    """
    state = engine.new_state(calendar_version=1)
    state["month"] = 12
    state["cities"]["c1"].update(stock=stock, tax=tax)
    other = state["cities"]["c2"]["stock"]
    events = []
    engine.annual_economy(state, events)
    assert state["cities"]["c1"]["stock"] == expected
    assert state["cities"]["c1"]["tax"] == 0
    assert state["cities"]["c2"]["stock"] == other + 100000
    assert events[0]["recipient"] == "p1"


@case(
    "annual-recruitment",
    "Rules §14: growth precedes renewal, recruitment is capped at one percent and ten percent strength",
)
@pytest.mark.parametrize(
    "version,troops,expected_population,expected_troops",
    [
        pytest.param("V0", 100, 1000, 100, id="v0-no-growth"),
        pytest.param("V1", 100, 1005, 100, id="at-ceiling"),
        pytest.param("V1", 99, 1005, 100, id="one-vacancy"),
        pytest.param("V1", 80, 1005, 90, id="recruitment-cap"),
    ],
)
def test_annual_recruitment(version, troops, expected_population, expected_troops):
    """Given {version} rules and {troops} Faithful before harvest.
    When growth and recruitment are applied.
    Then population becomes {expected_population} and Faithful strength becomes {expected_troops}.
    """
    state = engine.new_state(version, calendar_version=1)
    state["month"] = 12
    state["cities"]["c1"]["fideles"] = troops
    engine.annual_economy(state, [])
    assert state["cities"]["c1"]["population"] == expected_population
    assert state["cities"]["c1"]["fideles"] == expected_troops


@case(
    "monthly-irrigation-yield",
    "Rules §4: each irrigation level adds 100 Mesures per present inhabitant monthly",
)
@pytest.mark.parametrize("level,tax", [(0, 100000), (1, 200000), (2, 300000)])
def test_monthly_yield(level, tax):
    """Given a city with irrigation level {level}.
    When one month of tax accrues.
    Then accrued tax is {tax} and spendable stock remains unchanged.
    """
    state = engine.new_state(calendar_version=1)
    state["month"] = 1
    state["cities"]["c1"]["irrigation"] = level
    engine.annual_economy(state, [])
    assert state["cities"]["c1"]["tax"] == tax
    assert state["cities"]["c1"]["stock"] == 600000
