"""Request-locale rendering of already authorized, recipient-specific data."""

from django.utils.translation import get_language

from .messages import localize as localize_message
from .messages import render


def localize(value):
    return localize_message(value, get_language() or "fr")


def report_view(report):
    language = get_language() or "fr"
    return {
        "id": report.pk,
        "month": max(1, report.month),
        "title": render(report.content["title"], language) if report.content else report.title,
        "body": render(report.content["body"], language) if report.content else report.body,
        "original_archive": not report.content,
        "scene": {
            "battle": "raid",
            "return": "return",
            "work": "work",
            "harvest": "harvest",
            "sovereignty": "capture",
            "result": "council",
        }.get(report.kind, "letter"),
        "icon": {
            "battle": "blades",
            "return": "return",
            "work": "works",
            "harvest": "grain",
            "sovereignty": "council",
            "result": "council",
        }.get(report.kind, "book"),
    }
