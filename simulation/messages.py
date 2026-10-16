"""Serializable presentation messages. The simulation always produces French.

Only explicit message templates are translated, never player names or arbitrary
stored strings. Rendering is pure and receives its language as an explicit input.
"""

import gettext
from functools import lru_cache
from pathlib import Path


class Message(str):
    def __new__(cls, template, **values):
        obj = super().__new__(cls, template.format(**values))
        obj.content = {"template": template, "values": {k: describe(v) for k, v in values.items()}}
        return obj

    def __add__(self, other):
        return message("{left}{right}", left=self, right=other)

    def __radd__(self, other):
        return message("{left}{right}", left=other, right=self)

    def lower(self):
        obj = Message(str(self).lower())
        obj.content = {"lower": self.content}
        return obj


def message(template, **values):
    return Message(template, **values)


def describe(value):
    return value.content if isinstance(value, Message) else value


@lru_cache
def catalog(language):
    return gettext.translation(
        "django",
        Path(__file__).resolve().parent.parent / "locale",
        languages=[language.split("-")[0]],
        fallback=True,
    )


def render(content, language="fr"):
    if not isinstance(content, dict):
        return content
    if "number" in content:
        return (
            f"{content['number']:,}".replace(",", "\u202f")
            if language.startswith("fr")
            else f"{content['number']:,}"
        )
    if "lower" in content:
        return render(content["lower"], language).lower()
    template = content["template"]
    if not language.startswith("fr"):
        template = catalog(language).gettext(template)
    return template.format(
        **{key: render(value, language) for key, value in content["values"].items()}
    )


def localize(value, language):
    if isinstance(value, Message):
        return render(value.content, language)
    if isinstance(value, dict):
        return {key: localize(item, language) for key, item in value.items()}
    if isinstance(value, list):
        return [localize(item, language) for item in value]
    return value
