"""The simulation aggregate. Functions mutate only the supplied in-memory state.

The application persists a successful command atomically under its game lock.
No function here imports Django, reads a clock, or accesses storage.
"""

import hashlib
import random
from copy import deepcopy
from fractions import Fraction

from . import tactics
from .calendar import closed_moon, closing_moon, open_calendar
from .messages import describe, message
from .narration import (
    STARTED_ACTION_PHRASES,
    completed_work_phrase,
    military_losses,
    number,
    observed_losses,
    raid_finances,
    returned_loot,
)
from .rules import (
    ACTION_LABELS,
    EQUIPMENT_LABELS,
    OUTCOME_LABELS,
    RuleError,
    allocate,
    capacities,
    capture_result,
    effective_level,
    equipment_labels,
    equipment_values,
    expedition_prices,
    integrity_after_combat,
    losses,
    raid_result,
    rule_family,
    strategic_raid_result,
    tax_yield,
    wall_multiplier,
    work_prices,
)

CITY_NAMES = ["Qasr", "Tamesh", "Namar", "Sefra", "Ishar", "Daram", "Azal", "Mirha", "Tazir"]
REALM_NAMES = [
    "La maison d’Ambre",
    "Les seigneurs de Sefra",
    "La ligue d’Azal",
]


def new_state(
    version="V1",
    reign_months=120,
    opponents="active",
    player_name=message("La maison d’Ambre"),
    *,
    calendar_version=2,
    forge_version=2,
    map_version=3,
    economy_version=4,
    strategy_version=2,
):
    rule_family(version)
    if (
        reign_months not in (24, 60, 120, 240)
        or opponents not in ("active", "passive")
        or strategy_version not in (1, 2)
    ):
        raise RuleError(message("La configuration de cette partie est invalide."))
    cities = {}
    for index, name in enumerate(CITY_NAMES):
        city_id = f"c{index + 1}"
        cities[city_id] = {
            "id": city_id,
            "name": name,
            "owner": f"p{index // 3 + 1}",
            "population": 1000,
            "fideles": 100,
            "stock": 900_000 if economy_version >= 4 else 600_000,
            "tax": 0,
            "irrigation": 0,
            "storage": 0,
            "walls": 0,
            "forge": 0,
            "damaged": False,
            "raid_protected_until": 0,
            **(
                {"watch": 0, "shelter": 0, "transport": 0, "siege": 0}
                if economy_version >= 3
                else {}
            ),
            **({"integrity": 100, "damaged_works": []} if economy_version >= 4 else {}),
            "military_deaths": 0,
            "civilian_deaths": 0,
        }
    return {
        "schema": 1,
        "rules": version,
        "month": 1 if calendar_version == 2 else 0,
        "calendar_version": calendar_version,
        "forge_version": forge_version,
        "map_version": map_version,
        "economy_version": economy_version,
        "strategy_version": strategy_version if economy_version >= 4 else 1,
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
        "links": [[f"c{index + 1}", f"c{(index + 1) % 9 + 1}"] for index in range(9)]
        + (
            [["c1", "c5"], ["c4", "c8"], ["c7", "c2"], ["c2", "c4"], ["c5", "c7"], ["c8", "c1"]]
            if map_version == 2
            else [["c1", "c3"], ["c4", "c6"], ["c7", "c9"]]
            if map_version == 3
            else []
        ),
        "orders": [],
        "works": [],
        "expeditions": [],
        **({"convoys": []} if economy_version >= 4 else {}),
        "result": None,
    }


def owned_cities(state, actor):
    return [city for city in state["cities"].values() if city["owner"] == actor]


def restricted_fideles(state, city):
    if tactics.enabled(state) and closing_moon(state) < city.get("restricted_until", 0):
        return min(city["fideles"], city.get("restricted_fideles", 0))
    return 0


def deployable_fideles(state, city_id):
    city = state["cities"][city_id]
    return city["fideles"] - restricted_fideles(state, city)


def lose_local_fideles(state, city, count):
    restricted = restricted_fideles(state, city)
    if restricted:
        split = allocate(count, {"restricted": restricted, "free": city["fideles"] - restricted})
        city["restricted_fideles"] = restricted - split["restricted"]
    city["fideles"] -= count


def capacity(city, economy_version=1):
    return capacities(economy_version)[city["storage"]]


