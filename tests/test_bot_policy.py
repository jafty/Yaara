"""Bots use normal commands and fixed choices, never hidden enemy information."""

from copy import deepcopy

import pytest

from simulation import engine
from tests.cases import case
from tests.stubs import FixedRandom

pytestmark = pytest.mark.logic


@pytest.fixture
def bot_state(monkeypatch):
    monkeypatch.setattr(engine, "random_stream", FixedRandom())
    state = engine.new_state(opponents="passive")
    state["players"]["p1"]["bot"] = True
    return state


@case(
    "bot-policy", "Decisions: modest bots use own available resources and normal validated orders"
)
@pytest.mark.parametrize(
    "variation,kind",
    [
        ("irrigation", "irrigation"),
        ("walls", "walls"),
        ("raid", "raid"),
        ("capture", "capture"),
        ("equipment", "equipment"),
        ("storage", "storage"),
        ("no-proposal", None),
        ("unaffordable", None),
        ("eliminated", None),
        ("no-raid-troops", None),
    ],
)
def test_bot_policy(bot_state, variation, kind):
    """Given the bot resource condition {variation}.
    When its policy chooses orders.
    Then it accepts only the expected kind {kind} through normal validation or leaves state unchanged when no order is possible.
    """
    state = bot_state
    state["month"] = {"irrigation": 3, "walls": 1, "raid": 2}.get(variation, 4)
    if variation in ("irrigation", "capture", "equipment", "storage"):
        for city in engine.owned_cities(state, "p1"):
            city["stock"] = 2400000
    if variation == "irrigation":
        for city in engine.owned_cities(state, "p1"):
            city["stock"] = 1000000
    if variation in ("equipment", "storage"):
        for city in engine.owned_cities(state, "p1"):
            city["fideles"] = 40
    if variation == "storage":
        state["players"]["p1"]["equipment"] = 2
    if variation == "unaffordable":
        state["month"] = 3
        for city in engine.owned_cities(state, "p1"):
            city["stock"] = 0
    if variation == "eliminated":
        state["players"]["p1"]["eliminated"] = True
    if variation == "no-raid-troops":
        state["month"] = 2
        for city in engine.owned_cities(state, "p1"):
            city["fideles"] = 44
    before = deepcopy(state)
    accepted = engine.bot_orders(state, "fixed")
    if kind is None:
        assert accepted == []
        assert state == before
    else:
        assert len(accepted) == 1
        assert accepted[0]["kind"] == kind
        assert accepted[0]["actor"] == "p1"
        assert accepted[0]["status"] == "confirmed"
        assert state["orders"] == accepted
        assert state["cities"] == before["cities"]
        engine.assert_invariants(state)


@case("bot-skips-existing-walls", "Decisions: bot wall proposals concern only unfortified cities")
def test_bot_skips_walls(bot_state):
    """Given a bot realm whose first city already has walls.
    When the bot proposes fortification.
    Then it selects an unfortified city instead.
    """
    bot_state["month"] = 1
    bot_state["cities"]["c1"]["walls"] = 1
    accepted = engine.bot_orders(bot_state, "fixed")
    assert len(accepted) == 1
    assert accepted[0]["tasks"][0]["city"] == "c2"


@case(
    "bot-hidden-state-independent",
    "Decisions: bots do not consult hidden enemy population, stock or military strength",
)
def test_bot_hidden_state(bot_state):
    """Given two otherwise identical realms with different hidden enemy resources.
    When the bots choose orders with the same draw.
    Then their accepted orders are identical.
    """
    bot_state["month"] = 2
    replica = deepcopy(bot_state)
    for city in replica["cities"].values():
        if city["owner"] != "p1":
            city.update(stock=0, population=50000, fideles=10000)
    assert engine.bot_orders(bot_state, "fixed") == engine.bot_orders(replica, "fixed")


@case("bot-v0-no-v1-projects", "Rules V0: bots cannot propose equipment or storage")
def test_v0_bot(bot_state):
    """Given a V0 bot with abundant funds but too few troops for a campaign.
    When it chooses an order.
    Then it proposes neither equipment nor storage.
    """
    bot_state["rules"] = "V0"
    bot_state["month"] = 4
    for city in engine.owned_cities(bot_state, "p1"):
        city.update(stock=2400000, fideles=40)
    assert engine.bot_orders(bot_state, "fixed") == []
