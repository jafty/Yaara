"""French presentation vocabulary; no simulation state or hidden information."""

from .messages import Message
from .rules import CAPACITIES


def number(value):
    result = Message(f"{value:,}".replace(",", "\u202f"))
    result.tree = {"number": value}
    return result


WORK_PHRASES = {
    "irrigation": [Message("Aménager les premiers canaux"), Message("Étendre le réseau de canaux")],
    "storage": [Message("Agrandir le grenier"), Message("Ériger des silos")],
    "walls": [Message("Ériger une enceinte de terre crue"), Message("Élever une grande enceinte")],
    "repair": [Message("Réparer l’enceinte de terre crue"), Message("Réparer la grande enceinte")],
}


def work_phrase(kind, level):
    return WORK_PHRASES[kind][level - 1]


def work_effect(kind, level):
    if kind == "irrigation":
        return Message(
            "Chaque habitant présent produira {yield_per_moon} Mesures d’impôt par lune.",
            yield_per_moon=100 + 100 * level,
        )
    if kind == "storage":
        return Message(
            "La capacité de ce grenier passera à {capacity} Mesures.",
            capacity=number(CAPACITIES[level]),
        )
    if kind == "walls":
        return Message("La garnison locale sera mieux protégée contre les captures.")
    return Message("L’enceinte retrouvera toute la protection de son niveau actuel.")


def military_losses(count):
    if not count:
        return Message("Aucun de nos Fidèles n’a perdu la vie dans cette expédition.")
    return Message("Nous avons perdu {value0} Fidèles dans cette expédition.", value0=number(count))


def returned_loot(deposited, overflow):
    if not deposited and not overflow:
        return Message("Ils ne rapportent pas de butin.")
    text = Message("Le grenier reçoit {value0} Mesures de leur butin.", value0=number(deposited))
    if overflow:
        text += Message(
            " Faute de place, {value0} autres n’ont pu être conservées.", value0=number(overflow)
        )
    return text
