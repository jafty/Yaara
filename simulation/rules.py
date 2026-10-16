"""Pure arithmetic. No Django, I/O, wall clock, or implicit random draws."""

from dataclasses import dataclass
from fractions import Fraction

from .messages import message


class RuleError(ValueError):
    """An expected, player-facing rejection."""


def allocate(total: int, weights: dict[str, int], priority=None) -> dict[str, int]:
    """Hamilton allocation with an explicit, stable tie order."""
    if total < 0 or any(value < 0 for value in weights.values()):
        raise ValueError("Allocation must be nonnegative")
    denominator = sum(weights.values())
    result = dict.fromkeys(weights, 0)
    if denominator == 0 or total == 0:
        return result
    ranks = {key: index for index, key in enumerate(priority or sorted(weights))}
    remainders = {}
    for key, value in weights.items():
        result[key], remainders[key] = divmod(total * value, denominator)
    remaining = total - sum(result.values())
    for key in sorted(weights, key=lambda key: (-remainders[key], ranks.get(key, 0)))[:remaining]:
        result[key] += 1
    return result


def losses(count: int, rate: Fraction) -> int:
    value = count * rate
    rounded = (2 * value.numerator + value.denominator) // (2 * value.denominator)
    return min(count, max(0, rounded))


@dataclass(frozen=True)
class RuleFamily:
    version: str
    siege: bool
    cancellable: bool
    growth: Fraction
    max_level: int
    storage: bool
    equipment: bool


FAMILIES = {
    "V0": RuleFamily("V0", False, False, Fraction(0), 1, False, False),
    "V1": RuleFamily("V1", True, True, Fraction(5, 1000), 2, True, True),
}


def rule_family(version: str) -> RuleFamily:
    if version not in FAMILIES:
        raise RuleError(message("Cette version des règles n’est pas disponible."))
    return FAMILIES[version]


@dataclass(frozen=True)
class CaptureResult:
    outcome: str
    captured: bool
    attacker_rate: Fraction
    defender_rate: Fraction
    food_used: int = 0
    civilian_rate: Fraction = Fraction(0)


def capture_result(rules, attack, field, fortified, stock, present_population):
    if attack <= 0:
        raise ValueError("An attack requires positive strength")
    if fortified == 0:
        return CaptureResult("unopposed", True, Fraction(0), Fraction(0))
    if attack > fortified * Fraction(3, 2):
        return CaptureResult("surrender", True, Fraction(1, 100), Fraction(2, 100))
    if attack > fortified:
        return CaptureResult("assault", True, Fraction(8, 100), Fraction(12, 100))
    if rules.siege and attack > field:
        needed = present_population * 500
        if stock >= needed:
            return CaptureResult("held", False, Fraction(10, 100), Fraction(2, 100), needed)
        return CaptureResult(
            "shortage", True, Fraction(4, 100), Fraction(8, 100), stock, Fraction(2, 1000)
        )
    if attack < field * Fraction(1, 2):
        return CaptureResult("rout", False, Fraction(25, 100), Fraction(2, 100))
    return CaptureResult("defeat", False, Fraction(12, 100), Fraction(3, 100))


@dataclass(frozen=True)
class RaidResult:
    outcome: str
    attacker_losses: int
    defender_losses: int
    stolen: int
    destroyed: int


def raid_result(attackers, attack_equipment, defenders, defense_equipment, stock):
    attack = attackers * attack_equipment
    defense = defenders * defense_equipment
    accessible = stock // 4
    if attack > defense:
        attacker_dead = losses(attackers, Fraction(2, 100)) if defenders else 0
        defender_dead = losses(defenders, Fraction(4, 100))
        stolen = min(accessible * 60 // 100, (attackers - attacker_dead) * 5000)
        destroyed = min(accessible * 20 // 100, accessible - stolen)
        return RaidResult("success", attacker_dead, defender_dead, stolen, destroyed)
    if attack < defense * Fraction(1, 2):
        return RaidResult(
            "rout", losses(attackers, Fraction(20, 100)), losses(defenders, Fraction(1, 100)), 0, 0
        )
    return RaidResult(
        "defeat",
        losses(attackers, Fraction(8, 100)),
        losses(defenders, Fraction(2, 100)),
        0,
        accessible * 5 // 100,
    )


EQUIPMENT = [100, 120, 145]
EQUIPMENT_LABELS = [
    message("Équipement ordinaire"),
    message("Équipement renforcé"),
    message("Équipement supérieur"),
]
WALLS = [Fraction(1), Fraction(8, 5), Fraction(3)]
CAPACITIES = [2_400_000, 3_600_000, 6_000_000]
WORK_PRICES = {
    "irrigation": [(2_400_000, 6), (4_800_000, 12)],
    "storage": [(500_000, 4), (1_200_000, 8)],
    "walls": [(1_200_000, 8), (9_600_000, 20)],
    "repair": [(240_000, 3), (1_920_000, 6)],
}
ACTION_LABELS = {
    "irrigation": message("Aménager les canaux"),
    "storage": message("Agrandir le stockage"),
    "walls": message("Renforcer les fortifications"),
    "repair": message("Réparer l’enceinte"),
    "equipment": message("Organiser l’armement"),
    "raid": message("Piller les villages"),
    "capture": message("Capturer une cité"),
}
OUTCOME_LABELS = {
    "unopposed": message("Prise sans défense"),
    "surrender": message("Reddition rapide"),
    "assault": message("Assaut victorieux"),
    "held": message("La cité tient le siège"),
    "shortage": message("Capitulation par pénurie"),
    "rout": message("Défaite sévère"),
    "defeat": message("Attaque repoussée"),
    "success": message("Pillage réussi"),
}
