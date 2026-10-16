"""French presentation vocabulary; no simulation state or hidden information."""


def number(value):
    return f"{value:,}".replace(",", "\u202f")


WORK_PHRASES = {
    "irrigation": ["Aménager les premiers canaux", "Étendre le réseau de canaux"],
    "storage": ["Agrandir le grenier", "Ériger des silos"],
    "walls": ["Ériger une enceinte de terre crue", "Élever une grande enceinte"],
    "repair": ["Réparer l’enceinte de terre crue", "Réparer la grande enceinte"],
}


def work_phrase(kind, level):
    return WORK_PHRASES[kind][level - 1]


def military_losses(count):
    if not count:
        return "Aucun de nos Fidèles n’a perdu la vie dans cette expédition."
    return f"Nous avons perdu {number(count)} Fidèles dans cette expédition."


def returned_loot(deposited, overflow):
    if not deposited and not overflow:
        return "Ils ne rapportent pas de butin."
    text = f"Le grenier reçoit {number(deposited)} Mesures de leur butin."
    if overflow:
        text += f" Faute de place, {number(overflow)} autres n’ont pu être conservées."
    return text
