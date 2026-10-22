from copy import deepcopy

import pytest

from simulation import engine
from simulation.projections import player_view
from tests.cases import case

pytestmark = pytest.mark.logic


@case(
    "strategy-city-ledger",
    "Owner: visible food risk, eight installed families, crews and useful dates",
)
def test_city_ledger():
    """Given a city with damaged surveillance and a sealed irrigation project.
    When its owner reads the authorized city projection.
    Then food risk, all eight built families and completion dates are explicit.
    """
    state = engine.new_state(opponents="passive", economy_version=4)
    city = state["cities"]["c1"]
    city.update(stock=600000, watch=2, damaged_works=["watch"])
    engine.confirm_order(state, "p1", {"kind": "irrigation", "cities": ["c1"]}, "work")
    view = player_view(state, "p1")
    own = view["owned_cities"][0]
    assert own["siege_food"] == 500000
    assert own["siege_shortfall"] == 200000
    assert len(own["buildings"]) == 8
    watch = next(item for item in own["buildings"] if item["kind"] == "watch")
    assert (watch["level"], watch["effective_level"], watch["damaged"]) == (2, 1, True)
    irrigation = next(item for item in own["buildings"] if item["kind"] == "irrigation")
    assert irrigation["finish_moon"] == 4
    assert own["team_free_moon"] == 4
    assert view["free_teams"] == 2


@case(
    "strategy-projection-privacy",
    "Prompt K: strategic preparation may never inspect hidden enemy means",
)
def test_projection_privacy():
    """Given a reachable enemy city with undisclosed buildings, soldiers and treasury.
    When those private values change without a public event.
    Then its public projection and reachable-origin information remain exactly identical.
    """
    state = engine.new_state(opponents="passive", economy_version=4)
    before = player_view(state, "p1")
    state["cities"]["c4"].update(
        stock=1,
        tax=7,
        fideles=8,
        forge=3,
        watch=2,
        shelter=2,
        siege=2,
        transport=2,
        damaged_works=["shelter"],
    )
    after = player_view(state, "p1")
    assert before["cities"][3] == after["cities"][3]
    assert before["attack_targets"] == after["attack_targets"]
    assert "buildings" not in after["cities"][3]


@case(
    "strategy-work-warning",
    "Owner: spending warnings include post-order reserves and first useful effect",
)
def test_work_warning():
    """Given a three-Moon irrigation project allowed to finish at Moon twenty-four.
    When the owner reads the work quote during Moon twenty-one.
    Then the end-of-reign economic limitation and insufficient siege reserves are visible.
    """
    state = engine.new_state(opponents="passive", economy_version=4, reign_months=24)
    state["cities"]["c1"]["stock"] = 600000
    state["month"] = 21
    before = deepcopy(state)
    quote = next(
        action
        for action in player_view(state, "p1")["work_actions"]
        if action["kind"] == "irrigation"
    )["cities"][0]
    assert (quote["finish_moon"], quote["first_effect_moon"], quote["effect_after_reign"]) == (
        24,
        25,
        True,
    )
    assert (quote["stock_after"], quote["siege_shortfall_after"]) == (300000, 200000)
    assert state == before


@case(
    "strategy-displaced-population",
    "Prompt J: people abroad remain counted once under their original house after capture",
)
def test_displaced_population():
    """Given twenty travelling Faithful whose origin has just been captured.
    When each house reads its authorized accounts and the ranking is calculated.
    Then the twenty belong to their original house and not to the conqueror's population.
    """
    state = engine.new_state(opponents="passive", economy_version=4)
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c1": 20}}, "away"
    )
    engine.advance_month(state, "away")
    engine.detach_absent_contingents(state, "c1")
    state["cities"]["c1"]["owner"] = "p2"
    assert player_view(state, "p1")["population"] == 2020
    assert player_view(state, "p2")["population"] == 3980
    assert sum(row["population"] for row in engine.standings(state)) == 9000
