from fractions import Fraction

import pytest

from simulation.rules import allocate, capture_result, losses, raid_result, rule_family
from tests.cases import case

pytestmark = pytest.mark.logic


@case("allocation", "Design §26.3: Hamilton allocation conserves totals and respects priority")
@pytest.mark.parametrize(
    "total,weights,priority,expected",
    [
        pytest.param(20, {"a": 2, "b": 1}, ["a", "b"], {"a": 13, "b": 7}, id="remainders"),
        pytest.param(1, {"a": 1, "b": 1}, ["b", "a"], {"a": 0, "b": 1}, id="priority-tie"),
        pytest.param(
            200000,
            {"a": 600000, "b": 300000, "c": 100000},
            None,
            {"a": 120000, "b": 60000, "c": 20000},
            id="funding-example",
        ),
        pytest.param(0, {"a": 2}, None, {"a": 0}, id="zero-total"),
        pytest.param(10, {"a": 0}, None, {"a": 0}, id="zero-weights"),
        pytest.param(10, {}, None, {}, id="empty-weights"),
    ],
)
def test_allocation(total, weights, priority, expected):
    """Given a total of {total}, weights {weights} and priority {priority}.
    When the total is apportioned by largest remainder.
    Then the allocation is {expected}, including tie and empty-input boundaries.
    """
    assert allocate(total, weights, priority) == expected


@case("allocation-rejection", "Design §26.3: allocation inputs cannot be negative")
@pytest.mark.parametrize(
    "total,weights",
    [
        pytest.param(-1, {"a": 1}, id="negative-total"),
        pytest.param(1, {"a": -1}, id="negative-weight"),
    ],
)
def test_negative_allocation(total, weights):
    """Given allocation inputs {total} and {weights} containing a negative value.
    When allocation is requested.
    Then the invalid input is rejected.
    """
    with pytest.raises(ValueError):
        allocate(total, weights)


@case("casualties", "Design §26.2: casualties use half-up rounding, bounded by cohort size")
@pytest.mark.parametrize(
    "count,rate,expected",
    [
        pytest.param(25, Fraction(2, 100), 1, id="half-up"),
        pytest.param(220, Fraction(8, 100), 18, id="assault-attacker"),
        pytest.param(140, Fraction(12, 100), 17, id="assault-defender"),
        pytest.param(24, Fraction(2, 100), 0, id="below-half"),
        pytest.param(0, Fraction(1), 0, id="empty-cohort"),
        pytest.param(10, Fraction(2), 10, id="upper-bound"),
    ],
)
def test_casualties(count, rate, expected):
    """Given a cohort of {count} and casualty rate {rate}.
    When casualties are calculated.
    Then half-up rounding and cohort bounds give {expected} deaths.
    """
    assert losses(count, rate) == expected


@case("capture-v0", "Design §26.2: strict campaign, half-campaign, wall and 1.5-wall boundaries")
@pytest.mark.parametrize(
    "strength,outcome",
    [
        pytest.param(6999, "rout", id="below-half-field"),
        pytest.param(7000, "defeat", id="half-field-equality"),
        pytest.param(14000, "defeat", id="field-equality"),
        pytest.param(20000, "defeat", id="wall-equality"),
        pytest.param(20001, "assault", id="above-wall"),
        pytest.param(30000, "assault", id="surrender-equality"),
        pytest.param(30001, "surrender", id="above-surrender"),
    ],
)
def test_v0_capture_strict_boundaries(strength, outcome):
    """Given V0 defenders with field strength 14000 and fortified strength 20000.
    When an army with strength {strength} attacks.
    Then the strict comparison gives outcome {outcome}.
    """
    assert (
        capture_result(rule_family("V0"), strength, 14000, 20000, 1200000, 1000).outcome == outcome
    )


@case("capture-invalid", "A capture requires a positive attacking force")
@pytest.mark.parametrize("strength", [pytest.param(0, id="zero"), pytest.param(-1, id="negative")])
def test_capture_requires_attackers(strength):
    """Given an attacking strength of {strength}.
    When capture is calculated.
    Then a nonpositive army is rejected.
    """
    with pytest.raises(ValueError):
        capture_result(rule_family("V0"), strength, 14000, 20000, 1200000, 1000)


@case("capture-v1", "Design §26.2: siege uses only local food; equality holds the siege")
@pytest.mark.parametrize(
    "attack,field,wall,stock,expected",
    [
        pytest.param(20000, 14000, 34000, 500000, ("held", 500000, False), id="food-equality"),
        pytest.param(20000, 14000, 34000, 499999, ("shortage", 499999, True), id="food-shortage"),
        pytest.param(14000, 14000, 34000, 0, ("defeat", 0, False), id="field-equality"),
        pytest.param(80, 0, 0, 0, ("unopposed", 0, True), id="undefended"),
    ],
)
def test_siege(attack, field, wall, stock, expected):
    """Given V1 field strength {field}, wall strength {wall} and local food {stock}.
    When strength {attack} attacks.
    Then outcome, food consumed and ownership change are {expected}.
    """
    result = capture_result(rule_family("V1"), attack, field, wall, stock, 1000)
    assert (result.outcome, result.food_used, result.captured) == expected


@case("raid", "Design raid examples and §26.2: strict victory, casualties and local loot")
@pytest.mark.parametrize(
    "attackers,defenders,stock,expected",
    [
        pytest.param(45, 40, 1200000, ("success", 1, 2, 180000, 60000), id="documented-example"),
        pytest.param(45, 40, 300000, ("success", 1, 2, 45000, 15000), id="poor-target"),
        pytest.param(30, 30, 1200000, ("defeat", 2, 1, 0, 15000), id="equal-strength"),
        pytest.param(20, 0, 600000, ("success", 0, 0, 90000, 30000), id="undefended"),
        pytest.param(20, 41, 1200000, ("rout", 4, 0, 0, 0), id="below-half"),
        pytest.param(20, 40, 1200000, ("defeat", 2, 1, 0, 15000), id="half-equality"),
        pytest.param(45, 40, 0, ("success", 1, 2, 0, 0), id="empty-stock"),
        pytest.param(20, 0, 2400000, ("success", 0, 0, 100000, 120000), id="carrying-limit"),
    ],
)
def test_raid(attackers, defenders, stock, expected):
    """Given {attackers} attackers, {defenders} defenders and {stock} local Measures.
    When equally equipped forces resolve a raid.
    Then outcome, losses, stolen and destroyed food are {expected}.
    """
    result = raid_result(attackers, 100, defenders, 100, stock)
    assert (
        result.outcome,
        result.attacker_losses,
        result.defender_losses,
        result.stolen,
        result.destroyed,
    ) == expected


@case("raid-margin", "Design raid example: 180000 stolen less 132500 expedition price = 47500")
def test_documented_raid_margin():
    """Given the dossier raid of 45 attackers against 40 defenders and 1200000 Measures.
    When loot is reduced by the expedition cost.
    Then the net gain is 47500 Measures.
    """
    result = raid_result(45, 100, 40, 100, 1200000)
    assert result.stolen - 132500 == 47500
