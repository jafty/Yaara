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


def capture_result(rules, attack, field, fortified, stock, present_population, economy_version=1):
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
            if economy_version >= 4:
                return CaptureResult("held", False, Fraction(2, 100), Fraction(1, 100), needed)
            return CaptureResult("held", False, Fraction(10, 100), Fraction(2, 100), needed)
        return CaptureResult(
            "shortage",
            True,
            Fraction(4, 100),
            Fraction(8, 100),
            stock,
            Fraction(0) if economy_version >= 4 else Fraction(2, 1000),
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


def raid_result(attackers, attack_equipment, defenders, defense_equipment, stock, carrying=None):
    attack = attackers * attack_equipment
    defense = defenders * defense_equipment
    accessible = stock // 4
    if attack > defense:
        attacker_dead = losses(attackers, Fraction(2, 100)) if defenders else 0
        defender_dead = losses(defenders, Fraction(4, 100))
        stolen = min(
            accessible * 60 // 100,
            (attackers - attacker_dead) * 5000 if carrying is None else carrying(attacker_dead),
        )
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
EXPEDITION_PRICES = {
    "raid": {"base": 20_000, "per_person": 2500},
    "capture": {"base": 900_000, "per_person": 18_000},
}
STRATEGIC_EXPEDITION_PRICES = {
    "raid": {"base": 5_000, "per_person": 1_000},
    "capture": {"base": 50_000, "per_person": 2_000},
}


def expedition_prices(economy_version=1):
    return STRATEGIC_EXPEDITION_PRICES if economy_version >= 4 else EXPEDITION_PRICES


def strategic_raid_result(
    attackers, attack, defenders, defense, crop, protection, intercepted, carrying=None
):
    """One force comparison controls both the outcome and its casualty band."""
    engaged = min(attackers, defenders)
    exposed = (crop * 10 - min(protection * 10, crop * 9)) // 40
    if defenders == 0:
        outcome, attacker_dead, defender_dead, loot_rate, destruction_rate = (
            "unopposed",
            0,
            0,
            60,
            20,
        )
    elif attack > defense * Fraction(5, 4):
        outcome, attacker_dead, defender_dead, loot_rate, destruction_rate = (
            "success",
            losses(engaged, Fraction(2, 100)),
            losses(engaged, Fraction(4, 100)),
            60,
            20,
        )
    elif attack >= defense * Fraction(3, 4):
        won = attack > defense
        outcome, attacker_dead, defender_dead, loot_rate, destruction_rate = (
            "contested_win" if won else "defeat",
            losses(engaged, Fraction(6, 100)),
            losses(engaged, Fraction(6, 100)),
            30 if won else 0,
            10 if won else 5,
        )
    elif intercepted:
        outcome, attacker_dead, defender_dead, loot_rate, destruction_rate = (
            "rout",
            losses(attackers, Fraction(20, 100)),
            losses(engaged, Fraction(2, 100)),
            0,
            0,
        )
    else:
        outcome, attacker_dead, defender_dead, loot_rate, destruction_rate = (
            "withdrawal",
            losses(engaged, Fraction(2, 100)),
            losses(engaged, Fraction(1, 100)),
            0,
            0,
        )
    survivors = attackers - attacker_dead
    carry = survivors * 5000 if carrying is None else carrying(attacker_dead)
    stolen = min(exposed * loot_rate // 100, carry)
    destroyed = min(exposed * destruction_rate // 100, survivors * 2000, exposed - stolen)
    return RaidResult(outcome, attacker_dead, defender_dead, stolen, destroyed)


def integrity_after_combat(integrity, outcome, reduction):
    value = integrity_fraction(integrity)
    if outcome == "assault":
        value = min(value, Fraction(50))
    elif outcome == "held":
        value = min(value, max(Fraction(70), value - 20 * reduction))
    return int(value) if value.denominator == 1 else [value.numerator, value.denominator]


def integrity_fraction(value):
    return Fraction(*value) if isinstance(value, list) else Fraction(value)


EQUIPMENT_LABELS = [
    message("Équipement ordinaire"),
    message("Équipement renforcé"),
    message("Équipement supérieur"),
]
WALLS = [Fraction(1), Fraction(8, 5), Fraction(3)]
CAPACITIES = [2_400_000, 3_600_000, 6_000_000]


def tax_yield(level, economy_version=1):
    return (
        [100, 115, 130, 200]
        if economy_version >= 3
        else [100, 130, 200]
        if economy_version == 2
        else [100, 200, 300]
    )[level]


WORK_PRICES = {
    "forge": [(600_000, 8), (1_400_000, 14)],
    "irrigation": [(2_400_000, 6), (4_800_000, 12)],
    "storage": [(500_000, 4), (1_200_000, 8)],
    "walls": [(1_200_000, 8), (9_600_000, 20)],
    "repair": [(240_000, 3), (1_920_000, 6)],
}
ACTION_LABELS = {
    "forge": message("Améliorer la forge"),
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
    "contested_win": message("Pillage remporté de haute lutte"),
    "withdrawal": message("Raid interrompu"),
}


# Saved economies select their own catalogue; absent markers retain historical rules.
CURRENT_WORK_PRICES = {
    "irrigation": [(300_000, 3), (400_000, 5), (1_500_000, 10)],
    "storage": [(200_000, 3), (420_000, 5), (900_000, 8)],
    "forge": [(150_000, 3), (450_000, 5), (1_000_000, 8)],
    "walls": [(200_000, 5), (900_000, 10), (2_400_000, 20)],
    "watch": [(120_000, 3), (360_000, 5)],
    "shelter": [(150_000, 3), (450_000, 5)],
    "transport": [(200_000, 4), (600_000, 6)],
    "siege": [(300_000, 5), (750_000, 8)],
    "repair": [(40_000, 3), (180_000, 6), (480_000, 8)],
}
CURRENT_EQUIPMENT = [100, 110, 125, 145]
CURRENT_CAPACITIES = [2_400_000, 3_600_000, 5_400_000, 8_100_000]
CURRENT_WALLS = [Fraction(1), Fraction(2), Fraction(4), Fraction(7)]
CURRENT_EQUIPMENT_LABELS = [
    message("Équipement ordinaire"),
    message("Équipement du petit arsenal"),
    message("Équipement des ateliers d’armement"),
    message("Équipement du grand arsenal"),
]
ACTION_LABELS.update(
    {
        "watch": message("Organiser la surveillance"),
        "shelter": message("Protéger les récoltes"),
        "transport": message("Développer le transport"),
        "siege": message("Préparer le matériel de siège"),
    }
)
ACTION_LABELS.update(
    {
        "repair_watch": message("Réparer la surveillance"),
        "repair_shelter": message("Réparer les réserves protégées"),
        "convoy": message("Acheminer des ressources"),
    }
)
STRATEGIC_WORK_PRICES = {
    **CURRENT_WORK_PRICES,
    "repair_watch": [(24_000, 2), (72_000, 2)],
    "repair_shelter": [(30_000, 2), (90_000, 2)],
}


def work_prices(economy_version=1):
    return (
        STRATEGIC_WORK_PRICES
        if economy_version >= 4
        else CURRENT_WORK_PRICES
        if economy_version >= 3
        else WORK_PRICES
    )


def effective_level(city, family):
    return max(0, city[family] - int(family in city.get("damaged_works", [])))


def equipment_values(economy_version=1):
    return CURRENT_EQUIPMENT if economy_version >= 3 else EQUIPMENT


def equipment_labels(economy_version=1):
    return CURRENT_EQUIPMENT_LABELS if economy_version >= 3 else EQUIPMENT_LABELS


def capacities(economy_version=1):
    return CURRENT_CAPACITIES if economy_version >= 3 else CAPACITIES


def wall_multiplier(
    level, damaged=False, reduction=Fraction(0), economy_version=1, *, integrity=100
):
    values = (
        [Fraction(3), Fraction(4), Fraction(11, 2), Fraction(7)]
        if economy_version >= 4
        else CURRENT_WALLS
        if economy_version >= 3
        else WALLS
    )
    bonus = values[level] - 1
    if economy_version >= 4:
        bonus *= integrity_fraction(integrity) / 100
    elif damaged:
        bonus /= 2
    return 1 + bonus * (1 - max(Fraction(0), min(Fraction(1), reduction)))
