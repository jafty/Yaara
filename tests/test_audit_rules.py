"""Approved audit revision: local funding, restrained frontiers and irrigation."""

from copy import deepcopy

import pytest

from simulation import engine
from simulation.projections import player_view
from simulation.rules import RuleError
from tests.cases import case

pytestmark = pytest.mark.logic


@case("audit-irrigation", "Owner: new yield is 100/130/200; saved economies remain 100/200/300")
@pytest.mark.parametrize(
    "version,level,expected",
    [(1, 0, 100), (1, 1, 200), (1, 2, 300), (2, 0, 100), (2, 1, 130), (2, 2, 200)],
)
def test_irrigation(version, level, expected):
    """Given an economy {version} city with irrigation {level} and 1000 residents.
    When one Moon accrues and the owner reads the accounts.
    Then income and the displayed per-resident yield agree with {expected}.
    """
    state = engine.new_state(economy_version=version, opponents="passive")
    state["cities"]["c1"]["irrigation"] = level
    engine.advance_month(state, "audit")
    assert state["cities"]["c1"]["tax"] == expected * 1000
    assert player_view(state, "p1")["owned_cities"][0]["yield"] == expected


@case("audit-initial-frontiers", "Owner: each starting group reaches one city per rival house")
@pytest.mark.parametrize(
    "actor,targets", [("p1", {"c4", "c9"}), ("p2", {"c3", "c7"}), ("p3", {"c1", "c6"})]
)
def test_initial_frontiers(actor, targets):
    """Given a new reign with three connected starting city groups.
    When {actor} inspects its frontier.
    Then only {targets} are reachable with all friendly origins eligible.
    """
    state = engine.new_state()
    assert state["map_version"] == 3
    assert len({tuple(sorted(edge)) for edge in state["links"]}) == 12
    assert {c for c in state["cities"] if engine.eligible_origins(state, actor, c)} == targets
    owned = {c["id"] for c in engine.owned_cities(state, actor)}
    assert all(engine.eligible_origins(state, actor, c) == owned for c in targets)


@case("audit-local-work", "Owner: only a work's destination funds it, at exact affordability")
def test_local_work():
    """Given Qasr has exactly 500000 Measures and the other cities have 600000.
    When its storage decree is sealed and its Moon closes.
    Then only Qasr reserves and spends the construction price.
    """
    state = engine.new_state(opponents="passive")
    state["cities"]["c1"]["stock"] = 500000
    order = engine.confirm_order(state, "p1", {"kind": "storage", "cities": ["c1"]}, "local")
    assert order["funding"] == {"c1": 500000}
    assert state["cities"]["c1"]["stock"] == 500000
    engine.advance_month(state, "audit")
    assert [state["cities"][c]["stock"] for c in ("c1", "c2", "c3")] == [0, 600000, 600000]


@case("audit-local-shortfall", "Owner: rich neighbours cannot subsidize a local shortfall")
@pytest.mark.parametrize("kind", ["storage", "raid"])
def test_local_shortfall(kind):
    """Given the concerned city lacks one Measure while its neighbours are rich.
    When a {kind} decree is requested.
    Then it is rejected with a named local shortfall and no state mutation.
    """
    state = engine.new_state(opponents="passive")
    spec = (
        {"kind": kind, "cities": ["c1", "c2"]}
        if kind == "storage"
        else {"kind": "raid", "target": "c4", "contributions": {"c2": 20}}
    )
    state["cities"]["c2"]["stock"] = 499999 if kind == "storage" else 69999
    before = deepcopy(state)
    with pytest.raises(RuleError, match="Tamesh"):
        engine.confirm_order(state, "p1", spec, "shortfall")
    assert state == before