def absent(state, city_id):
    return sum(
        mission["cohorts"].get(city_id, 0)
        for mission in state["expeditions"]
        if mission["status"] != "completed"
        and city_id not in mission.get("detached_origins", [])
        and city_id not in mission.get("arrived_origins", [])
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


def local_forges(state):
    return state.get("forge_version", 1) == 2


def city_equipment(state, city):
    return city["forge"] if local_forges(state) else state["players"][city["owner"]]["equipment"]


def mission_strength(mission):
    if "cohort_equipment" in mission:
        return sum(
            count * mission["cohort_equipment"][origin]
            for origin, count in mission["cohorts"].items()
        )
    return sum(mission["cohorts"].values()) * mission["combativity"]


def ensure_actor(state, actor):
    if state["status"] != "active":
        raise RuleError(message("Le règne est terminé. Son résultat est désormais scellé."))
    if actor not in state["players"] or state["players"][actor]["eliminated"]:
        raise RuleError(message("Ce Prétendant ne peut plus donner d’ordres."))


def work_spec(state, city, kind):
    rules = rule_family(state["rules"])
    prices = work_prices(state.get("economy_version", 1))
    if kind not in prices:
        raise RuleError(message("Ce chantier n’existe pas."))
    if kind in ("storage", "repair", "forge") and not rules.storage:
        raise RuleError(message("Cette action appartient aux règles V1."))
    if kind == "forge" and not local_forges(state):
        raise RuleError(message("Ce règne conserve son projet d’armement commun."))
    strategic = state.get("economy_version", 1) >= 4
    if kind in ("repair_watch", "repair_shelter"):
        family = kind.removeprefix("repair_")
        if family not in city["damaged_works"]:
            raise RuleError(message("Cet ouvrage ne nécessite aucune réparation."))
        level = city[family]
    elif kind == "repair":
        if city["integrity"] == 100 if strategic else not city["walls"] or not city["damaged"]:
            raise RuleError(message("Cette enceinte ne nécessite aucune réparation."))
        level = city["walls"]
    else:
        if strategic and kind in city["damaged_works"]:
            raise RuleError(message("Il faut réparer cet ouvrage avant de l’améliorer."))
        level = city[kind] + 1
        maximum = len(prices[kind]) if state.get("economy_version", 1) >= 3 else rules.max_level
        if level > maximum:
            raise RuleError(message("Le niveau maximal de cet ouvrage est déjà atteint."))
        if kind == "walls" and city["damaged"]:
            raise RuleError(message("Il faut réparer l’enceinte avant de la renforcer."))
    cost, duration = (
        (20_000, 2) if strategic and kind == "repair" and level == 0 else prices[kind][level - 1]
    )
    if strategic and closing_moon(state) + duration > state["config"]["reign_months"]:
        raise RuleError(message("Ce chantier s’achèverait après la fin du règne."))
    if kind == "forge" and state.get("economy_version", 1) < 3:
        cost = max(cost, (600 if level == 1 else 1400) * city["population"])
    return {"city": city["id"], "kind": kind, "level": level, "cost": cost, "duration": duration}


def normalized_contributions(entries):
    if not isinstance(entries, dict) and not isinstance(entries, list):
        raise RuleError(message("Les contributions militaires sont invalides."))
    pairs = entries.items() if isinstance(entries, dict) else entries
    contributions = {}
    try:
        for city_id, count in pairs:
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError
            if count:
                contributions[city_id] = contributions.get(city_id, 0) + count
    except (ValueError, TypeError):
        raise RuleError(
            message("Les effectifs doivent être des nombres entiers positifs.")
        ) from None
    return contributions


def prepare_order(state, actor, spec, order_id):
    ensure_actor(state, actor)
    rules = rule_family(state["rules"])
    funds, people = reservations(state)
    available = {
        city["id"]: city["stock"] - funds[city["id"]] for city in owned_cities(state, actor)
    }
    kind = spec.get("kind")
    prices = expedition_prices(state.get("economy_version", 1))
    order = {
        "id": order_id,
        "actor": actor,
        "kind": kind,
        "status": "confirmed",
        "execute_month": closing_moon(state),
        "funding": {},
        "cost": 0,
        "tasks": [],
    }
    if kind in work_prices(state.get("economy_version", 1)):
        targets = spec.get("cities", [])
        if not isinstance(targets, list) or not targets or len(targets) != len(set(targets)):
            raise RuleError(message("Choisissez au moins une cité, une seule fois chacune."))
        for city_id in sorted(targets):
            city = state["cities"].get(city_id)
            if not city or city["owner"] != actor:
                raise RuleError(message("Cette cité ne relève pas de votre autorité."))
            if city_id in busy_cities(state):
                raise RuleError(message("Les équipes de cette cité sont déjà engagées."))
            order["tasks"].append(work_spec(state, city, kind))
        order["cost"] = sum(task["cost"] for task in order["tasks"])
    elif kind == "equipment":
        if local_forges(state):
            raise RuleError(message("Confiez la forge aux équipes d’une cité."))
        if not rules.equipment:
            raise RuleError(message("Les projets d’armement appartiennent aux règles V1."))
        player = state["players"][actor]
        if player["equipment"] >= 2 or equipment_busy(state, actor):
            raise RuleError(
                message("Votre forge est déjà engagée ou son organisation est achevée.")
            )
        order.update(equipment_spec(state, actor))
    elif kind == "convoy" and state.get("economy_version", 1) >= 4:
        origin, target, cargo = spec.get("origin"), spec.get("target"), spec.get("cargo")
        if origin not in available or target not in available or origin == target:
            raise RuleError(message("Choisissez deux cités distinctes de votre maison."))
        if target not in connected_component(state, origin):
            raise RuleError(message("Le convoi exige un chemin entièrement amical."))
        if isinstance(cargo, bool) or not isinstance(cargo, int) or not 1 <= cargo <= 500_000:
            raise RuleError(message("La cargaison doit contenir de 1 à 500 000 Mesures entières."))
        if any(
            item["kind"] == "convoy"
            and item.get("origin") == origin
            and item["status"] in ("confirmed", "active", "returning")
            for item in state["orders"]
        ):
            raise RuleError(message("Un convoi est déjà engagé depuis cette cité."))
        fee = (cargo * [10, 7, 5][state["cities"][origin]["transport"]] + 99) // 100
        order.update(
            origin=origin,
            target=target,
            cargo=cargo,
            fee=fee,
            cost=cargo + fee,
            funding={origin: cargo + fee},
        )
    elif kind in ("raid", "capture"):
        target = spec.get("target")
        if target not in state["cities"] or state["cities"][target]["owner"] == actor:
            raise RuleError(message("Choisissez une cité ennemie de cette partie."))
        if not tactics.enabled(state) and target in active_targets(state):
            raise RuleError(
                message(
                    "Une autre expédition est déjà engagée vers cette cité. Aucun moyen n’a été réservé."
                )
            )
        if (
            kind == "raid"
            and not tactics.enabled(state)
            and (
                closing_moon(state) + 1
                if state.get("economy_version", 1) >= 3
                else closed_moon(state)
            )
            < state["cities"][target]["raid_protected_until"]
        ):
            raise RuleError(
                message("Les villages ne constituent pas une cible de pillage disponible.")
            )
        contributions = normalized_contributions(spec.get("contributions", {}))
        eligible = eligible_origins(state, actor, target)
        for city_id, count in contributions.items():
            if city_id not in eligible:
                raise RuleError(
                    message(
                        "Cette communauté ne peut rejoindre cette frontière par nos possessions."
                    )
                )
            if count > deployable_fideles(state, city_id) - people[city_id]:
                raise RuleError(
                    message("Certains de ces hommes sont déjà promis à une autre expédition.")
                )
        total = sum(contributions.values())
        minimum = state["config"][f"{kind}_minimum"]
        if total < minimum:
            raise RuleError(
                message("Cette expédition demande au moins {p0} Fidèles au total.", p0=minimum)
            )
        if tactics.enabled(state):
            launch = tactics.launch_city(state, actor, target, contributions)
            if launch is None:
                raise RuleError(
                    message(
                        "Les contingents doivent rejoindre une même cité de frontière par nos possessions."
                    )
                )
            order["launch_city"] = launch
        order.update(
            {
                "target": target,
                "contributions": contributions,
                "cost": prices[kind]["base"] + prices[kind]["per_person"] * total,
            }
        )
    else:
        raise RuleError(message("Cet ordre n’est pas reconnu."))
    if state.get("economy_version", 1) >= 2 and kind != "equipment":
        if order["tasks"]:
            for task in order["tasks"]:
                task["funding"] = {task["city"]: task["cost"]}
                order["funding"][task["city"]] = task["cost"]
        elif kind != "convoy":
            fees = allocate(prices[kind]["base"], contributions)
            order["funding"] = {
                city_id: fees[city_id] + prices[kind]["per_person"] * count
                for city_id, count in contributions.items()
            }
        for city_id, amount in order["funding"].items():
            if amount > available[city_id]:
                raise RuleError(
                    message(
                        "Le grenier de {city} manque de {shortfall} Mesures libres pour cet ordre.",
                        city=state["cities"][city_id]["name"],
                        shortfall=number(amount - available[city_id]),
                    )
                )
        return order
    if sum(available.values()) < order["cost"]:
        raise RuleError(message("Cette dépense dépasserait les moyens non engagés."))
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


def equipment_spec(state, actor):
    level = state["players"][actor]["equipment"] + 1
    population = sum(city["population"] for city in owned_cities(state, actor))
    return {
        "level": level,
        "duration": 8 if level == 1 else 14,
        "cost": max(1_800_000, 600 * population)
        if level == 1
        else max(4_200_000, 1400 * population),
    }


def confirm_order(state, actor, spec, order_id):
    existing = next((order for order in state["orders"] if order["id"] == order_id), None)
    if existing:
        if existing["actor"] != actor:
            raise RuleError(message("Cet identifiant de confirmation est déjà utilisé."))
        return existing
    order = prepare_order(state, actor, spec, order_id)
    state["orders"].append(order)
    return order


def cancel_order(state, actor, order_id):
    ensure_actor(state, actor)
    if not rule_family(state["rules"]).cancellable:
        raise RuleError(message("En V0, une confirmation est définitive."))
    order = next(
        (item for item in state["orders"] if item["id"] == order_id and item["actor"] == actor),
        None,
    )
    if not order or order["status"] != "confirmed":
        raise RuleError(message("Cet ordre ne peut plus être annulé."))
    order["status"] = "cancelled"
    order["cancelled_month"] = closing_moon(state)
    return order


def random_stream(seed, month, purpose):
    digest = hashlib.sha256(f"{seed}:{month}:{purpose}".encode()).digest()
    return random.Random(int.from_bytes(digest, "big"))


def report(events, recipient, kind, title, body, *, scene=None, city_id=None, observation=None):
    content = {"title": describe(title), "body": describe(body)}
    if scene:
        content["scene"] = scene
    if city_id:
        content["city_id"] = city_id
    if observation is not None:
        content["observation"] = describe(observation)
    events.append(
        {
            "recipient": recipient,
            "kind": kind,
            "title": title,
            "body": body,
            "content": content,
        }
    )


def annual_economy(state, events):
    for city in state["cities"].values():
        city["tax"] += (city["population"] - absent(state, city["id"])) * tax_yield(
            city["irrigation"], state.get("economy_version", 1)
        )
        if state["month"] % 12:
            continue
        if state.get("economy_version", 1) < 3:
            harvest_city(state, city, events)


def harvest_city(state, city, events):
    rules = rule_family(state["rules"])
    added = min(city["tax"], capacity(city, state.get("economy_version", 1)) - city["stock"])
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
        message("La récolte de {p0}", p0=city["name"]),
        message(
            "Les comptes de {p0} sont arrêtés pour cette année. Le prélèvement a fait entrer {p1} Mesures dans son grenier ; {p2} autres n’ont pu y trouver place. J’ai inscrit {p3} nouveaux habitants et {p4} habitants rejoignant les Fidèles. La cité compte à présent {p5} habitants. Depuis le début du règne, {p6} de ses habitants ont perdu la vie.",
            p0=city["name"],
            p1=number(added),
            p2=number(overflow),
            p3=growth,
            p4=renewed,
            p5=number(city["population"]),
            p6=city["military_deaths"] + city["civilian_deaths"],
        ),
        city_id=city["id"] if state.get("economy_version", 1) >= 4 else None,
    )


