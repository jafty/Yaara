"""October 22 contracts: sustainable raids and one-Moon siege logistics."""

from fractions import Fraction

import pytest

from simulation import rules
from tests.cases import case

pytestmark = pytest.mark.logic


@case("strategy-expedition-prices", "October 22: new tariffs apply only to new economies")
@pytest.mark.parametrize(
    "version,raid,capture",
    [
        (1, (20000, 2500), (900000, 18000)),
        (3, (20000, 2500), (900000, 18000)),
        (4, (5000, 1000), (50000, 2000)),
    ],
)
def test_prices(version, raid, capture):
    """Given a saved economy version {version}.
    When expedition prices are requested.
    Then raid {raid} and capture {capture} preserve that economy's contract.
    """
    prices = rules.expedition_prices(version)
    assert tuple(prices["raid"].values()) == raid
    assert tuple(prices["capture"].values()) == capture


@case("strategy-raid-threshold", "Prompt D: strict victories, bounded casualties and retreat")
@pytest.mark.parametrize(
    "men,enemy,intercepted,outcome,dead,enemy_dead,loot,destroyed",
    [
        (50, 0, False, "unopposed", 0, 0, 150000, 50000),
        (100, 40, False, "success", 1, 2, 150000, 50000),
        (50, 40, False, "contested_win", 2, 2, 75000, 25000),
        (41, 40, False, "contested_win", 2, 2, 75000, 25000),
        (40, 40, False, "defeat", 2, 2, 0, 12500),
        (30, 40, False, "defeat", 2, 2, 0, 12500),
        (29, 40, False, "withdrawal", 1, 0, 0, 0),
        (29, 40, True, "rout", 6, 1, 0, 0),
        (1, 1, False, "defeat", 0, 0, 0, 2000),
    ],
)
def test_raid_thresholds(men, enemy, intercepted, outcome, dead, enemy_dead, loot, destroyed):
    """Given {men} raiders and {enemy} defenders with equal equipment and a 1200000 crop.
    When retreat interception is {intercepted} and the raid resolves.
    Then {outcome} loses {dead}/{enemy_dead} people and takes {loot} while destroying {destroyed}.
    """
    result = rules.strategic_raid_result(
        men, men * 100, enemy, enemy * 100, 1200000, 200000, intercepted
    )
    assert (
        result.outcome,
        result.attacker_losses,
        result.defender_losses,
        result.stolen,
        result.destroyed,
    ) == (outcome, dead, enemy_dead, loot, destroyed)


@case(
    "strategy-raid-protection", "Prompt E: protection is capped at ninety percent of accrued crops"
)
@pytest.mark.parametrize(
    "crop,shield,loot,destroyed",
    [
        (0, 800000, 0, 0),
        (100000, 800000, 1500, 500),
        (200000, 200000, 3000, 1000),
        (1200000, 800000, 60000, 20000),
    ],
)
def test_protection(crop, shield, loot, destroyed):
    """Given an unopposed raid against crop {crop} and nominal shelter {shield}.
    When protection and exposure are applied.
    Then at most ninety percent is protected and the raid takes {loot} and destroys {destroyed}.
    """
    result = rules.strategic_raid_result(100, 10000, 0, 0, crop, shield, False)
    assert (result.stolen, result.destroyed) == (loot, destroyed)


@case(
    "strategy-raid-carry-cap",
    "Prompt E: survival transport caps loot without converting leftovers to damage",
)
def test_carry_cap():
    """Given two unopposed survivors and a million exposed Measures before quartering.
    When their mixed equipment can carry only 100 Measures.
    Then they take 100 and destroy only their 4000-Measure capacity.
    """
    result = rules.strategic_raid_result(2, 200, 0, 0, 1200000, 200000, False, lambda dead: 100)
    assert (result.stolen, result.destroyed) == (100, 4000)


