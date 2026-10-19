import pytest

from simulation import engine
from simulation.rules import RuleError
from tests.builders import rich_state
from tests.cases import case
from tests.stubs import FixedRandom

pytestmark = pytest.mark.logic


@pytest.fixture
def fixed_random(monkeypatch):
    monkeypatch.setattr(engine, "random_stream", FixedRandom())


@pytest.fixture
def raid(fixed_random):
    state = engine.new_state(
        "V0", opponents="passive", calendar_version=1, map_version=1, economy_version=1
    )
    state["cities"]["c4"]["stock"] = 1200000
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c3": 45}}, "raid"
    )
    return state


@case(
    "raid-timeline",
    "Design §26.2 Fiscality and §26.3: reservation, absence, death and return by origin",
)
@pytest.mark.parametrize(
    "month,present,away,population,tax,status",
    [
        pytest.param(0, 100, 0, 1000, 0, None, id="reserved-still-present"),
        pytest.param(1, 55, 45, 1000, 100000, "outbound", id="departure-after-tax"),
        pytest.param(2, 55, 44, 999, 195500, "returning", id="combat-one-death"),
        pytest.param(3, 99, 0, 999, 291000, "completed", id="return-after-tax"),
    ],
)
def test_raid_timeline(raid, month, present, away, population, tax, status):
    """Given a confirmed forty-five-person raid with a prescribed defense draw.
    When month {month} is reached.
    Then present {present}, absent {away}, population {population}, tax {tax} and mission status {status} reconcile.
    """
    for _ in range(month):
        engine.advance_month(raid, "stubbed")
    city = raid["cities"]["c3"]
    assert (city["fideles"], engine.absent(raid, "c3"), city["population"], city["tax"]) == (
        present,
        away,
        population,
        tax,
    )
    assert (raid["expeditions"][0]["status"] if month else None) == status


@case("raid-draw", "Design: the prescribed 20, 30 or 40 percent local raid defense drives losses")
@pytest.mark.parametrize(
    "percentage,remaining",
    [
        pytest.param(20, 99, id="twenty"),
        pytest.param(30, 99, id="thirty"),
        pytest.param(40, 98, id="forty"),
    ],
)
def test_prescribed_raid_defense(percentage, remaining, monkeypatch):
    """Given a raid and a prescribed local defense percentage of {percentage}.
    When combat resolves.
    Then the target retains {remaining} Faithful.
    """
    monkeypatch.setattr(engine, "random_stream", FixedRandom(percentage))
    state = engine.new_state(
        opponents="passive", calendar_version=1, map_version=1, economy_version=1
    )
    engine.confirm_order(
        state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c3": 45}}, "raid"
    )
    for _ in range(2):
        engine.advance_month(state, "stubbed")
    assert state["cities"]["c4"]["fideles"] == remaining


@case(
    "raid-protection",
    "Design §26.2: a completed raid releases exclusivity but protects the target for twelve months",
)
@pytest.mark.parametrize(
    "month,protected",
    [
        pytest.param(2, True, id="immediate"),
        pytest.param(13, True, id="last-protected"),
        pytest.param(14, False, id="expiration"),
    ],
)
def test_raid_protection(raid, month, protected):
    """Given a completed raid whose protection expires at month fourteen.
    When a new raid is requested in month {month}.
    Then the target engagement is released and protection is {protected}.
    """
    for _ in range(month):
        engine.advance_month(raid, "stubbed")
    assert engine.active_targets(raid) == {}
    assert raid["cities"]["c4"]["raid_protected_until"] == 14
    spec = {"kind": "raid", "target": "c4", "contributions": {"c3": 45}}
    if protected:
        with pytest.raises(RuleError, match="pillage"):
            engine.confirm_order(raid, "p1", spec, "retry")
    else:
        engine.confirm_order(raid, "p1", spec, "retry")
        assert engine.active_targets(raid) == {"c4": "retry"}


@case(
    "raid-stocks",
    "Design §26.3: reservations preserve stock; price/destruction remove it; loot transfers it",
)
@pytest.mark.parametrize(
    "month,total,loot",
    [
        pytest.param(0, 6000000, 0, id="reservation"),
        pytest.param(1, 5867500, 0, id="price-debited"),
        pytest.param(2, 5627500, 180000, id="loot-in-transit"),
        pytest.param(3, 5807500, 0, id="loot-returned"),
    ],
)
def test_raid_stock_accounting(raid, month, total, loot):
    """Given a raid against a city holding 1200000 Measures.
    When month {month} is reached.
    Then total city stock is {total} and loot in transit is {loot}.
    """
    for _ in range(month):
        engine.advance_month(raid, "stubbed")
    assert sum(city["stock"] for city in raid["cities"].values()) == total
    assert sum(mission["loot"] for mission in raid["expeditions"]) == loot


@case(
    "capture-transfer",
    "Design §26.2: capture transfers the existing local city without resetting its economy or works",
)
@pytest.mark.parametrize(
    "variation", ["local-survivors", "attacker-survivors", "tax", "walls-damaged", "work-continues"]
)
def test_capture_transfer(variation, fixed_random):
    """Given a fortified enemy city with an active granary project and a sufficient attacking army.
    When capture resolves for variation {variation}.
    Then ownership changes while the specified survivor, tax, damage or continuing-work consequence is preserved.
    """
    state = rich_state()
    state["cities"]["c4"]["walls"] = 1
    engine.confirm_order(state, "p2", {"kind": "storage", "cities": ["c4"]}, "store")
    engine.confirm_order(
        state,
        "p1",
        {"kind": "capture", "target": "c4", "contributions": {"c1": 80, "c2": 80, "c3": 60}},
        "attack",
    )
    for _ in range(5 if variation == "work-continues" else 2):
        engine.advance_month(state, "stubbed")
    city = state["cities"]["c4"]
    assert city["owner"] == "p1"
    if variation == "local-survivors":
        assert city["fideles"] == 88
    elif variation == "attacker-survivors":
        assert sum(state["expeditions"][0]["cohorts"].values()) == 202
    elif variation == "tax":
        assert city["tax"] == 200000
    elif variation == "walls-damaged":
        assert city["damaged"]
    else:
        assert city["storage"] == 1


@case(
    "wall-damage",
    "Design: an upgrade preserves intervening damage; repair restores the existing wall level",
)
@pytest.mark.parametrize(
    "repair",
    [
        pytest.param(False, id="upgrade-preserves-damage"),
        pytest.param(True, id="repair-preserves-level"),
    ],
)
def test_wall_damage(repair, fixed_random):
    """Given a wall upgrade damaged after its departure.
    When the upgrade completes and repair is {repair}.
    Then wall level remains two and damage is cleared only by a completed repair.
    """
    state = rich_state()
    state["cities"]["c1"].update(walls=1, storage=2, stock=6000000)
    engine.confirm_order(state, "p1", {"kind": "walls", "cities": ["c1"]}, "wall")
    engine.advance_month(state, "stubbed")
    state["cities"]["c1"]["damaged"] = True
    for _ in range(20):
        engine.advance_month(state, "stubbed")
    if repair:
        engine.confirm_order(state, "p1", {"kind": "repair", "cities": ["c1"]}, "repair")
        for _ in range(7):
            engine.advance_month(state, "stubbed")
    assert state["cities"]["c1"]["walls"] == 2
    assert state["cities"]["c1"]["damaged"] is not repair
