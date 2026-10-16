"""Serializable narration, independent of Django, storage and the active locale.

The French string remains useful to the simulation's callers. Its expression tree
keeps vocabulary separate from names and observations for later translation.
"""


class Message(str):
    def __new__(cls, source, **values):
        instance = super().__new__(cls, source.format(**values))
        instance.tree = {
            "source": source,
            "values": {key: node(value) for key, value in values.items()},
        }
        return instance

    def __add__(self, other):
        return Message("{first}{second}", first=self, second=other)

    def __radd__(self, other):
        return Message("{first}{second}", first=other, second=self)

    def lower(self):
        instance = str.__new__(Message, str(self).lower())
        instance.tree = {"lower": self.tree}
        return instance


def node(value):
    return value.tree if isinstance(value, Message) else {"literal": value}


def render(tree, translate=lambda source: source):
    if "literal" in tree:
        return str(tree["literal"])
    if "number" in tree:
        result = f"{tree['number']:,}"
        separator = translate("number-group-separator")
        return result.replace(",", "\u202f" if separator == "number-group-separator" else separator)
    if "lower" in tree:
        return render(tree["lower"], translate).lower()
    return translate(tree["source"]).format(
        **{key: render(value, translate) for key, value in tree["values"].items()}
    )


def content(title, body):
    return {
        "title": node(title if isinstance(title, Message) else Message(title)),
        "body": node(body if isinstance(body, Message) else Message(body)),
    }