@case(
    "strategy-capture-threshold",
    "Owner delegation: one-Moon subsistence at 500 per resident and strict military thresholds",
)
@pytest.mark.parametrize(
    "attack,field,wall,stock,outcome,captured,ar,dr,food",
    [
        (1, 0, 0, 0, "unopposed", True, 0, 0, 0),
        (511, 140, 340, 0, "surrender", True, 1, 2, 0),
        (510, 140, 340, 0, "assault", True, 8, 12, 0),
        (341, 140, 340, 0, "assault", True, 8, 12, 0),
        (340, 140, 340, 500000, "held", False, 2, 1, 500000),
        (150, 140, 340, 600000, "held", False, 2, 1, 500000),
        (150, 140, 340, 499999, "shortage", True, 4, 8, 499999),
        (140, 140, 340, 0, "defeat", False, 12, 3, 0),
        (70, 140, 340, 0, "defeat", False, 12, 3, 0),
        (69, 140, 340, 0, "rout", False, 25, 2, 0),
    ],
)
def test_capture(attack, field, wall, stock, outcome, captured, ar, dr, food):
    """Given forces {attack}/{field}/{wall} and {stock} Measures for 1000 present residents.
    When a new-economy capture resolves its one-Moon operation.
    Then {outcome} has capture {captured}, rates {ar}/{dr}, food {food} and no civilian penalty.
    """
    result = rules.capture_result(
        rules.rule_family("V1"), attack, field, wall, stock, 1000, economy_version=4
    )
    assert (
        result.outcome,
        result.captured,
        result.attacker_rate,
        result.defender_rate,
        result.food_used,
        result.civilian_rate,
    ) == (outcome, captured, Fraction(ar, 100), Fraction(dr, 100), food, 0)


@case(
    "strategy-wall-integrity",
    "Prompt H and follow-up: walls 3/4/5.5/7, integrity and siege affect only the bonus",
)
@pytest.mark.parametrize(
    "level,integrity,reduction,expected",
    [
        (0, 100, 0, 3),
        (1, 100, 0, 4),
        (2, 100, 0, Fraction(11, 2)),
        (3, 100, 0, 7),
        (0, 100, Fraction(1, 4), Fraction(5, 2)),
        (3, 50, Fraction(1, 2), Fraction(5, 2)),
        (0, 0, 0, 1),
    ],
)
def test_wall_integrity(level, integrity, reduction, expected):
    """Given wall level {level}, integrity {integrity} and siege reduction {reduction}.
    When the new economy calculates defense before damage.
    Then the local multiplier is {expected} with an unchanged base defense.
    """
    assert rules.wall_multiplier(level, False, reduction, 4, integrity=integrity) == expected


@case("strategy-wall-damage", "Prompt H: held siege floor never repairs already weaker walls")
@pytest.mark.parametrize(
    "integrity,outcome,reduction,expected",
    [
        (100, "held", Fraction(1, 4), 95),
        (100, "held", Fraction(1, 2), 90),
        (73, "held", Fraction(1, 2), 70),
        (60, "held", Fraction(1, 2), 60),
        (100, "held", 0, 100),
        (100, "assault", 0, 50),
        (30, "assault", 0, 30),
        (80, "shortage", Fraction(1, 2), 80),
        (80, "defeat", Fraction(1, 2), 80),
    ],
)
def test_integrity_damage(integrity, outcome, reduction, expected):
    """Given integrity {integrity} and siege reduction {reduction}.
    When outcome {outcome} applies damage after the battle.
    Then integrity becomes {expected} without retroactive defense or accidental repair.
    """
    assert rules.integrity_after_combat(integrity, outcome, reduction) == expected


@case(
    "strategy-mixed-wall-damage",
    "Prompt H: fractional siege contributions retain exact wall damage in JSON saves",
)
def test_mixed_wall_damage():
    """Given intact level-three walls and an army with weighted siege reduction of three eighths.
    When one held siege damages the walls and the value is saved as JSON.
    Then integrity is exactly ninety-two and a half percent and defense remains exactly 131/20.
    """
    import json

    integrity = rules.integrity_after_combat(100, "held", Fraction(3, 8))
    saved = json.loads(json.dumps(integrity))
    assert saved == [185, 2]
    assert rules.wall_multiplier(3, False, 0, 4, integrity=saved) == Fraction(131, 20)
    assert rules.integrity_after_combat(saved, "held", Fraction(3, 8)) == 85
