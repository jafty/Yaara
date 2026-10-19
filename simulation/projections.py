"""Explicit allowlists of player-visible fields. Never serialize the aggregate."""

from . import engine
from .calendar import closed_moon, closing_moon
from .messages import Message
from .narration import WORK_ADVICE, WORK_PURPOSES, work_benefit, work_effect, work_name
from .rules import (
    ACTION_LABELS,
    EQUIPMENT_LABELS,
    EXPEDITION_PRICES,
    RuleError,
    rule_family,
    tax_yield,
)

STATUS_LABELS = {
    "confirmed": Message("Confirmé"),
    "active": Message("En cours"),
    "returning": Message("Au retour"),
    "completed": Message("Achevé"),
    "cancelled": Message("Annulé"),
    "invalidated": Message("Invalidé"),
}

# Public schematic geography; ownership and road topology never move settlements.
ATLAS_POSITIONS = (
    (115, 90),
    (305, 120),
    (520, 80),
    (165, 240),
    (400, 225),
    (570, 270),
    (95, 385),
    (305, 375),
    (500, 415),
)


# Fixed clipped Voronoi cells; borders are illustrative, never road adjacency.
ATLAS_TERRITORIES = (
    "0.0,0.0 226.6,0.0 203.9,143.7 0.0,211.7",
    "226.6,0.0 393.9,0.0 415.4,115.6 282.7,235.7 203.9,143.7",
    "393.9,0.0 680.0,0.0 680.0,139.5 501.1,186.5 415.4,115.6",
    "0.0,249.7 0.0,211.7 203.9,143.7 282.7,235.7 284.0,256.6 198.4,345.5",
    "284.0,256.6 282.7,235.7 415.4,115.6 501.1,186.5 468.4,310.3 414.0,338.9",
    "680.0,139.5 680.0,412.5 468.4,310.3 501.1,186.5",
    "205.7,500.0 0.0,500.0 0.0,249.7 198.4,345.5",
    "381.0,500.0 205.7,500.0 198.4,345.5 284.0,256.6 414.0,338.9",
    "680.0,412.5 680.0,500.0 381.0,500.0 414.0,338.9 468.4,310.3",
)