def departure_refuge(state, origin):
    return next(iter(sorted(connected_component(state, origin) - {origin})), None)


def detach_absent_contingents(state, city_id):
    """Only people physically present change house when their city is captured."""
    for mission in state["expeditions"]:
        if (
            mission["status"] != "completed"
            and city_id in mission["cohorts"]
            and city_id not in mission["detached_origins"]
            and city_id not in mission["arrived_origins"]
        ):
            state["cities"][city_id]["population"] -= mission["cohorts"][city_id]
            mission["detached_origins"].append(city_id)


def return_convoys(state, events):
    for convoy in state.get("convoys", []):
        if convoy["status"] == "completed" or convoy["arrival_month"] > state["month"]:
            continue
        actor = convoy["actor"]
        target = state["cities"][convoy["target"]]
        if target["owner"] != actor and convoy["status"] == "outbound":
            destination = (
                convoy["origin"]
                if state["cities"][convoy["origin"]]["owner"] == actor
                else convoy["refuge"]
            )
            if destination and state["cities"][destination]["owner"] == actor:
                convoy.update(
                    target=destination, status="returning", arrival_month=state["month"] + 1
                )
                report(
                    events,
                    actor,
                    "return",
                    message("Le convoi fait demi-tour"),
                    message(
                        "La destination a changé de maître. Le convoi tentera de rejoindre {city} à la lune {moon}.",
                        city=state["cities"][destination]["name"],
                        moon=convoy["arrival_month"],
                    ),
                )
                continue
        deposited = (
            min(convoy["cargo"], capacity(target, state["economy_version"]) - target["stock"])
            if target["owner"] == actor
            else 0
        )
        target["stock"] += deposited
        convoy.update(status="completed", deposited=deposited, lost=convoy["cargo"] - deposited)
        next(order for order in state["orders"] if order["id"] == convoy["id"])["status"] = (
            "completed"
        )
        report(
            events,
            actor,
            "return",
            message("Le compte du convoi"),
            message(
                "Cargaison conservée à {city} : {kept} Mesures ; cargaison perdue ou sans place : {lost}. Frais payés : {fee} Mesures.",
                city=target["name"],
                kept=number(deposited),
                lost=number(convoy["lost"]),
                fee=number(convoy["fee"]),
            ),
            city_id=target["id"],
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
            reason = message("Le financement réservé n’est plus disponible.")
        if order["kind"] in ("raid", "capture"):
            eligible = eligible_origins(state, actor, order["target"])
            if any(
                city_id not in eligible or deployable_fideles(state, city_id) < count
                for city_id, count in order["contributions"].items()
            ):
                reason = message("Les contributions ne peuvent plus rejoindre cette frontière.")
            if (
                order["kind"] == "raid"
                and not tactics.enabled(state)
                and state["month"] + int(state.get("economy_version", 1) >= 3)
                < state["cities"][order["target"]]["raid_protected_until"]
            ):
                reason = message("La protection contre le pillage est encore active.")
            if tactics.enabled(state):
                launch = tactics.launch_city(state, actor, order["target"], order["contributions"])
                if launch is None:
                    reason = message(
                        "Les contingents ne peuvent plus rejoindre leur cité de frontière."
                    )
                else:
                    order["launch_city"] = launch
        if order["kind"] == "convoy" and order["target"] not in connected_component(
            state, order["origin"]
        ):
            reason = message("Le chemin du convoi n’est plus amical.")
        for task in order["tasks"]:
            city = state["cities"][task["city"]]
            if state.get("economy_version", 1) >= 4 and (
                state["month"] + task["duration"] > state["config"]["reign_months"]
                or task["kind"] in city["damaged_works"]
            ):
                reason = message("Le délai du règne ou un dommage empêche ce chantier.")
            if city["owner"] != actor or (task["kind"] == "walls" and city["damaged"]):
                reason = message("La cité ou l’état de l’enceinte ne permet plus ces travaux.")
        if reason:
            order["status"] = "invalidated"
            order["invalidated_month"] = state["month"]
            report(
                events,
                actor,
                "order",
                message("Ordre invalidé"),
                reason + message(" Toutes les réservations sont libérées."),
            )
            continue
        for city_id, amount in order["funding"].items():
            state["cities"][city_id]["stock"] -= amount
        order["status"] = "active"
        order["executed_month"] = state["month"]
        if order["kind"] == "convoy":
            state["convoys"].append(
                {
                    "id": order["id"],
                    "actor": actor,
                    "origin": order["origin"],
                    "target": order["target"],
                    "cargo": order["cargo"],
                    "fee": order["fee"],
                    "refuge": departure_refuge(state, order["origin"]),
                    "arrival_month": state["month"] + 2,
                    "status": "outbound",
                }
            )
        elif order["kind"] in ("raid", "capture"):
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
                    "combativity": equipment_values(state.get("economy_version", 1))[
                        state["players"][actor]["equipment"]
                    ],
                    "loot": 0,
                    "departure_month": state["month"],
                    "combat_month": state["month"] + 1,
                    "return_month": state["month"] + 2,
                }
            )
            if local_forges(state):
                state["expeditions"][-1]["cohort_equipment"] = {
                    city_id: equipment_values(state.get("economy_version", 1))[
                        city_equipment(state, state["cities"][city_id])
                    ]
                    for city_id in order["contributions"]
                }
            if state.get("economy_version", 1) >= 3:
                mission = state["expeditions"][-1]
                for attribute in ("transport", "siege"):
                    mission["cohort_" + attribute] = {
                        city_id: state["cities"][city_id][attribute]
                        for city_id in order["contributions"]
                    }
            if state.get("economy_version", 1) >= 4:
                mission["refuges"] = {
                    origin: departure_refuge(state, origin) for origin in mission["cohorts"]
                }
                mission["detached_origins"] = []
                mission["arrived_origins"] = []
            if tactics.enabled(state):
                mission["launch_city"] = order["launch_city"]
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
            STARTED_ACTION_PHRASES[order["kind"]],
            message(
                "{p0} J’ai fait prélever {p1} Mesures dans les greniers qui les avaient promises. Les nouvelles vous seront rapportées à leur échéance.",
                p0=STARTED_ACTION_PHRASES[order["kind"]],
                p1=number(order["cost"]),
            ),
        )


