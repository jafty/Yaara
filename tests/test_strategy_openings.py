"""Human-plausible fixed plans, separate from the automatic opponents' policy."""

import pytest

from simulation import engine
from tests.cases import case
from tests.test_strategy_combat import RaidDraw

pytestmark = pytest.mark.logic


@case(
    "strategy-repeated-human-sieges",
    "Owner: anticipate repeated human siege pressure and the actual window for convoy defense",
)
@pytest.mark.parametrize(
    "response,fall_moon,held",
    [
        ("none", 5, 1),
        ("invest", 5, 1),
        ("react", 5, 1),
        ("anticipate", 8, 2),
        ("supply", None, 4),
    ],
)
def test_repeated_sieges(response, fall_moon, held):
    """Given two houses with 900000 Measures per city and a defender following {response}.
    When 150 attackers return and attempt another siege every three Moons before harvest.
    Then {held} sieges hold and the target falls at {fall_moon}, with late convoys unable to save it.
    """
    state = engine.new_state(opponents="passive")
    plans = {
        "react": {3: ("c5", 500000)},
        "anticipate": {2: ("c5", 500000)},
        "supply": {2: ("c5", 500000), 5: ("c6", 500000), 8: ("c5", 300000)},
    }
    sieges = []
    actual_fall = None
    for moon in range(1, 13):
        if response == "invest" and moon == 1:
            engine.confirm_order(state, "p2", {"kind": "irrigation", "cities": ["c4"]}, "invest")
        if moon in (1, 4, 7, 10):
            engine.confirm_order(
                state,
                "p1",
                {
                    "kind": "capture",
                    "target": "c4",
                    "contributions": {"c1": 50, "c2": 50, "c3": 50},
                },
                f"attack-{moon}",
            )
        plan = plans.get(response, {})
        if moon in plan:
            origin, cargo = plan[moon]
            engine.confirm_order(
                state,
                "p2",
                {
                    "kind": "convoy",
                    "origin": origin,
                    "target": "c4",
                    "cargo": cargo,
                },
                f"convoy-{moon}",
            )
        _, audit = engine.advance_month(state, "human-opening")
        sieges.extend(outcome["outcome"] for outcome in audit["outcomes"].values())
        if state["cities"]["c4"]["owner"] != "p2":
            actual_fall = moon
            break
    assert actual_fall == fall_moon
    assert sieges.count("held") == held
    assert sieges.count("shortage") == (fall_moon is not None)
    costs = sum(order["cost"] for order in state["orders"] if order["kind"] == "capture")
    assert costs == 350000 * len(sieges)
    if response == "react":
        assert state["convoys"][0]["status"] == "returning"
        assert state["cities"]["c4"]["stock"] == 0
    if response == "supply":
        assert state["cities"]["c4"]["stock"] == 1400800
        assert all(convoy["status"] == "completed" for convoy in state["convoys"])


@case(
    "strategy-human-raid-season",
    "Owner: a military win early in the year differs from a raid timed just before harvest",
)
@pytest.mark.parametrize("departure,retained,net", [(1, 3000, -53000), (10, 135000, 79000)])
def test_raid_season(monkeypatch, departure, retained, net):
    """Given ordinary undefended-year crops and fifty-one raiders facing forty village defenders.
    When a player departs at Moon {departure} and receives the survivors' spoils.
    Then retained spoils are {retained} and the monetary balance is {net}, without guaranteed overall profit.
    """
    monkeypatch.setattr(engine, "random_stream", lambda *args: RaidDraw())
    state = engine.new_state(opponents="passive")
    while state["month"] < departure:
        engine.advance_month(state, "season")
    order = engine.confirm_order(
        state,
        "p1",
        {
            "kind": "raid",
            "target": "c4",
            "contributions": {"c1": 51},
        },
        "seasonal",
    )
    engine.advance_month(state, "season")
    _, audit = engine.advance_month(state, "season")
    engine.advance_month(state, "season")
    mission = state["expeditions"][0]
    assert audit["outcomes"]["seasonal"]["outcome"] == "success"
    assert mission["recovered_loot"] == retained
    assert retained - order["cost"] == net
    assert mission["cohorts"] == {"c1": 50}


@case(
    "strategy-alternating-human-armies",
    "Owner: alternating armies can renew siege pressure before the first convoy response arrives",
)
@pytest.mark.parametrize("convoy_departure,fall_moon", [(None, 4), (3, 4), (1, None)])
def test_alternating_armies(convoy_departure, fall_moon):
    """Given two 150-person armies and a defender convoy departing at {convoy_departure}.
    When the armies attack on Moons two and four using distinct contingents.
    Then the city falls at {fall_moon}; only supply anticipated before the first battle saves it.
    """
    state = engine.new_state(opponents="passive")
    actual_fall = None
    outcomes = []
    for moon in range(1, 5):
        if moon in (1, 3):
            engine.confirm_order(
                state,
                "p1",
                {
                    "kind": "capture",
                    "target": "c4",
                    "contributions": {"c1": 50, "c2": 50, "c3": 50},
                },
                f"wave-{moon}",
            )
        if moon == convoy_departure:
            engine.confirm_order(
                state,
                "p2",
                {
                    "kind": "convoy",
                    "origin": "c5",
                    "target": "c4",
                    "cargo": 500000,
                },
                "supply",
            )
        _, audit = engine.advance_month(state, "alternating-armies")
        outcomes.extend(row["outcome"] for row in audit["outcomes"].values())
        if state["cities"]["c4"]["owner"] != "p2":
            actual_fall = moon
    assert actual_fall == fall_moon
    assert outcomes == ["held", "held" if fall_moon is None else "shortage"]
    assert sum(order["cost"] for order in state["orders"] if order["actor"] == "p1") == 700000


@case(
    "strategy-human-border-counterattack",
    "Owner: attacking exposed origins can cut a repeat siege route",
)
def test_border_counterattack():
    """Given 150 attackers drawn from all three cities and 200 counterattackers from the defender's rear cities.
    When both armies reach the opposite frontier during Moon two.
    Then the first siege holds but the counterattack captures its border origin and closes its route.
    """
    state = engine.new_state(opponents="passive", strategy_version=1)
    engine.confirm_order(
        state,
        "p1",
        {
            "kind": "capture",
            "target": "c4",
            "contributions": {"c1": 50, "c2": 50, "c3": 50},
        },
        "pressure",
    )
    engine.confirm_order(
        state,
        "p2",
        {
            "kind": "capture",
            "target": "c3",
            "contributions": {"c5": 100, "c6": 100},
        },
        "counter",
    )
    engine.advance_month(state, "human-counter")
    _, audit = engine.advance_month(state, "human-counter")
    assert audit["outcomes"]["pressure"]["outcome"] == "held"
    assert audit["outcomes"]["counter"]["outcome"] == "assault"
    assert state["cities"]["c3"]["owner"] == state["cities"]["c4"]["owner"] == "p2"
    assert not engine.eligible_origins(state, "p1", "c4")
    assert state["expeditions"][0]["detached_origins"] == ["c3"]
