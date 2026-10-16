"""Request-locale rendering of already authorized, recipient-specific data."""

from django.utils.translation import gettext

from .messages import Message, render


def localize(value):
    if isinstance(value, Message):
        return render(value.tree, gettext)
    if isinstance(value, dict):
        return {key: localize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [localize(item) for item in value]
    return value


def report_view(report):
    return {
        "month": max(1, report.month),
        "title": render(report.content["title"], gettext) if report.content else report.title,
        "body": render(report.content["body"], gettext) if report.content else report.body,
        "original_archive": not report.content,
    }