def finish_works(state, events):
    for work in state["works"]:
        if work["status"] != "active" or work["finish_month"] > state["month"]:
            continue
        work["status"] = "completed"
        if work["kind"] == "equipment":
            state["players"][work["actor"]]["equipment"] = work["level"]
            recipient = work["actor"]
            title = message("La forge a achevé son œuvre")
            body = (
                message("Les maîtres de la forge ont achevé ce que vous leur aviez confié. ")
                + EQUIPMENT_LABELS[work["level"]]
                + message(
                    " : tel est désormais l’état de nos hommes. Leur organisation équipera aussi les populations qui rejoindront votre maison."
                )
            )
        else:
            city = state["cities"][work["city"]]
            if work["kind"] in ("repair_watch", "repair_shelter"):
                city["damaged_works"].remove(work["kind"].removeprefix("repair_"))
            elif work["kind"] == "repair":
                city["damaged"] = False
                if state.get("economy_version", 1) >= 4:
                    city["integrity"] = 100
            else:
                city[work["kind"]] = work["level"]
            recipient = city["owner"]
            title = message("Travaux achevés à {p0}", p0=city["name"])
            body = message(
                "Les équipes de {p0} {p1}. L’ouvrage est désormais en service ; j’en tiendrai compte dans les registres à venir.",
                p0=city["name"],
                p1=completed_work_phrase(
                    work["kind"], work["level"], state.get("economy_version", 1)
                ),
            )
        report(
            events,
            recipient,
            "work",
            title,
            body,
            city_id=work.get("city") if state.get("economy_version", 1) >= 4 else None,
        )
    active = {work["order_id"] for work in state["works"] if work["status"] == "active"}
    for order in state["orders"]:
        if (
            order["kind"] not in ("raid", "capture", "convoy")
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
        if state.get("economy_version", 1) >= 4 and any(
            mission["kind"] == "capture"
            and mission["target"] == city_id
            and mission["actor"] != city["owner"]
            for mission in missions
        ):
            continue
        threats = {
            mission["id"]: mission_strength(mission)
            for mission in missions
            if mission["kind"] == "capture"
            and mission["target"] != city_id
            and mission["target"] in component
            and mission["actor"] != city["owner"]
        }
        if not threats:
            continue
        split = allocate(
            deployable_fideles(state, city_id) // 5, threats, [m["id"] for m in missions]
        )
        for mission_id, count in split.items():
            proposals.append(
                {
                    "origin": city_id,
                    "mission": mission_id,
                    "actor": city["owner"],
                    "count": count,
                    "combativity": equipment_values(state.get("economy_version", 1))[
                        city_equipment(state, city)
                    ],
                }
            )
    for mission in missions:
        contributions = [item for item in proposals if item["mission"] == mission["id"]]
        if not contributions:
            continue
        if local_forges(state) and len({item["combativity"] for item in contributions}) > 1:
            strength = sum(item["count"] * item["combativity"] for item in contributions)
            if strength > mission_strength(mission):
                shares = allocate(
                    mission_strength(mission),
                    {item["origin"]: item["count"] * item["combativity"] for item in contributions},
                    priority,
                )
                for item in contributions:
                    item["count"] = shares[item["origin"]] // item["combativity"]
            continue
        limit = mission_strength(mission) // contributions[0]["combativity"]
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
        if origin not in mission.get("detached_origins", []):
            military_deaths(state, origin, count)


def observation(enemy_count, own_survivors, equipment, economy_version=1):
    if own_survivors == 0:
        return message("Aucun survivant ne peut décrire les forces adverses.")
    if own_survivors < 10:
        return message("Les rares survivants ne livrent que des observations incertaines.")
    if enemy_count == 0:
        return message("Nos survivants n’ont rencontré aucun défenseur.")
    lower = enemy_count // 20 * 20
    return message(
        "Nos survivants disent avoir rencontré entre {p0} et {p1} hommes, avec un {p2}. Je rapporte ce qu’ils ont vu à la date de cette lettre ; leur récit ne révèle pas les forces de tout le domaine adverse.",
        p0=lower,
        p1=lower + 19,
        p2=message("ensemble d’équipements variés")
        if equipment == "mixed"
        else equipment_labels(economy_version)[equipment].lower(),
    )


def carrying_capacity(mission, dead, priority):
    casualties = allocate(dead, mission["cohorts"], priority)
    return sum(
        (count - casualties[origin]) * 5000 * (4 + mission["cohort_transport"][origin]) // 4
        for origin, count in mission["cohorts"].items()
    )


def siege_reduction(mission):
    strengths = {
        origin: count * mission["cohort_equipment"][origin]
        for origin, count in mission["cohorts"].items()
    }
    return Fraction(
        sum(strength * mission["cohort_siege"][origin] for origin, strength in strengths.items()),
        4 * sum(strengths.values()),
    )


def raid_aftermath(state, target, survivors, engaged_survivors, result, draw, relief_away=0):
    noncombat_dead = 0
    if result.stolen or result.destroyed:
        present = target["population"] - absent(state, target["id"]) - relief_away
        unengaged = present - engaged_survivors
        ceiling = min(unengaged * 2 // 1000, survivors * 5 // 100)
        noncombat_dead = draw.randint(0, ceiling)
        unengaged_fideles = target["fideles"] - engaged_survivors
        faithful_dead = sum(
            index < unengaged_fideles for index in draw.sample(range(unengaged), noncombat_dead)
        )
        target["population"] -= noncombat_dead
        lose_local_fideles(state, target, faithful_dead)
        target["civilian_deaths"] += noncombat_dead
    damaged = None
    candidates = [
        family
        for family in ("watch", "shelter")
        if target[family] and family not in target["damaged_works"]
    ]
    if (
        result.outcome in ("unopposed", "success", "contested_win")
        and survivors
        and candidates
        and draw.randrange(100) < 20
    ):
        selected = draw.choice(candidates)
        if selected == "watch" or draw.randrange(4) == 0:
            target["damaged_works"].append(selected)
            damaged = selected
    return noncombat_dead, damaged


def warning_force(band):
    return (
        message("Moins de 50 Fidèles."),
        message("Entre 50 et 99 Fidèles."),
        message("Entre 100 et 199 Fidèles."),
        message("Au moins 200 Fidèles."),
    )[band]


def detect_departures(state, events):
    for mission in state["expeditions"]:
        if mission["status"] != "outbound" or mission["combat_month"] <= state["month"]:
            continue
        city = state["cities"][mission["target"]]
        recipient = city["owner"]
        level = effective_level(city, "watch")
        if not level or recipient == mission["actor"]:
            continue
        warnings = mission.setdefault("warnings", [])
        learned = max((w["level"] for w in warnings if w["recipient"] == recipient), default=0)
        if learned >= level:
            continue
        warning = {"recipient": recipient, "level": level, "combat_month": mission["combat_month"]}
        body = message(
            "La surveillance signale une expédition vers {city}. Arrivée prévue : lune {moon}.",
            city=city["name"],
            moon=mission["combat_month"],
        )
        if level >= 2:
            count = sum(mission["cohorts"].values())
            band = sum(count >= limit for limit in (50, 100, 200))
            warning.update(kind=mission["kind"], force_band=band)
            body += message(" Mission observée : {kind}. ", kind=ACTION_LABELS[mission["kind"]])
            body += warning_force(band)
        warnings.append(warning)
        report(
            events,
            recipient,
            "warning",
            message("La surveillance de {city}", city=city["name"]),
            body,
            city_id=city["id"],
        )


def resolve_field_encounters(state, due, events):
    roads = {}
    for mission in due:
        launch = mission["launch_city"]
        edge = tuple(sorted((launch, mission["target"])))
        key = (mission["departure_month"], edge)
        roads.setdefault(key, {edge[0]: [], edge[1]: []})[launch].append(mission)
    audit = []
    priority = sorted(state["cities"])
    for (_, edge), directions in sorted(roads.items()):
        first, second = directions[edge[0]], directions[edge[1]]
        if not first or not second or first[0]["actor"] == second[0]["actor"]:
            continue
        counts = [sum(sum(m["cohorts"].values()) for m in side) for side in (first, second)]
        strengths = [sum(mission_strength(m) for m in side) for side in (first, second)]
        dead_a, dead_b, pass_a, pass_b, outcome = tactics.field_result(
            counts[0],
            strengths[0],
            counts[1],
            strengths[1],
        )
        audit.append({"road": list(edge), "outcome": outcome, "losses": [dead_a, dead_b]})
        for side, dead, continues, enemy_dead in (
            (first, dead_a, pass_a, dead_b),
            (second, dead_b, pass_b, dead_a),
        ):
            shares = allocate(dead, {m["id"]: sum(m["cohorts"].values()) for m in side})
            for mission in side:
                own_dead = shares[mission["id"]]
                lose_attackers(state, mission, own_dead, priority)
                survivors = sum(mission["cohorts"].values())
                if not continues:
                    mission["status"] = "returning"
                    next(o for o in state["orders"] if o["id"] == mission["id"])["status"] = (
                        "returning"
                    )
                body = message(
                    "Sur la route de {first} à {second}, nos troupes ont rencontré une armée adverse. Pertes propres : {dead} Fidèles. Survivants : {survivors}. ",
                    first=state["cities"][edge[0]]["name"],
                    second=state["cities"][edge[1]]["name"],
                    dead=own_dead,
                    survivors=survivors,
                )
                body += (
                    message("La route est ouverte : les survivants poursuivent leur mission.")
                    if continues
                    else message("Les survivants renoncent à avancer et rentrent à la date prévue.")
                )
                body += observed_losses(enemy_dead, survivors)
                report(
                    events,
                    mission["actor"],
                    "field",
                    message("Bataille rangée sur la frontière"),
                    body,
                    city_id=mission["launch_city"],
                )
    return audit


def resolve_combats(state, seed, events):
    due = [
        mission
        for mission in state["expeditions"]
        if mission["status"] == "outbound" and mission["combat_month"] == state["month"]
    ]
    field_audit = resolve_field_encounters(state, due, events) if tactics.enabled(state) else []
    due = [mission for mission in due if mission["status"] == "outbound"]
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
    strategic = state.get("economy_version", 1) >= 4
    if strategic:
        audit["outcomes"] = {}
    if tactics.enabled(state):
        audit["field_encounters"] = field_audit
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
                message("L’expédition renonce au combat"),
                message(
                    "Le combat n’a plus lieu d’être. Les hommes rentrent selon le calendrier prévu, sans remboursement."
                ),
            )
            continue
        attackers = sum(mission["cohorts"].values())
        defender_equipment = city_equipment(state, target)
        defense_combativity = equipment_values(state.get("economy_version", 1))[defender_equipment]
        attack_strength = mission_strength(mission)
        cohort_values = set(mission.get("cohort_equipment", {}).values())
        attacker_equipment = (
            "mixed"
            if len(cohort_values) > 1
            else equipment_values(state.get("economy_version", 1)).index(
                attack_strength // attackers
            )
        )
        if mission["kind"] == "raid":
            if state["month"] < target["raid_protected_until"]:
                report(
                    events,
                    actor,
                    "battle",
                    message("Pillage impossible"),
                    message(
                        "Les villages sont encore protégés. Les hommes rentrent sans remboursement."
                    ),
                )
                continue
            watch = effective_level(target, "watch") if state.get("economy_version", 1) >= 3 else 0
            fraction = (
                [0, 40, 60][watch]
                if watch
                else random_stream(seed, state["month"], f"raid:{mission['id']}").choice(
                    [20, 30, 40]
                )
            )
            audit["encounters"][mission["id"]] = fraction
            encountered = max(1, target["fideles"] * fraction // 100) if target["fideles"] else 0
            if strategic:
                draw = random_stream(seed, state["month"], f"raid-effects:{mission['id']}")
                intercepted = (
                    attack_strength < encountered * defense_combativity * Fraction(3, 4)
                    and draw.randrange(100) < [10, 20, 30][watch]
                )
                result = strategic_raid_result(
                    attackers,
                    attack_strength,
                    encountered,
                    encountered * defense_combativity,
                    target["tax"],
                    [200_000, 400_000, 800_000][effective_level(target, "shelter")],
                    intercepted,
                    lambda dead: carrying_capacity(mission, dead, priority),
                )
            else:
                result = raid_result(
                    attackers,
                    Fraction(attack_strength, attackers),
                    encountered,
                    defense_combativity,
                    max(0, target["tax"] - [200_000, 400_000, 800_000][target["shelter"]])
                    if state.get("economy_version", 1) >= 3
                    else target["stock"],
                    (lambda dead: carrying_capacity(mission, dead, priority))
                    if state.get("economy_version", 1) >= 3
                    else None,
                )
            lose_attackers(state, mission, result.attacker_losses, priority)
            lose_local_fideles(state, target, result.defender_losses)
            military_deaths(state, target["id"], result.defender_losses)
            seasonal = state.get("economy_version", 1) >= 3
            target["tax" if seasonal else "stock"] -= result.stolen + result.destroyed
            mission["loot"] = result.stolen
            won = result.outcome in ("success", "contested_win", "unopposed")
            scene_outcome = "success" if won else "failure"
            civilian_dead, damaged_work = (
                raid_aftermath(
                    state,
                    target,
                    attackers - result.attacker_losses,
                    encountered - result.defender_losses,
                    result,
                    draw,
                    relief_away=sum(
                        item["count"] for item in relief if item["origin"] == target["id"]
                    ),
                )
                if strategic
                else (0, None)
            )
            if strategic and (
                result.stolen + result.destroyed + result.defender_losses + civilian_dead > 0
                or damaged_work
            ):
                target["raid_protected_until"] = state["month"] + 3
            if (
                not strategic
                and result.outcome == "success"
                and (not seasonal or result.stolen + result.destroyed > 0)
            ):
                target["raid_protected_until"] = state["month"] + (3 if seasonal else 12)
            if strategic:
                audit["outcomes"][mission["id"]] = {
                    "kind": "raid",
                    "outcome": result.outcome,
                    "target": target["id"],
                    "attacker": actor,
                    "defender": defender,
                    "attacker_deaths": result.attacker_losses,
                    "defender_deaths": result.defender_losses,
                    "noncombat_deaths": civilian_dead,
                    "stolen": result.stolen,
                    "destroyed": result.destroyed,
                    "damaged_work": damaged_work,
                }
            report(
                events,
                actor,
                "battle",
                message(
                    "{p0} à {p1}",
                    p0=message("Pillage sans opposition")
                    if result.outcome == "unopposed"
                    else OUTCOME_LABELS[result.outcome],
                    p1=target["name"],
                ),
                raid_finances(
                    order["cost"],
                    [
                        (state["cities"][city_id]["name"], amount)
                        for city_id, amount in order["funding"].items()
                    ],
                    result.stolen,
                    settled=False,
                )
                + "\n\n"
                + message(
                    "La nouvelle de cette expédition nous est parvenue. {p0} ",
                    p0=military_losses(result.attacker_losses),
                )
                + (
                    message(
                        "Les survivants transportent {p0} Mesures vers leurs origines ; nous ne pourrons les engager avant leur retour. ",
                        p0=number(result.stolen),
                    )
                    if result.stolen
                    else message("Les survivants rentreront sans butin. ")
                )
                + observation(
                    encountered,
                    attackers - result.attacker_losses,
                    defender_equipment,
                    state.get("economy_version", 1),
                )
                + (
                    message(
                        " Nos survivants sont au nombre de {count}. ",
                        count=attackers - result.attacker_losses,
                    )
                    + observed_losses(result.defender_losses, attackers - result.attacker_losses)
                    + (
                        message(" Nos hommes ont incendié une partie des récoltes accessibles.")
                        if result.destroyed and attackers - result.attacker_losses >= 10
                        else ""
                    )
                    + (
                        message(
                            " Un ouvrage a été endommagé : {work}.",
                            work=ACTION_LABELS[damaged_work],
                        )
                        if damaged_work and attackers - result.attacker_losses >= 10
                        else ""
                    )
                    if strategic
                    else ""
                ),
                scene=f"offensive-raid-{scene_outcome}",
                city_id=target["id"] if strategic else None,
                observation=observation(
                    encountered,
                    attackers - result.attacker_losses,
                    defender_equipment,
                    state.get("economy_version", 1),
                )
                if strategic
                else None,
            )
            report(
                events,
                defender,
                "battle",
                message("Les villages de {p0} ont été attaqués", p0=target["name"]),
                message(
                    "Les assaillants portaient le sceau de {house}. ",
                    house=state["players"][actor]["name"],
                )
                + observation(
                    attackers,
                    encountered - result.defender_losses,
                    attacker_equipment,
                    state.get("economy_version", 1),
                )
                + " "
                + message(
                    "Le raid sur nos villages a coûté la vie à {p0} de nos Fidèles. Les assaillants ont emporté {p1} Mesures et en ont détruit {p2} autres. Ces pertes diminuent la récolte en préparation ; la production continue. "
                    if seasonal
                    else "Le raid sur nos villages a coûté la vie à {p0} de nos Fidèles. Les assaillants ont emporté {p1} Mesures et en ont détruit {p2} autres. Ces pertes sont inscrites dans le grenier de la cité. ",
                    p0=result.defender_losses,
                    p1=number(result.stolen),
                    p2=number(result.destroyed),
                )
                + (
                    message(
                        " Victimes parmi les habitants non engagés : {count}. ", count=civilian_dead
                    )
                    + message(
                        " Nos survivants sont au nombre de {count}. ",
                        count=encountered - result.defender_losses,
                    )
                    + observed_losses(result.attacker_losses, encountered - result.defender_losses)
                    + (
                        message(
                            " Un ouvrage a été endommagé : {work}. Il fonctionne au niveau inférieur jusqu’à sa réparation.",
                            work=ACTION_LABELS[damaged_work],
                        )
                        if damaged_work
                        else ""
                    )
                    if strategic
                    else ""
                ),
                scene=f"received-raid-{scene_outcome}",
                city_id=target["id"] if strategic else None,
            )
            continue
        support = [
            item
            for item in relief
            if item["mission"] == mission["id"] and item["actor"] == defender
        ]
        local = target["fideles"]
        encountered_equipment = {item["combativity"] for item in support}
        if local:
            encountered_equipment.add(defense_combativity)
        if encountered_equipment:
            defender_equipment = (
                "mixed"
                if len(encountered_equipment) > 1
                else equipment_values(state.get("economy_version", 1)).index(
                    next(iter(encountered_equipment))
                )
            )
        reinforcement = sum(item["count"] for item in support)
        relief_strength = sum(item["count"] * item["combativity"] for item in support)
        field = local * defense_combativity + relief_strength
        reduction = (
            siege_reduction(mission) if state.get("economy_version", 1) >= 3 else Fraction(0)
        )
        wall = wall_multiplier(
            target["walls"],
            target["damaged"],
            reduction,
            state.get("economy_version", 1),
            integrity=target.get("integrity", 100),
        )
        fortified = local * defense_combativity * wall + relief_strength
        exported = sum(item["count"] for item in relief if item["origin"] == target["id"])
        present_population = target["population"] - absent(state, target["id"]) - exported
        result = capture_result(
            rule_family(state["rules"]),
            attack_strength,
            field,
            fortified,
            target["stock"],
            present_population,
            economy_version=state.get("economy_version", 1),
        )
        attacker_dead = losses(attackers, result.attacker_rate)
        defender_dead = losses(local + reinforcement, result.defender_rate)
        lose_attackers(state, mission, attacker_dead, priority)
        weights = {target["id"]: local, **{item["origin"]: item["count"] for item in support}}
        split = allocate(defender_dead, weights, priority)
        lose_local_fideles(state, target, split[target["id"]])
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
        if strategic:
            audit["outcomes"][mission["id"]] = {
                "kind": "capture",
                "outcome": result.outcome,
                "target": target["id"],
                "attacker": actor,
                "defender": defender,
                "attacker_deaths": attacker_dead,
                "defender_deaths": defender_dead,
                "noncombat_deaths": civilian_dead,
                "food_used": result.food_used,
            }
            target["integrity"] = integrity_after_combat(
                target["integrity"], result.outcome, reduction
            )
            target["damaged"] = target["integrity"] != 100
        if result.captured:
            if strategic:
                detach_absent_contingents(state, target["id"])
            target["owner"] = actor
            if tactics.enabled(state):
                target["restricted_fideles"] = target["fideles"]
                target["restricted_until"] = state["month"] + 4
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
                    message("{p0} change de souverain", p0=target["name"]),
                    message(
                        "Le nom du souverain a changé dans les registres de {p0}. La cité relève désormais de {p1} ; c’est tout ce que cette nouvelle publique nous apprend.",
                        p0=target["name"],
                        p1=state["players"][actor]["name"],
                    ),
                )
        if strategic:
            for item in support:
                report(
                    events,
                    defender,
                    "battle",
                    message("Les secours de {city}", city=state["cities"][item["origin"]]["name"]),
                    message(
                        "À {target}, le contingent de {origin} a perdu {dead} Fidèles ; {survivors} ont survécu et restent attachés à votre maison.",
                        target=target["name"],
                        origin=state["cities"][item["origin"]]["name"],
                        dead=split[item["origin"]],
                        survivors=item["count"],
                    ),
                    city_id=item["origin"],
                )
        scene_outcome = "success" if result.captured else "failure"
        report(
            events,
            actor,
            "battle",
            message("{p0} à {p1}", p0=OUTCOME_LABELS[result.outcome], p1=target["name"]),
            message(
                "{p0} Les survivants repartent vers leurs origines ; ils y rejoindront les présents à la date annoncée. ",
                p0=military_losses(attacker_dead),
            )
            + observation(
                local + reinforcement,
                attackers - attacker_dead,
                defender_equipment,
                state.get("economy_version", 1),
            )
            + (
                message(
                    " Survivants : {survivors}. Coût payé : {cost} Mesures. ",
                    survivors=attackers - attacker_dead,
                    cost=number(order["cost"]),
                )
                + observed_losses(defender_dead, attackers - attacker_dead)
                if strategic
                else ""
            ),
            scene=f"offensive-capture-{scene_outcome}",
            city_id=target["id"] if strategic else None,
            observation=observation(
                local + reinforcement,
                attackers - attacker_dead,
                defender_equipment,
                state.get("economy_version", 1),
            )
            if strategic
            else None,
        )
        report(
            events,
            defender,
            "battle",
            message("La bataille de {p0}", p0=target["name"]),
            message(
                "Voici l’issue que l’on nous rapporte : {p0}. Nous avons perdu {p1} Fidèles engagés, dont {p2} de la garnison locale, ainsi que {p3} civils. ",
                p0=OUTCOME_LABELS[result.outcome].lower(),
                p1=defender_dead,
                p2=split[target["id"]],
                p3=civilian_dead,
            )
            + (
                message(
                    "Le siège a consommé {p0} Mesures prises dans le grenier de cette cité. ",
                    p0=number(result.food_used),
                )
                if result.outcome in ("held", "shortage")
                else ""
            )
            + observation(
                attackers,
                local + reinforcement - defender_dead,
                attacker_equipment,
                state.get("economy_version", 1),
            )
            + (
                message(
                    " Les assaillants portaient le sceau de {house}. ",
                    house=state["players"][actor]["name"],
                )
                + message(
                    " Nos survivants sont au nombre de {count}. ",
                    count=local + reinforcement - defender_dead,
                )
                + observed_losses(attacker_dead, local + reinforcement - defender_dead)
                if strategic
                else ""
            ),
            scene=f"received-capture-{scene_outcome}",
            city_id=target["id"] if strategic else None,
        )
    # Relief stays away throughout the whole phase, even after its battle.
    for item in relief:
        state["cities"][item["origin"]]["fideles"] += item["count"]
    return audit


def return_contingents(state, mission, events):
    """Settle each origin once, preserving detached people until actual arrival."""
    actor = mission["actor"]
    neighbours = {
        second if first == mission["target"] else first
        for first, second in state["links"]
        if mission["target"] in (first, second)
    }
    order = next(item for item in state["orders"] if item["id"] == mission["id"])
    if "loot_shares" not in mission:
        mission["loot_shares"] = allocate(mission["loot"], mission["cohorts"])
        mission["return_routes"] = {}
        mission["recovered_loot"] = 0
    diverted = False
    for origin, survivors in mission["cohorts"].items():
        if origin in mission["arrived_origins"]:
            continue
        city = state["cities"][origin]
        route = mission["return_routes"].get(origin)
        if route is None and city["owner"] != actor and survivors:
            refuge = next(
                (key for key in sorted(neighbours) if state["cities"][key]["owner"] == actor),
                None,
            )
            if refuge:
                mission["return_routes"][origin] = refuge
                diverted = True
                report(
                    events,
                    actor,
                    "return",
                    message("Le contingent cherche refuge"),
                    message(
                        "{count} Fidèles de {origin} se dirigent vers {refuge}. Leur arrivée est prévue à la lune {moon}.",
                        count=survivors,
                        origin=city["name"],
                        refuge=state["cities"][refuge]["name"],
                        moon=state["month"] + 1,
                    ),
                )
                continue
        destination = state["cities"][route] if route else city
        friendly = destination["owner"] == actor and (route is None or route in neighbours)
        if not friendly:
            destination = city
            friendly = destination["owner"] == actor
        if origin in mission["detached_origins"]:
            destination["population"] += survivors
        destination["fideles"] += survivors
        if (
            not friendly
            and tactics.enabled(state)
            and closing_moon(state) < destination.get("restricted_until", 0)
        ):
            destination["restricted_fideles"] = destination.get("restricted_fideles", 0) + survivors
        loot = mission["loot_shares"][origin]
        deposited = (
            min(loot, capacity(destination, state["economy_version"]) - destination["stock"])
            if friendly
            else 0
        )
        destination["stock"] += deposited
        mission["loot"] -= loot
        mission["recovered_loot"] += deposited
        mission["arrived_origins"].append(origin)
        report(
            events,
            actor,
            "return",
            message("Retour du contingent de {city}", city=city["name"]),
            message(
                "{count} survivants ont rejoint {city}. {fate} Butin conservé : {kept} Mesures ; perdu ou sans place : {lost}.",
                count=survivors,
                city=destination["name"],
                fate=message("Ils rejoignent les Fidèles de votre maison.")
                if friendly
                else message(
                    "Ils rejoignent les Fidèles du nouveau souverain et restent soumis à l’éventuelle restriction de départ de la cité."
                ),
                kept=number(deposited),
                lost=number(loot - deposited),
            ),
            city_id=destination["id"],
        )
    if diverted:
        mission["return_month"] = state["month"] + 1
        return
    if mission["kind"] == "raid":
        report(
            events,
            actor,
            "return",
            message("Le bilan du raid"),
            raid_finances(
                order["cost"],
                [
                    (state["cities"][origin]["name"], amount)
                    for origin, amount in order["funding"].items()
                ],
                mission["recovered_loot"],
                settled=True,
            ),
        )
    mission["loot"] = 0
    mission["status"] = order["status"] = "completed"


def return_expeditions(state, events):
    for mission in state["expeditions"]:
        if mission["status"] == "completed" or mission["return_month"] > state["month"]:
            continue
        if state.get("economy_version", 1) >= 4:
            return_contingents(state, mission, events)
            continue
        shares = allocate(mission["loot"], mission["cohorts"])
        order = next(item for item in state["orders"] if item["id"] == mission["id"])
        accounts = {}
        recovered = 0
        for city_id, survivors in mission["cohorts"].items():
            city = state["cities"][city_id]
            city["fideles"] += survivors
            deposited = min(
                shares[city_id], capacity(city, state.get("economy_version", 1)) - city["stock"]
            )
            city["stock"] += deposited
            if city["owner"] == mission["actor"]:
                recovered += deposited
            if survivors:
                account = message(
                    "J’ai fait inscrire le retour de {p0} Fidèles à {p1}. Ils rejoignent les présents de leur cité d’origine. {p2}",
                    p0=survivors,
                    p1=city["name"],
                    p2=returned_loot(deposited, shares[city_id] - deposited),
                )
                recipient = city["owner"]
                if recipient in accounts:
                    accounts[recipient]["title"] = message("Les contingents sont rentrés")
                    accounts[recipient]["body"] += "\n\n" + account
                else:
                    accounts[recipient] = {
                        "title": message("Retour à {p0}", p0=city["name"]),
                        "body": account,
                    }
        if not sum(mission["cohorts"].values()):
            accounts[mission["actor"]] = {
                "title": message("Une expédition ne reviendra pas"),
                "body": message("Aucun homme n’a survécu. Aucun butin n’est déposé."),
            }
        if mission["kind"] == "raid":
            account = accounts.setdefault(
                mission["actor"],
                {
                    "title": message("Le bilan du raid"),
                    "body": message(
                        "Les survivants ont rejoint des cités qui ne relèvent plus de votre maison."
                    ),
                },
            )
            account["body"] = (
                raid_finances(
                    order["cost"],
                    [
                        (state["cities"][city_id]["name"], amount)
                        for city_id, amount in order["funding"].items()
                    ],
                    recovered,
                    settled=True,
                )
                + "\n\n"
                + account["body"]
            )
        for recipient, account in accounts.items():
            report(events, recipient, "return", account["title"], account["body"])
        mission["loot"] = 0
        mission["status"] = "completed"
        order["status"] = "completed"


def displaced_population(state, actor):
    return sum(
        count
        for mission in state["expeditions"]
        if mission["actor"] == actor and mission["status"] != "completed"
        for origin, count in mission["cohorts"].items()
        if origin in mission.get("detached_origins", [])
        and origin not in mission.get("arrived_origins", [])
    )


def standings(state):
    rows = [
        {
            "actor": actor,
            "name": player["name"],
            "cities": len(owned_cities(state, actor)),
            "population": sum(city["population"] for city in owned_cities(state, actor))
            + displaced_population(state, actor),
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
                message("Votre prétention au trône s’achève"),
                message(
                    "Vous ne possédez plus de cité. Vos armées encore en route rentrent vers leurs origines."
                ),
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
                message("Le règne est achevé"),
                message(
                    "Au premier rang : {p0}. Les opérations encore en route ne modifieront plus ce résultat.",
                    p0=winners,
                ),
            )


def assert_invariants(state):
    funds, people = reservations(state)
    for city_id, city in state["cities"].items():
        assert (
            0 <= funds[city_id] <= city["stock"] <= capacity(city, state.get("economy_version", 1))
        ), ("stock", city_id)
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
    assert tactics.enabled(state) or len(active) == len(set(active)), "Duplicate target engagement"
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
        raise RuleError(message("Ce règne est déjà terminé."))
    if not open_calendar(state):
        state["month"] += 1
    events = []
    annual_economy(state, events)
    depart_orders(state, events)
    finish_works(state, events)
    if tactics.enabled(state):
        detect_departures(state, events)
    audit = resolve_combats(state, seed, events)
    if state.get("economy_version", 1) >= 3 and state["month"] % 12 == 0:
        for city in state["cities"].values():
            harvest_city(state, city, events)
    return_expeditions(state, events)
    return_convoys(state, events)
    check_end(state, events)
    if open_calendar(state) and state["status"] == "active":
        state["month"] += 1
    assert_invariants(state)
    return events, audit


def bot_orders(state, seed):
    """A modest policy using owned state and public geography, never enemy stocks/men."""
    decision_month = closed_moon(state)
    accepted = []
    for actor, player in state["players"].items():
        if not player["bot"] or player["eliminated"]:
            continue
        rng = random_stream(seed, decision_month, f"bot:{actor}")
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
                capture_price = expedition_prices(state.get("economy_version", 1))["capture"]
                budget = max(0, (wealth - capture_price["base"]) // capture_price["per_person"])
                total = min(240, budget, sum(contributions.values()))
                if total >= 150:
                    contributions = allocate(total, contributions)
                    proposals.append(
                        {"kind": "capture", "target": target, "contributions": contributions}
                    )
        if decision_month % 3 == 0:
            for city in cities:
                proposals.append({"kind": "irrigation", "cities": [city["id"]]})
        if decision_month % 4 == 1:
            for city in cities:
                if city["walls"] == 0:
                    proposals.append({"kind": "walls", "cities": [city["id"]]})
        if rule_family(state["rules"]).storage and wealth > 4_000_000:
            if local_forges(state):
                proposals.extend({"kind": "forge", "cities": [city["id"]]} for city in cities)
            else:
                proposals.append({"kind": "equipment"})
            for city in cities:
                proposals.append({"kind": "storage", "cities": [city["id"]]})
        if decision_month % 5 == 2:
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
        if state.get("economy_version", 1) >= 3:
            # Seasonal decisions use only the calendar, own accounts and public walls.
            proposals = [spec for spec in proposals if spec["kind"] != "raid"]
            if decision_month % 12 in (4, 7, 10):
                for target in targets:
                    eligible = eligible_origins(state, actor, target)
                    for city in cities:
                        if city["id"] in eligible and city["fideles"] - people[city["id"]] >= 45:
                            proposals.insert(
                                0,
                                {
                                    "kind": "raid",
                                    "target": target,
                                    "contributions": {city["id"]: 45},
                                },
                            )
                            break
            preferences = (
                ("forge", "watch", "transport", "siege", "shelter", "storage")
                if actor == "p2"
                else (
                    "irrigation",
                    "shelter",
                    "walls",
                    "watch",
                    "forge",
                    "storage",
                    "transport",
                    "siege",
                )
            )
            proposals.extend(
                {"kind": kind, "cities": [city["id"]]} for kind in preferences for city in cities
            )
            proposals.sort(key=lambda spec: spec["kind"] != "capture")
        for spec in proposals:
            try:
                if state.get("economy_version", 1) >= 3 and spec["kind"] in work_prices(3):
                    quote = work_spec(state, state["cities"][spec["cities"][0]], spec["kind"])
                    city_id = quote["city"]
                    if state["cities"][city_id]["stock"] - funds[city_id] - quote["cost"] < 100_000:
                        continue
                order = confirm_order(state, actor, spec, f"bot-{actor}-{decision_month}")
            except RuleError:
                continue
            accepted.append(order)
            break
    return accepted
