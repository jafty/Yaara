# French and English presentation

French remains the default. The language form uses Django's CSRF-protected
`set_language` endpoint and language cookie; without a choice, LocaleMiddleware
uses the supported browser language and then French. The choice applies to pages,
forms, validation messages, player projections, reports and interactive help.
It never changes an order, a simulation rule or a game snapshot. Names supplied
by players and stored realm/city names remain verbatim in either language.

Django gettext handles templates, form labels, plurals and JavaScript. The pure
engine imports no Django translation state. Its `message(template, **values)`
returns a French string with a serializable description attached. Existing
French comparisons, exception matching and JSON snapshots keep their meaning.
At the HTTP boundary, explicit messages are rendered with the request language;
arbitrary strings are never searched or replaced. Translate before formatting
values, so names and numbers are not mistaken for translation keys. `number()`
keeps a number's value for locale-specific rendering.

New recipient reports store both their original French title/body and a JSON
`content` description of those same public facts. Reading a report renders that
description without running the engine again or consulting current opponent
state. This preserves the report's original date, recipient and information
limits. Existing reports have empty content and remain verbatim: no attempt is
made to parse or rewrite archived prose. Changing language does not update any
report row. Run the `0002_report_content` migration before deploying this code.

Use separate phrases for intentions, beginnings and completions. A proposed
work says “Agrandir le grenier”; departure says “Les travaux des greniers ont
commencé”; completion says “Les équipes de Qasr ont agrandi le grenier”. Do not
infer a past participle by replacing a verb suffix: the explicit vocabulary
handles irregular verbs and distinguishes work begun from work completed.

## Updating copy

Keep French source templates and named interpolation values in `message()`.
Keep names literal. Preserve message descriptions when composing report text:
use message parameters or message concatenation rather than interpolating a
message into a new unmarked string. A new rendering operation must preserve its
description; do not assume every inherited string operation does so.

With GNU gettext installed:

```bash
uv run python manage.py makemessages -l en --no-wrap
uv run python manage.py makemessages -l en -d djangojs --no-wrap
# Review and translate every new or fuzzy entry in locale/en/LC_MESSAGES/*.po.
uv run python manage.py compilemessages -l en --ignore=.venv
```

The small `makemessages` command extension adds the `message` extraction keyword;
the rest is Django's standard workflow. Commit both `.po` and compiled `.mo`
catalogs, so production needs no translation compiler. The browser loads the
Django JavaScript catalog before the progressive enhancement script. Numeric
HTML values use Django localization; JavaScript uses the document language.

The pure-core regressions retain the French assertions and cover past-tense
work phrases and a report's JSON round trip. HTTP cases cover language selection,
English forms and projections, legacy archives and JavaScript. The browser smoke
explicitly starts in French, switches to English, previews and resolves a work,
then reads the same completion in French. These checks supplement the existing
privacy, transaction and rule tests.
