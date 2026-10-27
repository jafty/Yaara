"""Map and courrier presentation, exclusively from authorized player projections.

This module formats existing decisions; it never quotes, validates or executes an order.
"""

from math import ceil, hypot, pi, sin
from urllib.parse import urlencode

from django.utils.translation import gettext as _

from .alerts import build_alert_center

MAP_POSITIONS = (
    (135, 220),
    (90, 75),
    (275, 120),
    (440, 70),
    (590, 185),
    (515, 300),
    (445, 390),
    (260, 435),
    (125, 360),
)
MAP_TERRITORIES = (
    "0.00,280.71 0.00,182.41 175.06,128.08 282.29,278.20 247.56,298.40",
    "0.00,0.00 206.22,0.00 175.06,128.08 0.00,182.41",
    "206.22,0.00 328.71,0.00 393.11,212.52 362.37,253.51 320.27,280.01 282.29,278.20 175.06,128.08",
    "328.71,0.00 612.75,0.00 468.72,187.86 393.11,212.52",
    "612.75,0.00 680.00,0.00 680.00,325.65 468.72,187.86",
    "680.00,325.65 680.00,500.00 679.29,500.00 362.37,253.51 393.11,212.52 468.72,187.86",
    "679.29,500.00 373.78,500.00 320.27,280.01 362.37,253.51",
    "373.78,500.00 135.56,500.00 247.56,298.40 282.29,278.20 320.27,280.01",
    "135.56,500.00 0.00,500.00 0.00,280.71 247.56,298.40",
)


def territory_path(polygon):
    """Shared edges use the same irregular ink contour, traversed in either direction."""
    points = [tuple(map(float, pair.split(","))) for pair in polygon.split()]
    path = [f"M {points[0][0]:.2f} {points[0][1]:.2f}"]
    for start, end in zip(points, points[1:] + points[:1]):
        first, last = sorted((start, end))
        dx, dy = last[0] - first[0], last[1] - first[1]
        length = hypot(dx, dy)
        frame = (dx == 0 and first[0] in (0, 680)) or (dy == 0 and first[1] in (0, 500))
        count = max(2, ceil(length / 42))
        amplitude = 0 if frame else min(15, length * 0.09)
        phase = (first[0] + last[1]) * 0.04
        knots = []
        for index in range(count + 1):
            t = index / count
            bend = amplitude * sin(pi * t) * sin(2.5 * pi * t + phase)
            knots.append(
                (
                    first[0] + dx * t - dy / max(length, 1) * bend,
                    first[1] + dy * t + dx / max(length, 1) * bend,
                )
            )
        if start != first:
            knots.reverse()
        for index in range(count):
            before, here = knots[max(0, index - 1)], knots[index]
            after, beyond = knots[index + 1], knots[min(count, index + 2)]
            controls = [
                tuple(here[axis] + (after[axis] - before[axis]) / 6 for axis in (0, 1)),
                tuple(after[axis] - (beyond[axis] - here[axis]) / 6 for axis in (0, 1)),
            ]
            path.append("C " + " ".join(f"{x:.2f} {y:.2f}" for x, y in [*controls, after]))
    return " ".join(path) + " Z"


def workspace_context(view, selected=None, activity=None):
    cities = {city["id"]: city for city in view["cities"]}
    owned = {city["id"] for city in view["owned_cities"]}
    work_kinds = {action["kind"] for action in view["work_actions"]}
    for index, city in enumerate(view["cities"]):
        city["x"], city["y"] = MAP_POSITIONS[index]
        city["territory"] = MAP_TERRITORIES[index]
        tile = city["walls"] if view["seasonal_raids"] else (0, 4, 5)[city["walls"]]
        city["settlement_viewbox"] = f"{tile % 3 * 512} {tile // 3 * 512} 512 512"
        city["territory_path"] = territory_path(city["territory"])
        query = {"tab": "map", "city": city["id"]}
        if city["owned"] and activity in work_kinds | {"works", "accounts"}:
            query["action"] = activity
        city["map_query"] = urlencode(query)
    for link in view["links"]:
        link["first"] = cities[link["first"]["id"]]
        link["second"] = cities[link["second"]["id"]]
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
