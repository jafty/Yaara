"""The simulation aggregate. Functions mutate only the supplied in-memory state.

The application persists a successful command atomically under its game lock.
No function here imports Django, reads a clock, or accesses storage.
"""

import hashlib
import random
from copy import deepcopy

from .narration import military_losses, number, returned_loot, work_phrase
from .rules import (
    ACTION_LABELS,
    CAPACITIES,
    EQUIPMENT,
    EQUIPMENT_LABELS,
    OUTCOME_LABELS,
    WALLS,
    WORK_PRICES,
    RuleError,
    allocate,
    capture_result,
    losses,
    raid_result,
    rule_family,
)

CITY_NAMES = ["Qasr", "Tamesh", "Namar", "Sefra", "Ishar", "Daram", "Azal", "Mirha", "Tazir"]
REALM_NAMES = ["La maison d’Ambre", "Les seigneurs de Sefra", "La ligue d’Azal"]


def new_state(version="V1", reign_months=120, opponents="active", player_name="La maison d’Ambre"):
    rule_family(version)
    if reign_months not in (24, 60, 120, 240) or opponents not in ("active", "passive"):
        raise RuleError("La configuration de cette partie est invalide.")
    cities = {}
    for index, name in enumerate(CITY_NAMES):
        city_id = f"c{index + 1}"
        cities[city_id] = {
            "id": city_id,
            "name": name,
            "owner": f"p{index // 3 + 1}",
            "population": 1000,
            "fideles": 100,
            "stock": 600_000,
            "tax": 0,
            "irrigation": 0,
            "storage": 0,
            "walls": 0,
            "damaged": False,
            "raid_protected_until": 0,
            "military_deaths": 0,
            "civilian_deaths": 0,
        }
    return {
        "schema": 1,
        "rules": version,
        "month": 0,
        "status": "active",
        "config": {"reign_months": reign_months, "raid_minimum": 20, "capture_minimum": 80},
        "players": {
            f"p{index + 1}": {
                "id": f"p{index + 1}",
                "name": player_name if index == 0 else name,
                "equipment": 0,
                "eliminated": False,
                "bot": index > 0 and opponents == "active",
            }
            for index, name in enumerate(REALM_NAMES)
        },
        "cities": cities,
        "links": [[f"c{index + 1}", f"c{(index + 1) % 9 + 1}"] for index in range(9)],
        "orders": [],
        "works": [],
        "expeditions": [],
        "result": None,
    }


def owned_cities(state, actor):
    return [city for city in state["cities"].values() if city["owner"] == actor]


def capacity(city):
    return CAPACITIES[city["storage"]]


def absent(state, city_id):
    return sum(
        mission["cohorts"].get(city_id, 0)
        for mission in state["expeditions"]
        if mission["status"] != "completed"
    )


def reservations(state):
    funds = dict.fromkeys(state["cities"], 0)
    people = dict.fromkeys(state["cities"], 0)
    for order in state["orders"]:
        if order["status"] == "confirmed":
            for city_id, value in order["funding"].items():
                funds[city_id] += value
            for city_id, value in order.get("contributions", {}).items():
                people[city_id] += value
    return funds, people


def active_targets(state):
    return {
        order["target"]: order["id"]
        for order in state["orders"]
        if order["kind"] in ("raid", "capture") and order["status"] in ("confirmed", "active")
    }


def connected_component(state, city_id):
    owner = state["cities"][city_id]["owner"]
    reached = {city_id}
    todo = [city_id]
    while todo:
        current = todo.pop()
        for first, second in state["links"]:
            neighbor = second if first == current else first if second == current else None
            if neighbor and neighbor not in reached and state["cities"][neighbor]["owner"] == owner:
                reached.add(neighbor)
                todo.append(neighbor)
    return reached


def eligible_origins(state, actor, target):
    if target not in state["cities"] or state["cities"][target]["owner"] == actor:
        return set()
    eligible = set()
    for first, second in state["links"]:
        neighbor = second if first == target else first if second == target else None
        if neighbor and state["cities"][neighbor]["owner"] == actor:
            eligible.update(connected_component(state, neighbor))
    return eligible


