"""French presentation vocabulary; no simulation state or hidden information."""

from .messages import message
from .rules import CAPACITIES


def number(value):
    obj = message(f"{value:,}".replace(",", "\u202f"))
    obj.content = {"number": value}
    return obj


WORK_PHRASES = {
    "irrigation": [message("Aménager les premiers canaux"), message("Étendre le réseau de canaux")],
    "storage": [message("Agrandir le grenier"), message("Ériger des silos")],
    "walls": [message("Ériger une enceinte de terre crue"), message("Élever une grande enceinte")],
    "repair": [message("Réparer l’enceinte de terre crue"), message("Réparer la grande enceinte")],
}


def work_phrase(kind, level):
    return WORK_PHRASES[kind][level - 1]


def military_losses(count):
    if not count:
        return message("Aucun de nos Fidèles n’a perdu la vie dans cette expédition.")
    return message("Nous avons perdu {p0} Fidèles dans cette expédition.", p0=number(count))


def returned_loot(deposited, overflow):
    if not deposited and not overflow:
        return message("Ils ne rapportent pas de butin.")
    text = message("Le grenier reçoit {p0} Mesures de leur butin.", p0=number(deposited))
    if overflow:
        text += message(
            " Faute de place, {p0} autres n’ont pu être conservées.", p0=number(overflow)
        )
    return text


COMPLETED_WORK_PHRASES = {
    "irrigation": [
        message("ont aménagé les premiers canaux"),
        message("ont étendu le réseau de canaux"),
    ],
    "storage": [message("ont agrandi le grenier"), message("ont érigé des silos")],
    "walls": [
        message("ont érigé une enceinte de terre crue"),
        message("ont élevé une grande enceinte"),
    ],
    "repair": [
        message("ont réparé l’enceinte de terre crue"),
        message("ont réparé la grande enceinte"),
    ],
}


def completed_work_phrase(kind, level):
    return COMPLETED_WORK_PHRASES[kind][level - 1]


STARTED_ACTION_PHRASES = {
    "irrigation": message("Les travaux des canaux ont commencé."),
    "storage": message("Les travaux des greniers ont commencé."),
    "walls": message("Les travaux des fortifications ont commencé."),
    "repair": message("Les réparations de l’enceinte ont commencé."),
    "equipment": message("Les maîtres de la forge ont commencé leur ouvrage."),
    "raid": message("Nos hommes sont partis piller les villages."),
    "capture": message("Nos hommes sont partis conquérir la cité."),
}


def work_effect(kind, level):
    if kind == "irrigation":
        return message(
            "Chaque habitant présent produira {yield_per_moon} Mesures d’impôt par lune.",
            yield_per_moon=100 + 100 * level,
        )
    if kind == "storage":
        return message(
            "La capacité de ce grenier passera à {capacity} Mesures.",
            capacity=number(CAPACITIES[level]),
        )
    if kind == "walls":
        return message("La garnison locale sera mieux protégée contre les captures.")
    return message("L’enceinte retrouvera toute la protection de son niveau actuel.")
