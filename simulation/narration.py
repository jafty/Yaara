"""French presentation vocabulary; no simulation state or hidden information."""

from .messages import message
from .rules import CAPACITIES, EQUIPMENT_LABELS, tax_yield

WORK_NAMES = {
    "forge": [
        message("Atelier d’armes"),
        message("Forge de la cité"),
        message("Forge des maîtres"),
    ],
    "irrigation": [
        message("Cultures de l’oasis"),
        message("Premiers canaux"),
        message("Réseau de canaux"),
    ],
    "storage": [
        message("Grenier de la cité"),
        message("Grand grenier"),
        message("Silos de réserve"),
    ],
    "walls": [
        message("Cité ouverte"),
        message("Enceinte de terre crue"),
        message("Grande enceinte"),
    ],
}
WORK_NAMES["repair"] = WORK_NAMES["walls"]


def work_name(kind, level):
    return WORK_NAMES[kind][level]


def number(value):
    obj = message(f"{value:,}".replace(",", "\u202f"))
    obj.content = {"number": value}
    return obj


WORK_PHRASES = {
    "forge": [message("Aménager la forge de la cité"), message("Renforcer la forge de la cité")],
    "irrigation": [message("Aménager les premiers canaux"), message("Étendre le réseau de canaux")],
    "storage": [message("Agrandir le grenier"), message("Ériger des silos")],
    "walls": [message("Ériger une enceinte de terre crue"), message("Élever une grande enceinte")],
    "repair": [message("Réparer l’enceinte de terre crue"), message("Réparer la grande enceinte")],
}


WORK_PURPOSES = {
    "irrigation": message("Conduire l’eau aux cultures et accroître le prélèvement."),
    "storage": message("Préserver davantage de grain lorsque vient la récolte."),
    "walls": message("Abriter la garnison derrière une enceinte plus sûre."),
    "repair": message("Rendre à l’enceinte sa protection perdue."),
    "forge": message("Mieux armer les Fidèles de chaque cité."),
    "equipment": message("Mieux armer les Fidèles de toute votre maison."),
}

WORK_ADVICE = {
    "irrigation": message(
        "Le prélèvement s’accumule chaque lune et n’entre au grenier qu’à la récolte. Seuls les habitants présents y contribuent ; les hommes partis en expédition n’y ajoutent rien jusqu’à leur retour."
    ),
    "storage": message(
        "Agrandir le grenier ne crée pas de grain. La capacité reste propre à chaque cité ; un surplus de récolte ou de butin qui ne peut y tenir est perdu."
    ),
    "walls": message(
        "L’enceinte protège la garnison locale contre les captures, sans renforcer les secours. Elle ne protège pas contre le pillage des villages."
    ),
    "repair": message(
        "La réparation restaure l’enceinte existante sans l’agrandir. Une enceinte endommagée doit être réparée avant de pouvoir être renforcée."
    ),
    "forge": message(
        "Chaque cité conserve son propre armement, qui équipe aussi ses futurs habitants. La forge suit la cité si elle change de maître. Les expéditions déjà parties conservent leur équipement."
    ),
    "equipment": message(
        "Ce règne conserve un armement commun à toute la maison, y compris ses futurs habitants. Le devis dépend de sa population actuelle. Les expéditions déjà parties conservent leur équipement."
    ),
}


def work_benefit(kind, current, target, economy_version=1):
    if kind == "irrigation":
        return message(
            "Impôt par habitant présent : {before} → {after} Mesures par lune.",
            before=number(tax_yield(current, economy_version)),
            after=number(tax_yield(target, economy_version)),
        )
    if kind == "storage":
        return message(
            "Capacité du grenier : {before} → {after} Mesures.",
            before=number(CAPACITIES[current]),
            after=number(CAPACITIES[target]),
        )
    if kind == "forge":
        return message(
            "Armement : {before} → {after}.",
            before=EQUIPMENT_LABELS[current],
            after=EQUIPMENT_LABELS[target],
        )
    if kind == "repair":
        return message("L’enceinte retrouvera toute sa protection, sans être agrandie.")
    return work_effect(kind, target)


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
    "forge": [message("ont aménagé la forge"), message("ont renforcé la forge")],
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
    "forge": message("Les travaux des forges ont commencé."),
    "irrigation": message("Les travaux des canaux ont commencé."),
    "storage": message("Les travaux des greniers ont commencé."),
    "walls": message("Les travaux des fortifications ont commencé."),
    "repair": message("Les réparations de l’enceinte ont commencé."),
    "equipment": message("Les maîtres de la forge ont commencé leur ouvrage."),
    "raid": message("Nos hommes sont partis piller les villages."),
    "capture": message("Nos hommes sont partis conquérir la cité."),
}


def work_effect(kind, level, economy_version=1):
    if kind == "forge":
        return message(
            "La forge fournira un équipement renforcé aux Fidèles de cette cité, y compris aux nouveaux habitants. Les expéditions déjà parties conserveront leur équipement."
            if level == 1
            else "La forge fournira un équipement supérieur aux Fidèles de cette cité, y compris aux nouveaux habitants. Les expéditions déjà parties conserveront leur équipement."
        )
    if kind == "irrigation":
        return message(
            "Chaque habitant présent produira {yield_per_moon} Mesures d’impôt par lune.",
            yield_per_moon=tax_yield(level, economy_version),
        )
    if kind == "storage":
        return message(
            "La capacité de ce grenier passera à {capacity} Mesures.",
            capacity=number(CAPACITIES[level]),
        )
    if kind == "walls":
        return message("La garnison locale sera mieux protégée contre les captures.")
    return message("L’enceinte retrouvera toute la protection de son niveau actuel.")