def busy_cities(state):
    busy = {
        work["city"] for work in state["works"] if work["status"] == "active" and work.get("city")
    }
    for order in state["orders"]:
        if order["status"] == "confirmed":
            busy.update(task["city"] for task in order.get("tasks", []))
    return busy


def equipment_busy(state, actor):
    return any(
        work["kind"] == "equipment" and work["actor"] == actor and work["status"] == "active"
        for work in state["works"]
    ) or any(
        order["kind"] == "equipment" and order["actor"] == actor and order["status"] == "confirmed"
        for order in state["orders"]
    )


def ensure_actor(state, actor):
    if state["status"] != "active":
        raise RuleError("Le règne est terminé. Son résultat est désormais scellé.")
    if actor not in state["players"] or state["players"][actor]["eliminated"]:
        raise RuleError("Ce Prétendant ne peut plus donner d’ordres.")


def work_spec(state, city, kind):
    rules = rule_family(state["rules"])
    if kind not in WORK_PRICES:
        raise RuleError("Ce chantier n’existe pas.")
    if kind in ("storage", "repair") and not rules.storage:
        raise RuleError("Cette action appartient aux règles V1.")
    if kind == "repair":
        if not city["walls"] or not city["damaged"]:
            raise RuleError("Cette enceinte ne nécessite aucune réparation.")
        level = city["walls"]
    else:
        level = city[kind] + 1
        if level > rules.max_level:
            raise RuleError("Le niveau maximal de cet ouvrage est déjà atteint.")
        if kind == "walls" and city["damaged"]:
            raise RuleError("Il faut réparer l’enceinte avant de la renforcer.")
    cost, duration = WORK_PRICES[kind][level - 1]
    return {"city": city["id"], "kind": kind, "level": level, "cost": cost, "duration": duration}


def normalized_contributions(entries):
    if not isinstance(entries, dict) and not isinstance(entries, list):
        raise RuleError("Les contributions militaires sont invalides.")
    pairs = entries.items() if isinstance(entries, dict) else entries
    contributions = {}
    try:
        for city_id, count in pairs:
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError
            if count:
                contributions[city_id] = contributions.get(city_id, 0) + count
    except (ValueError, TypeError):
        raise RuleError("Les effectifs doivent être des nombres entiers positifs.") from None
    return contributions


