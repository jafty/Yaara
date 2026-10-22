"""Actionable display alerts from the existing, authorized player projection."""

from urllib.parse import urlencode

from django import template

from simulation.presentation import localize
from simulation.rules import ACTION_LABELS

register = template.Library()


@register.simple_tag
def build_alert_center(view):
    threats, damage, reserves = [], [], []
    if view and not view["finished"]:
        available_kinds = {action["kind"] for action in view["work_actions"]}
        for city in view["owned_cities"]:
            common = {"city_id": city["id"], "city_name": city["name"]}
            if city["engaged"] and not city["own_engagement"]:
                threats.append({**common, "kind": "threat"})
            buildings = city["buildings"] or [
                {"kind": "walls", "name": city["wall_label"], "damaged": city["damaged"]}
            ]
            for building in buildings:
                if not building["damaged"]:
                    continue
                repair = {
                    "walls": "repair",
                    "watch": "repair_watch",
                    "shelter": "repair_shelter",
                }.get(building["kind"])
                repair_label = localize(ACTION_LABELS[repair]) if repair else None
                phase = "none"
                if repair_label in city["team_tasks"]:
                    phase = (
                        "active"
                        if any(work["label"] == repair_label for work in city["works"])
                        else "reserved"
                    )
                query = (
                    urlencode({"tab": "constructions", "action": repair, "city": city["id"]})
                    if repair in available_kinds
                    else urlencode({"tab": "city", "city": city["id"]})
                )
                damage.append(
                    {
                        **common,
                        "kind": "damage",
                        "building": building["name"],
                        "family": building["kind"],
                        "repair_phase": phase,
                        "finish_moon": city["team_free_moon"] if phase != "none" else None,
                        "query": query,
                    }
                )
            if view["rules"] == "V1" and city["siege_shortfall"]:
                reserves.append({**common, "kind": "reserves", "missing": city["siege_shortfall"]})
    items = threats + damage + reserves
    return {
        "items": items,
        "count": len(items),
        "urgent": bool(threats),
        "damage_count": len(damage),
        "threat_count": len(threats),
    }
