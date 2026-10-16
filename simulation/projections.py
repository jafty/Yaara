"""Explicit allowlists of player-visible fields. Never serialize the aggregate."""

import math

from . import engine
from .messages import message
from .rules import ACTION_LABELS, EQUIPMENT_LABELS, RuleError, rule_family

STATUS_LABELS = {
    "confirmed": message("Confirmé"),
    "active": message("En cours"),
    "returning": message("Au retour"),
    "completed": message("Achevé"),
    "cancelled": message("Annulé"),
    "invalidated": message("Invalidé"),
}


def player_view(state, actor):
    funds, people = engine.reservations(state)
    targets = engine.active_targets(state)
    busy = engine.busy_cities(state)
    cities = []
    for index, city in enumerate(state["cities"].values()):
        angle = math.radians(index * 40 - 130)
        public = {
            "id": city["id"],
            "name": city["name"],
            "owner": city["owner"],
            "owner_name": state["players"][city["owner"]]["name"],
            "owned": city["owner"] == actor,
            "walls": city["walls"],
            "wall_label": [
                message("Sans enceinte"),
                message("Enceinte de terre"),
                message("Grande enceinte"),
            ][city["walls"]],
            "damaged": city["damaged"],
            "engaged": city["id"] in targets,
            "x": round(340 + 244 * math.cos(angle), 1),
            "y": round(225 + 154 * math.sin(angle), 1),
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
                    "yield": 100 + 100 * city["irrigation"],
                    "irrigation": city["irrigation"],
                    "storage": city["storage"],
                    "busy": city["id"] in busy,
                    "deaths": city["military_deaths"] + city["civilian_deaths"],
                    "works": [
                        {
                            "label": ACTION_LABELS[work["kind"]],
                            "finish_month": work["finish_month"],
                            "start_month": work["start_month"],
                            "progress": min(
                                100,
                                round(
                                    (state["month"] - work["start_month"]) / work["duration"] * 100
                                ),
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
                "can_cancel": rule_family(state["rules"]).cancellable
                and order["status"] == "confirmed",
                "destination": by_id[order["target"]]["name"]
                if order.get("target")
                else ", ".join(by_id[task["city"]]["name"] for task in order["tasks"])
                or message("Toutes vos possessions"),
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
    for kind in ("irrigation", "storage", "walls", "repair"):
        if kind in ("storage", "repair") and not rule_family(state["rules"]).storage:
            continue
        options = []
        for city in engine.owned_cities(state, actor):
            try:
                task = engine.work_spec(state, city, kind)
                options.append(
                    {
                        "id": city["id"],
                        "name": city["name"],
                        "cost": task["cost"],
                        "duration": task["duration"],
                        "level": task["level"],
                        "busy": city["id"] in busy,
                    }
                )
            except RuleError:
                continue
        available_actions.append({"kind": kind, "label": ACTION_LABELS[kind], "cities": options})
    return {
        "month": state["month"],
        "year": max(0, state["month"] - (state["status"] == "finished")) // 12 + 1,
        "year_month": max(0, state["month"] - (state["status"] == "finished")) % 12 + 1,
        "reign_months": state["config"]["reign_months"],
        "remaining": state["config"]["reign_months"] - state["month"],
        "rules": state["rules"],
        "finished": state["status"] == "finished",
        "eliminated": state["players"][actor]["eliminated"],
        "actor": actor,
        "realm": state["players"][actor]["name"],
        "equipment": EQUIPMENT_LABELS[state["players"][actor]["equipment"]],
        "equipment_available": rule_family(state["rules"]).equipment
        and state["players"][actor]["equipment"] < 2
        and not engine.equipment_busy(state, actor),
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
        "harvest_in": 12 - state["month"] % 12,
        "orders": orders,
        "missions": missions,
        "ranking": ranking,
        "attack_targets": attack_targets,
        "work_actions": available_actions,
        "cancellable": rule_family(state["rules"]).cancellable,
        "epilogue_missions": state["result"]["expeditions_in_transit"] if state["result"] else 0,
    }
