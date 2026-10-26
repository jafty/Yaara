"""Map and courrier presentation, exclusively from authorized player projections.

This module formats existing decisions; it never quotes, validates or executes an order.
"""

from math import hypot
from urllib.parse import urlencode

from django.utils.translation import gettext as _

from .alerts import build_alert_center


def workspace_context(view, selected=None, activity=None):
    cities = {city["id"]: city for city in view["cities"]}
    owned = {city["id"] for city in view["owned_cities"]}
    work_kinds = {action["kind"] for action in view["work_actions"]}
    for city in view["cities"]:
        query = {"tab": "map", "city": city["id"]}
        if city["owned"] and activity in work_kinds | {"works", "accounts"}:
            query["action"] = activity
        city["map_query"] = urlencode(query)
    marches = []
    for item in view["orders"]:
        if item["status"] != "confirmed" or item["kind"] not in ("raid", "capture"):
            continue
        origin = item["launch_city"]
        if origin:
            marches.append(
                {
                    "origin": cities[origin],
                    "target": cities[item["target_id"]],
                    "state": "sealed",
                    "anchor": "order-" + item["id"],
                    "label": _("Ordre scellé"),
                    "moon": item["execute_month"],
                }
            )
    for item in view["missions"]:
        origins = item["origins"] if item["returning"] else [item["launch_city"]]
        for origin in origins:
            if origin:
                marches.append(
                    {
                        "origin": cities[item["target_id"]]
                        if item["returning"]
                        else cities[origin],
                        "target": cities[origin]
                        if item["returning"]
                        else cities[item["target_id"]],
                        "state": "returning" if item["returning"] else "outbound",
                        "anchor": "mission-" + item["id"],
                        "label": _("Retour prévu") if item["returning"] else _("Arrivée prévue"),
                        "moon": item["return_month"] if item["returning"] else item["combat_month"],
                    }
                )
    for march in marches:
        origin, target = march["origin"], march["target"]
        dx, dy = target["x"] - origin["x"], target["y"] - origin["y"]
        distance = hypot(dx, dy)
        inset = min(45, distance / 4) / max(distance, 1)
        march["path"] = (
            f"M {origin['x'] + dx * inset:.2f} {origin['y'] + dy * inset:.2f} "
            f"L {target['x'] - dx * inset:.2f} {target['y'] - dy * inset:.2f}"
        )
    attention = build_alert_center(view)
    attention["items"] = [
        item
        for item in attention["items"]
        if item["kind"] != "damage" or item["repair_phase"] == "none"
    ]
    for item in attention["items"]:
        if item["kind"] == "damage":
            item["query"] = item["query"].replace("tab=constructions", "tab=map")
            item["scene"] = item["family"]
        else:
            item["scene"] = "army" if item["kind"] == "threat" else "storage"
    if not view["finished"]:
        for city in view["owned_cities"]:
            if city["forecast_overflow"]:
                attention["items"].append(
                    {
                        "kind": "overflow",
                        "city_id": city["id"],
                        "city_name": city["name"],
                        "missing": city["forecast_overflow"],
                        "moon": view["harvest_moon"],
                        "scene": "harvest",
                    }
                )
    attention["count"] = len(attention["items"])
    local_actions = []
    if selected and selected["owned"]:
        for action in view["work_actions"]:
            option = next((c for c in action.get("cities", []) if c["id"] == selected["id"]), None)
            if option and (not action.get("repair") or option.get("current_damaged")):
                local_actions.append({**action, "option": option})
    return {
        "marches": marches,
        "attention": attention,
        "local_actions": local_actions,
        "map_graph": {
            "owned": sorted(owned),
            "cities": [{"id": c["id"], "x": c["x"], "y": c["y"]} for c in cities.values()],
            "links": [[e["first"]["id"], e["second"]["id"]] for e in view["links"]],
        },
    }


def schedule(view):
    """Dated commitments link to immutable identities or a precise local account."""
    if view["finished"]:
        return []
    events = []
    for order in view["orders"]:
        if order["status"] == "confirmed":
            events.append(
                {
                    "moon": order["execute_month"],
                    "label": order["label"],
                    "detail": order["destination"],
                    "anchor": "order-" + order["id"],
                }
            )
    for city in view["owned_cities"]:
        for index, work in enumerate(city["works"]):
            events.append(
                {
                    "moon": work["finish_month"],
                    "label": work["label"],
                    "detail": city["name"],
                    "anchor": f"work-{city['id']}-{index}",
                }
            )
    for index, work in enumerate(view["equipment_work"]):
        events.append(
            {
                "moon": work["finish_month"],
                "label": _("Armement achevé"),
                "detail": view["realm"],
                "anchor": f"equipment-{index}",
            }
        )
    for mission in view["missions"]:
        if not mission["returning"]:
            events.append(
                {
                    "moon": mission["combat_month"],
                    "label": _("Arrivée prévue"),
                    "detail": mission["target"],
                    "anchor": "mission-" + mission["id"],
                }
            )
        events.append(
            {
                "moon": mission["return_month"],
                "label": _("Retour prévu"),
                "detail": mission["target"],
                "anchor": "mission-" + mission["id"],
            }
        )
    for index, convoy in enumerate(view["convoys"]):
        events.append(
            {
                "moon": convoy["arrival_moon"],
                "label": _("Acheminer des ressources"),
                "detail": convoy["target"],
                "anchor": f"convoy-{index}",
            }
        )
    events.append(
        {
            "moon": view["harvest_moon"],
            "label": _("Versement de la récolte"),
            "detail": "",
            "anchor": "harvest-accounts",
        }
    )
    return sorted(events, key=lambda event: event["moon"])