@case(
    "audit-local-expedition",
    "Owner: origins pay their troops plus a proportional fixed departure fee",
)
@pytest.mark.parametrize(
    "kind,contributions,expected",
    [
        ("raid", {"c1": 7, "c3": 14}, {"c1": 24167, "c3": 48333}),
        ("capture", {"c1": 30, "c3": 60}, {"c1": 840000, "c3": 1680000}),
    ],
)
def test_local_expedition(kind, contributions, expected):
    """Given two origins contribute in a one-to-two ratio with sufficient local stocks.
    When a {kind} expedition is sealed.
    Then its fixed fee and per-person cost charge only those origins as {expected}.
    """
    state = engine.new_state(opponents="passive")
    for c in state["cities"].values():
        c["stock"] = 2400000
    order = engine.confirm_order(
        state, "p1", {"kind": kind, "target": "c4", "contributions": contributions}, "raid"
    )
    assert order["funding"] == expected
    assert sum(expected.values()) == order["cost"]


@case(
    "audit-legacy-economy", "Compatibility: absent economy marker retains saved funding and yield"
)
def test_legacy_economy():
    """Given a saved reign has no economy marker and first-level canals.
    When a local work is quoted and income accrues.
    Then its pooled funding and 200-Measure yield remain unchanged.
    """
    state = engine.new_state(economy_version=1, map_version=2)
    state.pop("economy_version")
    state["cities"]["c1"]["irrigation"] = 1
    order = engine.prepare_order(state, "p1", {"kind": "storage", "cities": ["c1"]}, "legacy")
    assert order["funding"] == {"c1": 166667, "c2": 166667, "c3": 166666}
    engine.advance_month(state, "audit")
    assert state["cities"]["c1"]["tax"] == 200000


@case("audit-local-cancellation", "Owner: cancelling a local decree releases only its reservations")
def test_local_cancellation():
    """Given a local storage decree reserves Qasr's funds.
    When the player withdraws it before closure.
    Then all its funds and teams are free with unchanged stocks and a cancellation date.
    """
    state = engine.new_state()
    engine.confirm_order(state, "p1", {"kind": "storage", "cities": ["c1"]}, "cancel")
    engine.cancel_order(state, "p1", "cancel")
    assert not any(engine.reservations(state)[0].values())
    assert not engine.busy_cities(state)
    assert state["cities"]["c1"]["stock"] == 600000
    assert state["orders"][0]["cancelled_month"] == 1


@case(
    "audit-frontier-conquest",
    "Owner: taking a frontier city opens deeper targets through owned roads",
)
def test_frontier_conquest():
    """Given Sefra has joined the player's starting domain.
    When the expanded frontier is consulted.
    Then Ishar and Daram become accessible without changing the saved roads.
    """
    state = engine.new_state()
    state["cities"]["c4"]["owner"] = "p1"
    roads = deepcopy(state["links"])
    assert {c for c in state["cities"] if engine.eligible_origins(state, "p1", c)} == {
        "c5",
        "c6",
        "c9",
    }
    assert engine.eligible_origins(state, "p1", "c5") == {"c1", "c2", "c3", "c4"}
    assert state["links"] == roads


@case(
    "audit-engagement-owner", "Owner: public engagement distinguishes own from rival reservations"
)
@pytest.mark.parametrize("actor,own", [("p1", True), ("p2", False)])
def test_engagement_owner(actor, own):
    """Given the first house reserves an expedition to Sefra.
    When {actor} reads its public engagement status.
    Then the commitment is marked as own {own} without exposing its order identifier.
    """
    state = engine.new_state()
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c3": 20}}, "hidden-order"
    )
    city = next(c for c in player_view(state, actor)["cities"] if c["id"] == "c4")
    assert city["engaged"] and city["own_engagement"] is own
    assert "hidden-order" not in str(city)


@case(
    "audit-raid-identity",
    "Owner: raid defenders learn the public house and survivor-dependent estimates",
)
def test_raid_identity():
    """Given the first house sends a raid of 45 people against Sefra.
    When combat resolves with surviving witnesses.
    Then its defender report names the house and leads with observations before losses.
    """
    state = engine.new_state(opponents="passive")
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c3": 45}}, "raid"
    )
    engine.advance_month(state, "audit")
    events, _ = engine.advance_month(state, "audit")
    body = next(e["body"] for e in events if e["recipient"] == "p2" and e["kind"] == "battle")
    assert "La maison d’Ambre" in body and "entre 40 et 59 hommes" in body
    assert body.index("entre 40 et 59") < body.index("coûté la vie")
