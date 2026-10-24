"""Seeded full-reign journeys supplement the independent frontier contracts."""

import pytest

from simulation import engine
from tests.cases import case

pytestmark = pytest.mark.journey


@case(
    "frontier-full-reign",
    "Owner October 24: the combined frontier rules remain playable through a complete reign",
)
@pytest.mark.parametrize("seed", range(10))
def test_frontier_reign(seed):
    """Given three active houses using the new frontier rules and a fixed seed.
    When normal validated orders resolve until the reign ends.
    Then every closure preserves population, reservations and local-resource invariants.
    """
    state = engine.new_state()
    for player in state["players"].values():
        player["bot"] = True
    closures = 0
    while state["status"] == "active":
        engine.bot_orders(state, str(seed))
        engine.advance_month(state, str(seed))
        engine.assert_invariants(state)
        closures += 1
        assert closures <= 120
    assert state["result"]["standings"][0]["rank"] == 1
    assert sum(len(engine.owned_cities(state, actor)) for actor in state["players"]) == 9