def prepare_order(state, actor, spec, order_id):
    ensure_actor(state, actor)
    rules = rule_family(state["rules"])
    funds, people = reservations(state)
    available = {
        city["id"]: city["stock"] - funds[city["id"]] for city in owned_cities(state, actor)
    }
    kind = spec.get("kind")
    order = {
        "id": order_id,
        "actor": actor,
        "kind": kind,
        "status": "confirmed",
        "execute_month": state["month"] + 1,
        "funding": {},
        "cost": 0,
        "tasks": [],
    }
    if kind in WORK_PRICES:
        targets = spec.get("cities", [])
        if not isinstance(targets, list) or not targets or len(targets) != len(set(targets)):
            raise RuleError("Choisissez au moins une cité, une seule fois chacune.")
        for city_id in sorted(targets):
            city = state["cities"].get(city_id)
            if not city or city["owner"] != actor:
                raise RuleError("Cette cité ne relève pas de votre autorité.")
            if city_id in busy_cities(state):
                raise RuleError("Les équipes de cette cité sont déjà engagées.")
            order["tasks"].append(work_spec(state, city, kind))
        order["cost"] = sum(task["cost"] for task in order["tasks"])
    elif kind == "equipment":
        if not rules.equipment:
            raise RuleError("Les projets d’armement appartiennent aux règles V1.")
        player = state["players"][actor]
        if player["equipment"] >= 2 or equipment_busy(state, actor):
            raise RuleError("Votre forge est déjà engagée ou son organisation est achevée.")
        level = player["equipment"] + 1
        population = sum(city["population"] for city in owned_cities(state, actor))
        order.update(
            {
                "level": level,
                "duration": 8 if level == 1 else 14,
                "cost": max(1_800_000, 600 * population)
                if level == 1
                else max(4_200_000, 1400 * population),
            }
        )
    elif kind in ("raid", "capture"):
        target = spec.get("target")
        if target not in state["cities"] or state["cities"][target]["owner"] == actor:
            raise RuleError("Choisissez une cité ennemie de cette partie.")
        if target in active_targets(state):
            raise RuleError(
                "Une autre expédition est déjà engagée vers cette cité. Aucun moyen n’a été réservé."
            )
        if kind == "raid" and state["month"] < state["cities"][target]["raid_protected_until"]:
            raise RuleError("Les villages ne constituent pas une cible de pillage disponible.")
        contributions = normalized_contributions(spec.get("contributions", {}))
        eligible = eligible_origins(state, actor, target)
        for city_id, count in contributions.items():
            if city_id not in eligible:
                raise RuleError(
                    "Cette communauté ne peut rejoindre cette frontière par nos possessions."
                )
            if count > state["cities"][city_id]["fideles"] - people[city_id]:
                raise RuleError("Certains de ces hommes sont déjà promis à une autre expédition.")
        total = sum(contributions.values())
        minimum = state["config"][f"{kind}_minimum"]
        if total < minimum:
            raise RuleError(f"Cette expédition demande au moins {minimum} Fidèles au total.")
        order.update(
            {
                "target": target,
                "contributions": contributions,
                "cost": 20_000 + 2500 * total if kind == "raid" else 900_000 + 18000 * total,
            }
        )
    else:
        raise RuleError("Cet ordre n’est pas reconnu.")
    if sum(available.values()) < order["cost"]:
        raise RuleError("Cette dépense dépasserait les moyens non engagés.")
    # Batch work keeps its individual financing plans in deterministic city order.
    if order["tasks"]:
        for task in order["tasks"]:
            task["funding"] = allocate(task["cost"], available)
            for city_id, amount in task["funding"].items():
                available[city_id] -= amount
                order["funding"][city_id] = order["funding"].get(city_id, 0) + amount
    else:
        order["funding"] = allocate(order["cost"], available)
    return order


def confirm_order(state, actor, spec, order_id):
    existing = next((order for order in state["orders"] if order["id"] == order_id), None)
    if existing:
        if existing["actor"] != actor:
            raise RuleError("Cet identifiant de confirmation est déjà utilisé.")
        return existing
    order = prepare_order(state, actor, spec, order_id)
    state["orders"].append(order)
    return order


def cancel_order(state, actor, order_id):
    ensure_actor(state, actor)
    if not rule_family(state["rules"]).cancellable:
        raise RuleError("En V0, une confirmation est définitive.")
    order = next(
        (item for item in state["orders"] if item["id"] == order_id and item["actor"] == actor),
        None,
    )
    if not order or order["status"] != "confirmed":
        raise RuleError("Cet ordre ne peut plus être annulé.")
    order["status"] = "cancelled"
    return order


def random_stream(seed, month, purpose):
    digest = hashlib.sha256(f"{seed}:{month}:{purpose}".encode()).digest()
    return random.Random(int.from_bytes(digest, "big"))


def report(events, recipient, kind, title, body):
    events.append({"recipient": recipient, "kind": kind, "title": title, "body": body})


