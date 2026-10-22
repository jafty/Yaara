"""Request-locale rendering of already authorized, recipient-specific data."""

from django.utils.translation import get_language

from .messages import describe, render
from .messages import localize as localize_message
from .narration import STARTED_ACTION_PHRASES

ACTION_START_SCENES = {
    "raid": "start-army",
    "capture": "start-army",
    "storage": "start-storage",
    "forge": "start-forge",
    "equipment": "start-forge",
    "walls": "start-walls",
    "repair": "start-walls",
    "irrigation": "start-irrigation",
    "watch": "start-watch",
    "shelter": "start-shelter",
    "transport": "start-transport",
    "siege": "start-siege",
}

REPORT_SCENES = frozenset(
    f"{direction}-{kind}-{outcome}"
    for direction in ("offensive", "received")
    for kind in ("raid", "capture")
    for outcome in ("success", "failure")
)


def localize(value):
    return localize_message(value, get_language() or "fr")


def report_view(report):
    language = get_language() or "fr"
    scene = report.content.get("scene")
    start_scene = None
    if report.kind == "order" and report.content:
        # Earlier departure letters used a generic title but the same structured action.
        body = report.content["body"]
        action = body.get("values", {}).get("p0") if isinstance(body, dict) else None
        start_scene = next(
            (
                ACTION_START_SCENES[kind]
                for kind, phrase in STARTED_ACTION_PHRASES.items()
                if describe(phrase) in (report.content["title"], action)
            ),
            None,
        )
    return {
        "id": report.pk,
        "month": max(1, report.month),
        "title": render(report.content["title"], language) if report.content else report.title,
        "body": render(report.content["body"], language) if report.content else report.body,
        "original_archive": not report.content,
        "scene": start_scene
        or (
            scene
            if report.kind == "battle" and scene in REPORT_SCENES
            else {
                "battle": "raid",
                "return": "return",
                "work": "work",
                "harvest": "harvest",
                "sovereignty": "capture",
                "result": "council",
            }.get(report.kind, "letter")
        ),
        "icon": {
            "battle": "blades",
            "return": "return",
            "work": "works",
            "harvest": "grain",
            "sovereignty": "council",
            "result": "council",
        }.get(report.kind, "book"),
    }