def player_view(state, actor):
    closed = closed_moon(state)
    upcoming = closing_moon(state)
    dating = max(1, closed if state["status"] == "finished" else upcoming)
    funds, people = engine.reservations(state)
    targets = engine.active_targets(state)
    busy = engine.busy_cities(state)
    cities = []
    for index, city in enumerate(state["cities"].values()):
        public = {
            "id": city["id"],
            "name": city["name"],
            "owner": city["owner"],
            "owner_name": state["players"][city["owner"]]["name"],
            "owned": city["owner"] == actor,
            "walls": city["walls"],
            "wall_label": [
                Message("Sans enceinte"),
                Message("Enceinte de terre"),
                Message("Grande enceinte"),
            ][city["walls"]],
            "damaged": city["damaged"],
            "engaged": city["id"] in targets,
            "own_engagement": any(
                order["id"] == targets.get(city["id"]) and order["actor"] == actor
                for order in state["orders"]
            ),
            "x": ATLAS_POSITIONS[index][0],
            "y": ATLAS_POSITIONS[index][1],
            "territory": ATLAS_TERRITORIES[index],
        }
        if public["owned"]:
            away = engine.absent(state, city["id"])
            public.update(
                {
                    "population": city["population"],
                    "present_population": city["population"] - away,
                    "fideles": city["fideles"],
                    "absent": away,
                    "available_fideles": city["fideles"] - people[city["id"]],
                    "reserved_fideles": people[city["id"]],
                    "stock": city["stock"],
                    "capacity": engine.capacity(city),
                    "available_stock": city["stock"] - funds[city["id"]],
                    "reserved_stock": funds[city["id"]],
                    "stock_percent": round(city["stock"] / engine.capacity(city) * 100),
                    "tax": city["tax"],
                    "yield": tax_yield(city["irrigation"], state.get("economy_version", 1)),
                    "irrigation": city["irrigation"],
                    "storage": city["storage"],
                    "forge": city.get("forge", 0),
                    "forge_name": work_name("forge", engine.city_equipment(state, city)),
                    "equipment": EQUIPMENT_LABELS[engine.city_equipment(state, city)],
                    "busy": city["id"] in busy,
                    "deaths": city["military_deaths"] + city["civilian_deaths"],
                    "works": [
                        {
                            "label": ACTION_LABELS[work["kind"]],
                            "name": work_name(work["kind"], work["level"]),
                            "finish_month": work["finish_month"],
                            "start_month": work["start_month"],
                            "progress": min(
                                100,
                                round((closed - work["start_month"]) / work["duration"] * 100),
                            ),
                        }
                        for work in state["works"]
                        if work.get("city") == city["id"] and work["status"] == "active"
                    ],
                }
            )
        cities.append(public)
    by_id = {city["id"]: city for city in cities}
    owned = [city for city in cities if city["owned"]]
    orders = []
    for order in reversed(state["orders"]):
        if order["actor"] != actor:
            continue
        orders.append(
            {
                "id": order["id"],
                "label": ACTION_LABELS[order["kind"]],
                "kind": order["kind"],
                "status": order["status"],
                "status_label": STATUS_LABELS[order["status"]],
                "cost": order["cost"],
                "execute_month": order["execute_month"],
                "executed_month": order.get("executed_month", order["execute_month"]),
                "cancelled_month": order.get("cancelled_month"),
                "finish_month": max(
                    (
                        work["finish_month"]
                        for work in state["works"]
                        if work["order_id"] == order["id"]
                    ),
                    default=None,
                ),
                "can_cancel": rule_family(state["rules"]).cancellable
                and order["status"] == "confirmed",
                "destination": by_id[order["target"]]["name"]
                if order.get("target")
                else ", ".join(by_id[task["city"]]["name"] for task in order["tasks"])
                or Message("Toutes vos possessions"),
                "men": sum(order.get("contributions", {}).values()),
            }
        )
    missions = [
        {
            "kind": ACTION_LABELS[mission["kind"]],
            "target": by_id[mission["target"]]["name"],
            "men": sum(mission["cohorts"].values()),
            "combat_month": mission["combat_month"],
            "return_month": mission["return_month"],
            "loot": mission["loot"],
            "returning": mission["status"] == "returning",
        }
        for mission in state["expeditions"]
        if mission["actor"] == actor and mission["status"] != "completed"
    ]
    attack_targets = []
    for city in cities:
        eligible = engine.eligible_origins(state, actor, city["id"])
        city["reachable"] = bool(eligible)
        if eligible:
            attack_targets.append(
                {
                    "id": city["id"],
                    "name": city["name"],
                    "owner_name": city["owner_name"],
                    "engaged": city["engaged"],
                    "origins": sorted(eligible),
                }
            )
    ranking = [
        {
            "actor": row["actor"],
            "name": row["name"],
            "cities": row["cities"],
            "rank": row["rank"],
            "own": row["actor"] == actor,
        }
        for row in (state["result"]["standings"] if state["result"] else engine.standings(state))
    ]
    available_actions = []
    for kind in ("irrigation", "storage", "walls", "repair", "forge"):
        if kind == "forge" and (
            not engine.local_forges(state) or not rule_family(state["rules"]).equipment
        ):
            continue
        if kind in ("storage", "repair") and not rule_family(state["rules"]).storage:
            continue
        options = []
        for city in engine.owned_cities(state, actor):
            current = city["walls"] if kind == "repair" else city[kind]
            option = {
                "id": city["id"],
                "name": city["name"],
                "current_name": work_name(kind, current),
                "current_damaged": kind in ("walls", "repair") and city["damaged"],
                "work_name": "",
                "cost": 0,
                "duration": 0,
                "level": current,
                "busy": city["id"] in busy,
                "available_stock": by_id[city["id"]]["available_stock"],
                "shortfall": 0,
                "available": False,
                "benefit": "",
                "reason": "",
            }
            try:
                task = engine.work_spec(state, city, kind)
            except RuleError as error:
                complete = current == rule_family(state["rules"]).max_level and kind != "repair"
                reason = error.args[0]
                if complete:
                    reason = Message("Cet ouvrage est achevé.")
                elif kind == "repair" and not current:
                    reason = Message("Cette cité n’a pas d’enceinte à réparer.")
                option.update(status="completed" if complete else "unavailable", reason=reason)
            else:
                option.update(
                    cost=task["cost"],
                    duration=task["duration"],
                    level=task["level"],
                    work_name=work_name(kind, task["level"]),
                    benefit=work_benefit(
                        kind, current, task["level"], state.get("economy_version", 1)
                    ),
                    available=not option["busy"],
                    status="busy" if option["busy"] else "available",
                    shortfall=max(0, task["cost"] - option["available_stock"]),
                )
                if option["busy"]:
                    active_works = by_id[city["id"]]["works"]
                    option["reason"] = (
                        Message(
                            "Chantier en cours : {work}, jusqu’à la lune {moon}.",
                            work=active_works[0]["name"],
                            moon=active_works[0]["finish_month"],
                        )
                        if active_works
                        else Message("Un décret scellé réserve déjà ces équipes.")
                    )
            options.append(option)
        prices = sorted(
            {
                (city["level"], city["cost"], city["duration"])
                for city in options
                if city["work_name"]
            }
        )
        available_actions.append(
            {
                "kind": kind,
                "label": ACTION_LABELS[kind],
                "cities": options,
                "selectable": any(city["available"] for city in options),
                "purpose": WORK_PURPOSES[kind],
                "advice": WORK_ADVICE[kind],
                "prices": [
                    {
                        "level": level,
                        "name": work_name(kind, level),
                        "cost": cost,
                        "duration": duration,
                        "effect": work_effect(kind, level, state.get("economy_version", 1)),
                    }
                    for level, cost, duration in prices
                ],
            }
        )
    equipment_quote = {}
    if (
        not engine.local_forges(state)
        and rule_family(state["rules"]).equipment
        and state["players"][actor]["equipment"] < 2
    ):
        equipment_quote = engine.equipment_spec(state, actor)
    equipment_available = bool(equipment_quote) and not engine.equipment_busy(state, actor)
    if not engine.local_forges(state) and rule_family(state["rules"]).equipment:
        available_actions.append(
            {
                "kind": "equipment",
                "label": ACTION_LABELS["forge"],
                "purpose": WORK_PURPOSES["equipment"],
                "advice": WORK_ADVICE["equipment"],
                "equipment": EQUIPMENT_LABELS[state["players"][actor]["equipment"]],
                "benefit": work_benefit(
                    "forge", state["players"][actor]["equipment"], equipment_quote["level"]
                )
                if equipment_quote
                else "",
                "selectable": equipment_available,
                "prices": [
                    {**equipment_quote, "name": work_name("forge", equipment_quote["level"])}
                ]
                if equipment_quote
                else [],
            }
        )
    return {
        "month": state["month"],
        "open_moon": upcoming,
        "closed_moon": closed,
        "year": (dating - 1) // 12 + 1,
        "year_month": (dating - 1) % 12 + 1,
        "reign_months": state["config"]["reign_months"],
        "remaining": state["config"]["reign_months"] - closed,
        "rules": state["rules"],
        "finished": state["status"] == "finished",
        "eliminated": state["players"][actor]["eliminated"],
        "actor": actor,
        "realm": state["players"][actor]["name"],
        "equipment": EQUIPMENT_LABELS[state["players"][actor]["equipment"]],
        "local_forges": engine.local_forges(state),
        "local_funding": state.get("economy_version", 1) >= 2,
        "equipment_quote": equipment_quote,
        "equipment_shortfall": max(
            0, equipment_quote.get("cost", 0) - sum(city["available_stock"] for city in owned)
        ),
        "equipment_available": equipment_available,
        "equipment_work": [
            {"finish_month": work["finish_month"]}
            for work in state["works"]
            if work["kind"] == "equipment" and work["actor"] == actor and work["status"] == "active"
        ],
        "cities": cities,
        "owned_cities": owned,
        "links": [
            {"first": by_id[first], "second": by_id[second]} for first, second in state["links"]
        ],
        "stock": sum(city["stock"] for city in owned),
        "available_stock": sum(city["available_stock"] for city in owned),
        "reserved_stock": sum(city["reserved_stock"] for city in owned),
        "capacity": sum(city["capacity"] for city in owned),
        "population": sum(city["population"] for city in owned),
        "available_fideles": sum(city["available_fideles"] for city in owned),
        "absent": sum(city["absent"] for city in owned),
        "tax": sum(city["tax"] for city in owned),
        "harvest_in": 12 - closed % 12,
        "harvest_moon": closed + 12 - closed % 12,
        "sealed_count": sum(order["status"] == "confirmed" for order in orders),
        "orders": orders,
        "missions": missions,
        "ranking": ranking,
        "attack_targets": attack_targets,
        "work_actions": available_actions,
        "cancellable": rule_family(state["rules"]).cancellable,
        "raid_minimum": state["config"]["raid_minimum"],
        "capture_minimum": state["config"]["capture_minimum"],
        "expedition_prices": {
            kind: {**prices, "minimum": state["config"][f"{kind}_minimum"]}
            for kind, prices in EXPEDITION_PRICES.items()
        },
        "epilogue_missions": state["result"]["expeditions_in_transit"] if state["result"] else 0,
    }