def annual_economy(state, events):
    rules = rule_family(state["rules"])
    for city in state["cities"].values():
        city["tax"] += (city["population"] - absent(state, city["id"])) * (
            100 + city["irrigation"] * 100
        )
        if state["month"] % 12:
            continue
        added = min(city["tax"], capacity(city) - city["stock"])
        overflow = city["tax"] - added
        city["stock"] += added
        city["tax"] = 0
        growth = int(city["population"] * rules.growth)
        city["population"] += growth
        existing = city["fideles"] + absent(state, city["id"])
        renewed = max(0, min(city["population"] // 10 - existing, city["population"] // 100))
        city["fideles"] += renewed
        report(
            events,
            city["owner"],
            "harvest",
            f"La récolte de {city['name']}",
            f"Les comptes de {city['name']} sont arrêtés pour cette année. Le prélèvement a fait entrer {number(added)} Mesures dans son grenier ; {number(overflow)} autres n’ont pu y trouver place. "
            f"J’ai inscrit {growth} nouveaux habitants et {renewed} habitants rejoignant les Fidèles. "
            f"La cité compte à présent {number(city['population'])} habitants. Depuis le début du règne, {city['military_deaths'] + city['civilian_deaths']} de ses habitants ont perdu la vie.",
        )


def depart_orders(state, events):
    for order in state["orders"]:
        if order["status"] != "confirmed" or order["execute_month"] != state["month"]:
            continue
        actor = order["actor"]
        reason = None
        if any(
            state["cities"][city_id]["owner"] != actor or state["cities"][city_id]["stock"] < amount
            for city_id, amount in order["funding"].items()
        ):
            reason = "Le financement réservé n’est plus disponible."
        if order["kind"] in ("raid", "capture"):
            eligible = eligible_origins(state, actor, order["target"])
            if any(
                city_id not in eligible or state["cities"][city_id]["fideles"] < count
                for city_id, count in order["contributions"].items()
            ):
                reason = "Les contributions ne peuvent plus rejoindre cette frontière."
            if (
                order["kind"] == "raid"
                and state["month"] < state["cities"][order["target"]]["raid_protected_until"]
            ):
                reason = "La protection contre le pillage est encore active."
        for task in order["tasks"]:
            city = state["cities"][task["city"]]
            if city["owner"] != actor or (task["kind"] == "walls" and city["damaged"]):
                reason = "La cité ou l’état de l’enceinte ne permet plus ces travaux."
        if reason:
            order["status"] = "invalidated"
            report(
                events,
                actor,
                "order",
                "Ordre invalidé",
                reason + " Toutes les réservations sont libérées.",
            )
            continue
        for city_id, amount in order["funding"].items():
            state["cities"][city_id]["stock"] -= amount
        order["status"] = "active"
        if order["kind"] in ("raid", "capture"):
            for city_id, count in order["contributions"].items():
                state["cities"][city_id]["fideles"] -= count
            state["expeditions"].append(
                {
                    "id": order["id"],
                    "actor": actor,
                    "kind": order["kind"],
                    "target": order["target"],
                    "cohorts": dict(order["contributions"]),
                    "status": "outbound",
                    "combativity": EQUIPMENT[state["players"][actor]["equipment"]],
                    "loot": 0,
                    "departure_month": state["month"],
                    "combat_month": state["month"] + 1,
                    "return_month": state["month"] + 2,
                }
            )
        else:
            tasks = (
                order["tasks"]
                if order["tasks"]
                else [
                    {
                        "kind": "equipment",
                        "level": order["level"],
                        "duration": order["duration"],
                        "city": None,
                    }
                ]
            )
            for task in tasks:
                state["works"].append(
                    {
                        **task,
                        "order_id": order["id"],
                        "actor": actor,
                        "status": "active",
                        "start_month": state["month"],
                        "finish_month": state["month"] + task["duration"],
                    }
                )
        report(
            events,
            actor,
            "order",
            "Votre décret entre en vigueur",
            f"Votre ordre a pris son cours : {ACTION_LABELS[order['kind']].lower()}. J’ai fait prélever {number(order['cost'])} Mesures dans les greniers qui les avaient promises. Les nouvelles vous seront rapportées à leur échéance.",
        )


def finish_works(state, events):
    for work in state["works"]:
        if work["status"] != "active" or work["finish_month"] > state["month"]:
            continue
        work["status"] = "completed"
        if work["kind"] == "equipment":
            state["players"][work["actor"]]["equipment"] = work["level"]
            recipient = work["actor"]
            title = "La forge a achevé son œuvre"
            body = (
                "Les maîtres de la forge ont achevé ce que vous leur aviez confié. "
                + EQUIPMENT_LABELS[work["level"]]
                + " : tel est désormais l’état de nos hommes. Leur organisation équipera aussi les populations qui rejoindront votre maison."
            )
        else:
            city = state["cities"][work["city"]]
            if work["kind"] == "repair":
                city["damaged"] = False
            else:
                city[work["kind"]] = work["level"]
            recipient = city["owner"]
            title = f"Travaux achevés à {city['name']}"
            body = f"Les équipes de {city['name']} ont mené leur tâche à son terme : {work_phrase(work['kind'], work['level']).lower()}. L’ouvrage est désormais en service ; j’en tiendrai compte dans les registres à venir."
        report(events, recipient, "work", title, body)
    active = {work["order_id"] for work in state["works"] if work["status"] == "active"}
    for order in state["orders"]:
        if (
            order["kind"] not in ("raid", "capture")
            and order["status"] == "active"
            and order["id"] not in active
        ):
            order["status"] = "completed"


def relief_allocations(state, missions, priority):
    """Allocate once from the pre-combat snapshot; no iterative redistribution."""
    proposals = []
    for city_id in priority:
        city = state["cities"][city_id]
        component = connected_component(state, city_id)
        threats = {
            mission["id"]: sum(mission["cohorts"].values()) * mission["combativity"]
            for mission in missions
            if mission["kind"] == "capture"
            and mission["target"] != city_id
            and mission["target"] in component
            and mission["actor"] != city["owner"]
        }
        if not threats:
            continue
        split = allocate(city["fideles"] // 5, threats, [m["id"] for m in missions])
        for mission_id, count in split.items():
            proposals.append(
                {
                    "origin": city_id,
                    "mission": mission_id,
                    "actor": city["owner"],
                    "count": count,
                    "combativity": EQUIPMENT[state["players"][city["owner"]]["equipment"]],
                }
            )
    for mission in missions:
        contributions = [item for item in proposals if item["mission"] == mission["id"]]
        if not contributions:
            continue
        limit = (
            sum(mission["cohorts"].values())
            * mission["combativity"]
            // contributions[0]["combativity"]
        )
        weights = {item["origin"]: item["count"] for item in contributions}
        if sum(weights.values()) > limit:
            split = allocate(limit, weights, priority)
            for item in contributions:
                item["count"] = split[item["origin"]]
    return [item for item in proposals if item["count"]]


def military_deaths(state, origin, count):
    state["cities"][origin]["population"] -= count
    state["cities"][origin]["military_deaths"] += count


def lose_attackers(state, mission, dead, priority):
    split = allocate(dead, mission["cohorts"], priority)
    for origin, count in split.items():
        mission["cohorts"][origin] -= count
        military_deaths(state, origin, count)


def observation(enemy_count, own_survivors, equipment):
    if own_survivors == 0:
        return "Aucun survivant ne peut décrire les forces adverses."
    if own_survivors < 10:
        return "Les rares survivants ne livrent que des observations incertaines."
    if enemy_count == 0:
        return "Nos survivants n’ont rencontré aucun défenseur."
    lower = enemy_count // 20 * 20
    return f"Nos survivants disent avoir rencontré entre {lower} et {lower + 19} hommes, avec un {EQUIPMENT_LABELS[equipment].lower()}. Je rapporte ce qu’ils ont vu à la date de cette lettre ; leur récit ne révèle pas les forces de tout le domaine adverse."


def resolve_combats(state, seed, events):
    due = [
        mission
        for mission in state["expeditions"]
        if mission["status"] == "outbound" and mission["combat_month"] == state["month"]
    ]
    priority = sorted(state["cities"])
    random_stream(seed, state["month"], "rounding").shuffle(priority)
    random_stream(seed, state["month"], "combat").shuffle(due)
    relief = relief_allocations(state, due, priority)
    audit_relief = deepcopy(relief)
    for item in relief:
        state["cities"][item["origin"]]["fideles"] -= item["count"]
    audit = {
        "priority": priority,
        "combat_order": [mission["id"] for mission in due],
        "relief": audit_relief,
        "encounters": {},
    }
    for mission in due:
        target = state["cities"][mission["target"]]
        defender = target["owner"]
        actor = mission["actor"]
        order = next(item for item in state["orders"] if item["id"] == mission["id"])
        order["status"] = "returning"
        mission["status"] = "returning"
        if defender == actor or state["players"][actor]["eliminated"]:
            report(
                events,
                actor,
                "battle",
                "L’expédition renonce au combat",
                "Le combat n’a plus lieu d’être. Les hommes rentrent selon le calendrier prévu, sans remboursement.",
            )
            continue
        attackers = sum(mission["cohorts"].values())
        defender_equipment = state["players"][defender]["equipment"]
        defense_combativity = EQUIPMENT[defender_equipment]
        attacker_equipment = EQUIPMENT.index(mission["combativity"])
        if mission["kind"] == "raid":
            if state["month"] < target["raid_protected_until"]:
                report(
                    events,
                    actor,
                    "battle",
                    "Pillage impossible",
                    "Les villages sont encore protégés. Les hommes rentrent sans remboursement.",
                )
                continue
            fraction = random_stream(seed, state["month"], f"raid:{mission['id']}").choice(
                [20, 30, 40]
            )
            audit["encounters"][mission["id"]] = fraction
            encountered = max(1, target["fideles"] * fraction // 100) if target["fideles"] else 0
            result = raid_result(
                attackers, mission["combativity"], encountered, defense_combativity, target["stock"]
            )
            lose_attackers(state, mission, result.attacker_losses, priority)
            target["fideles"] -= result.defender_losses
            military_deaths(state, target["id"], result.defender_losses)
            target["stock"] -= result.stolen + result.destroyed
            mission["loot"] = result.stolen
            if result.outcome == "success":
                target["raid_protected_until"] = state["month"] + 12
            report(
                events,
                actor,
                "battle",
                f"{OUTCOME_LABELS[result.outcome]} à {target['name']}",
                f"La nouvelle de cette expédition nous est parvenue. {military_losses(result.attacker_losses)} "
                + (
                    f"Les survivants transportent {number(result.stolen)} Mesures vers leurs origines ; nous ne pourrons les engager avant leur retour. "
                    if result.stolen
                    else "Les survivants rentreront sans butin. "
                )
                + observation(encountered, attackers - result.attacker_losses, defender_equipment),
            )
            report(
                events,
                defender,
                "battle",
                f"Les villages de {target['name']} ont été attaqués",
                f"Le raid sur nos villages a coûté la vie à {result.defender_losses} de nos Fidèles. Les assaillants ont emporté {number(result.stolen)} Mesures et en ont détruit {number(result.destroyed)} autres. Ces pertes sont inscrites dans le grenier de la cité. "
                + observation(attackers, encountered - result.defender_losses, attacker_equipment),
            )
            continue
        support = [
            item
            for item in relief
            if item["mission"] == mission["id"] and item["actor"] == defender
        ]
        local = target["fideles"]
        reinforcement = sum(item["count"] for item in support)
        relief_strength = sum(item["count"] * item["combativity"] for item in support)
        field = local * defense_combativity + relief_strength
        wall = WALLS[target["walls"]]
        if target["damaged"]:
            wall = 1 + (wall - 1) / 2
        fortified = local * defense_combativity * wall + relief_strength
        exported = sum(item["count"] for item in relief if item["origin"] == target["id"])
        present_population = target["population"] - absent(state, target["id"]) - exported
        result = capture_result(
            rule_family(state["rules"]),
            attackers * mission["combativity"],
            field,
            fortified,
            target["stock"],
            present_population,
        )
        attacker_dead = losses(attackers, result.attacker_rate)
        defender_dead = losses(local + reinforcement, result.defender_rate)
        lose_attackers(state, mission, attacker_dead, priority)
        weights = {target["id"]: local, **{item["origin"]: item["count"] for item in support}}
        split = allocate(defender_dead, weights, priority)
        target["fideles"] -= split[target["id"]]
        military_deaths(state, target["id"], split[target["id"]])
        for item in support:
            dead = split[item["origin"]]
            item["count"] -= dead
            military_deaths(state, item["origin"], dead)
        # Civilians exclude all Fidèles, including absent expeditions and relief.
        civilians = max(
            0, target["population"] - target["fideles"] - absent(state, target["id"]) - exported
        )
        civilian_dead = losses(civilians, result.civilian_rate)
        target["population"] -= civilian_dead
        target["civilian_deaths"] += civilian_dead
        target["stock"] -= result.food_used
        if result.captured:
            target["owner"] = actor
            if (
                rule_family(state["rules"]).siege
                and result.outcome == "assault"
                and target["walls"]
            ):
                target["damaged"] = True
            for recipient in state["players"]:
                report(
                    events,
                    recipient,
                    "sovereignty",
                    f"{target['name']} change de souverain",
                    f"Le nom du souverain a changé dans les registres de {target['name']}. La cité relève désormais de {state['players'][actor]['name']} ; c’est tout ce que cette nouvelle publique nous apprend.",
                )
        report(
            events,
            actor,
            "battle",
            f"{OUTCOME_LABELS[result.outcome]} à {target['name']}",
            f"{military_losses(attacker_dead)} Les survivants repartent vers leurs origines ; ils y rejoindront les présents à la date annoncée. "
            + observation(local + reinforcement, attackers - attacker_dead, defender_equipment),
        )
        report(
            events,
            defender,
            "battle",
            f"La bataille de {target['name']}",
            f"Voici l’issue que l’on nous rapporte : {OUTCOME_LABELS[result.outcome].lower()}. Nous avons perdu {defender_dead} Fidèles engagés, dont {split[target['id']]} de la garnison locale, ainsi que {civilian_dead} civils. "
            + (
                f"Le siège a consommé {number(result.food_used)} Mesures prises dans le grenier de cette cité. "
                if result.outcome in ("held", "shortage")
                else ""
            )
            + observation(attackers, local + reinforcement - defender_dead, attacker_equipment),
        )
    # Relief stays away throughout the whole phase, even after its battle.
    for item in relief:
        state["cities"][item["origin"]]["fideles"] += item["count"]
    return audit


def return_expeditions(state, events):
    for mission in state["expeditions"]:
        if mission["status"] == "completed" or mission["return_month"] > state["month"]:
            continue
        shares = allocate(mission["loot"], mission["cohorts"])
        for city_id, survivors in mission["cohorts"].items():
            city = state["cities"][city_id]
            city["fideles"] += survivors
            deposited = min(shares[city_id], capacity(city) - city["stock"])
            city["stock"] += deposited
            report(
                events,
                city["owner"],
                "return",
                f"Retour à {city['name']}",
                f"J’ai fait inscrire le retour de {survivors} Fidèles à {city['name']}. Ils rejoignent les présents de leur cité d’origine. {returned_loot(deposited, shares[city_id] - deposited)}",
            )
        if not sum(mission["cohorts"].values()):
            report(
                events,
                mission["actor"],
                "return",
                "Une expédition ne reviendra pas",
                "Aucun homme n’a survécu. Aucun butin n’est déposé.",
            )
        mission["loot"] = 0
        mission["status"] = "completed"
        next(item for item in state["orders"] if item["id"] == mission["id"])["status"] = (
            "completed"
        )


def standings(state):
    rows = [
        {
            "actor": actor,
            "name": player["name"],
            "cities": len(owned_cities(state, actor)),
            "population": sum(city["population"] for city in owned_cities(state, actor)),
        }
        for actor, player in state["players"].items()
    ]
    rows.sort(key=lambda row: (-row["cities"], -row["population"]))
    previous = None
    rank = 0
    for index, row in enumerate(rows):
        value = (row["cities"], row["population"])
        if value != previous:
            rank = index + 1
        row["rank"] = rank
        previous = value
    return rows


def check_end(state, events):
    for actor, player in state["players"].items():
        if not owned_cities(state, actor) and not player["eliminated"]:
            player["eliminated"] = True
            for mission in state["expeditions"]:
                if mission["actor"] == actor and mission["status"] == "outbound":
                    mission["status"] = "returning"
                    next(order for order in state["orders"] if order["id"] == mission["id"])[
                        "status"
                    ] = "returning"
            report(
                events,
                actor,
                "result",
                "Votre prétention au trône s’achève",
                "Vous ne possédez plus de cité. Vos armées encore en route rentrent vers leurs origines.",
            )
    if (
        len({city["owner"] for city in state["cities"].values()}) == 1
        or state["month"] >= state["config"]["reign_months"]
    ):
        state["status"] = "finished"
        state["result"] = {
            "month": state["month"],
            "rules": state["rules"],
            "standings": standings(state),
            "expeditions_in_transit": sum(
                mission["status"] != "completed" for mission in state["expeditions"]
            ),
        }
        winners = " · ".join(
            row["name"] for row in state["result"]["standings"] if row["rank"] == 1
        )
        for actor in state["players"]:
            report(
                events,
                actor,
                "result",
                "Le règne est achevé",
                f"Au premier rang : {winners}. Les opérations encore en route ne modifieront plus ce résultat.",
            )


def assert_invariants(state):
    funds, people = reservations(state)
    for city_id, city in state["cities"].items():
        assert 0 <= funds[city_id] <= city["stock"] <= capacity(city), ("stock", city_id)
        assert 0 <= people[city_id] <= city["fideles"], ("reservation", city_id)
        assert 0 <= city["fideles"] + absent(state, city_id) <= city["population"], (
            "population",
            city_id,
        )
        assert city["tax"] >= 0
    active = [
        order["target"]
        for order in state["orders"]
        if order["kind"] in ("raid", "capture") and order["status"] in ("confirmed", "active")
    ]
    assert len(active) == len(set(active)), "Duplicate target engagement"
    work_slots = [
        work["city"] for work in state["works"] if work["status"] == "active" and work.get("city")
    ]
    work_slots += [
        task["city"]
        for order in state["orders"]
        if order["status"] == "confirmed"
        for task in order["tasks"]
    ]
    assert len(work_slots) == len(set(work_slots)), "Duplicate construction slot"


def advance_month(state, seed):
    if state["status"] != "active":
        raise RuleError("Ce règne est déjà terminé.")
    state["month"] += 1
    events = []
    annual_economy(state, events)
    depart_orders(state, events)
    finish_works(state, events)
    audit = resolve_combats(state, seed, events)
    return_expeditions(state, events)
    check_end(state, events)
    assert_invariants(state)
    return events, audit


def bot_orders(state, seed):
    """A modest policy using owned state and public geography, never enemy stocks/men."""
    accepted = []
    for actor, player in state["players"].items():
        if not player["bot"] or player["eliminated"]:
            continue
        rng = random_stream(seed, state["month"], f"bot:{actor}")
        cities = owned_cities(state, actor)
        rng.shuffle(cities)
        targets = [
            city_id for city_id in state["cities"] if eligible_origins(state, actor, city_id)
        ]
        rng.shuffle(targets)
        funds, people = reservations(state)
        wealth = sum(city["stock"] - funds[city["id"]] for city in cities)
        proposals = []
        if wealth >= 3_600_000:
            for target in targets:
                eligible = eligible_origins(state, actor, target)
                contributions = {
                    city["id"]: max(0, city["fideles"] - people[city["id"]] - 15)
                    for city in cities
                    if city["id"] in eligible
                }
                budget = max(0, (wealth - 900_000) // 18000)
                total = min(240, budget, sum(contributions.values()))
                if total >= 150:
                    contributions = allocate(total, contributions)
                    proposals.append(
                        {"kind": "capture", "target": target, "contributions": contributions}
                    )
        if state["month"] % 3 == 0:
            for city in cities:
                proposals.append({"kind": "irrigation", "cities": [city["id"]]})
        if state["month"] % 4 == 1:
            for city in cities:
                if city["walls"] == 0:
                    proposals.append({"kind": "walls", "cities": [city["id"]]})
        if rule_family(state["rules"]).storage and wealth > 4_000_000:
            proposals.append({"kind": "equipment"})
            for city in cities:
                proposals.append({"kind": "storage", "cities": [city["id"]]})
        if state["month"] % 5 == 2:
            for target in targets:
                origins = eligible_origins(state, actor, target)
                origin = next(
                    (
                        city
                        for city in cities
                        if city["id"] in origins and city["fideles"] - people[city["id"]] >= 45
                    ),
                    None,
                )
                if origin:
                    proposals.append(
                        {"kind": "raid", "target": target, "contributions": {origin["id"]: 45}}
                    )
        for spec in proposals:
            try:
                order = confirm_order(state, actor, spec, f"bot-{actor}-{state['month']}")
            except RuleError:
                continue
            accepted.append(order)
            break
    return accepted
