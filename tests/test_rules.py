from fractions import Fraction

import pytest

from simulation.rules import allocate, capture_result, losses, raid_result, rule_family


def test_largest_remainders_preserve_total_and_tie_priority():
    assert allocate(20, {"a": 2, "b": 1}, ["a", "b"]) == {"a": 13, "b": 7}
    assert allocate(1, {"a": 1, "b": 1}, ["b", "a"]) == {"a": 0, "b": 1}
    assert allocate(200_000, {"a": 600_000, "b": 300_000, "c": 100_000}) == {
        "a": 120_000,
        "b": 60_000,
        "c": 20_000,
    }


def test_half_up_casualties():
    assert losses(25, Fraction(2, 100)) == 1
    assert losses(220, Fraction(8, 100)) == 18
    assert losses(140, Fraction(12, 100)) == 17


@pytest.mark.parametrize(
    "strength,outcome",
    [
        (0, "invalid"),
        (6999, "rout"),
        (7000, "defeat"),
        (14000, "defeat"),
        (20000, "defeat"),
        (20001, "assault"),
        (30000, "assault"),
        (30001, "surrender"),
    ],
)
def test_v0_capture_strict_boundaries(strength, outcome):
    if outcome == "invalid":
        with pytest.raises(ValueError):
            capture_result(rule_family("V0"), strength, 14000, 20000, 1_200_000, 1000)
    else:
        assert (
            capture_result(rule_family("V0"), strength, 14000, 20000, 1_200_000, 1000).outcome
            == outcome
        )


def test_siege_equality_and_local_consumption():
    rules = rule_family("V1")
    result = capture_result(rules, 20000, 14000, 34000, 500000, 1000)
    assert (result.outcome, result.food_used, result.captured) == ("held", 500000, False)
    result = capture_result(rules, 20000, 14000, 34000, 499999, 1000)
    assert (result.outcome, result.food_used, result.captured) == ("shortage", 499999, True)
    assert capture_result(rules, 14000, 14000, 34000, 0, 1000).outcome == "defeat"
    assert capture_result(rules, 80, 0, 0, 0, 1000).outcome == "unopposed"


def test_documented_raid_and_poor_target():
    result = raid_result(45, 100, 40, 100, 1_200_000)
    assert (result.attacker_losses, result.stolen, result.destroyed) == (1, 180000, 60000)
    assert result.stolen - (20000 + 2500 * 45) == 47500
    assert raid_result(45, 100, 40, 100, 300000).stolen == 45000
    assert raid_result(30, 100, 30, 100, 1_200_000).outcome == "defeat"
    assert raid_result(20, 100, 0, 100, 600000).attacker_losses == 0
