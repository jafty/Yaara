"""Completed-reign archives, built only from recipient projections and saved letters."""

from django.core.exceptions import PermissionDenied
from django.utils.translation import get_language

from .calendar import closed_moon
from .presentation import localize, report_view
from .projections import player_view

ACCOUNT_FIELDS = (
    "actor",
    "realm",
    "population",
    "stock",
    "available_stock",
    "reserved_stock",
    "capacity",
    "available_fideles",
    "absent",
    "tax",
    "eliminated",
    "equipment",
    "owned_cities",
    "orders",
    "missions",
)


def chronicle_accounts(state):
    # Reuse the player allowlist: never archive raw snapshots, seeds or combat draws.
    return {
        actor: {key: view[key] for key in ACCOUNT_FIELDS}
        for actor in state["players"]
        for view in [player_view(state, actor)]
    }


def reign_archive(game, user, actor, scope):
    if game.state["status"] != "finished" or (scope == "all" and game.owner_id != user.pk):
        raise PermissionDenied
    actors = set(game.state["players"]) if scope == "all" else {actor}
    reports = []
    for report in game.reports.filter(recipient__in=actors).order_by("month", "id"):
        rendered = report_view(report, state=game.state)
        reports.append(
            {
                "id": report.pk,
                "month": rendered["month"],
                "recorded_month": report.month,
                "recipient": report.recipient,
                "house": localize(game.state["players"][report.recipient]["name"]),
                "kind": report.kind,
                "title": rendered["title"],
                "body": rendered["body"],
                "original_archive": rendered["original_archive"],
            }
        )
    accounts = []
    for tick in game.ticks.order_by("month"):
        saved = tick.trace.get("chronicle", {})
        if saved.get("schema_version") == 1 and actors <= saved.get("houses", {}).keys():
            accounts.append(
                {
                    "moon": tick.month,
                    "houses": {key: localize(saved["houses"][key]) for key in sorted(actors)},
                }
            )
    recorded = {row["moon"] for row in accounts}
    final_moon = closed_moon(game.state)
    return {
        "schema_version": 1,
        "game": {"id": str(game.pk), "title": game.title, "final_moon": final_moon},
        "scope": scope,
        "language": get_language(),
        "rule_versions": {
            key: game.state.get(key, 1)
            for key in (
                "calendar_version",
                "economy_version",
                "forge_version",
                "map_version",
            )
        }
        | {"rules": game.state["rules"]},
        "coverage": {
            "missing_account_moons": [
                moon for moon in range(1, final_moon + 1) if moon not in recorded
            ],
            "accounts_timing": "after_moon_closure",
            "report_order": "moon_then_record_id",
        },
        "reports": reports,
        "accounts": accounts,
        "final_accounts": {
            key: localize(value)
            for key, value in chronicle_accounts(game.state).items()
            if key in actors
        },
        "ranking": localize(player_view(game.state, actor)["ranking"]),
    }


# Analysis data deliberately excludes map geometry, UI labels and forecasts.
ECONOMY_FIELDS = (
    "population",
    "stock",
    "available_stock",
    "reserved_stock",
    "capacity",
    "available_fideles",
    "absent",
    "tax",
    "eliminated",
)
CITY_FIELDS = (
    "id",
    "name",
    "population",
    "present_population",
    "fideles",
    "absent",
    "available_fideles",
    "reserved_fideles",
    "stock",
    "capacity",
    "available_stock",
    "reserved_stock",
    "tax",
    "yield",
    "irrigation",
    "storage",
    "forge",
    "equipment",
    "walls",
    "damaged",
    "raid_available_moon",
    "deaths",
    "works",
)
BUILDING_FIELDS = ("kind", "level", "effective_level", "damaged", "finish_moon")


def compact_city(city):
    return {key: city[key] for key in CITY_FIELDS if key in city} | {
        "buildings": [
            {key: building[key] for key in BUILDING_FIELDS if key in building}
            for building in city.get("buildings", [])
        ]
    }


def condense_archive(archive):
    """Reduce an already-authorized v1 archive; never inspect private simulation state.

    Account deltas are observations at closure, not inferred causes or replayed events.
    Letters retain full evidence, including old unstructured narration.
    """
    previous_cities = {}
    previous_orders = {}
    city_changes = []
    order_changes = []
    economy = []
    for entry in archive["accounts"]:
        moon = entry["moon"]
        for actor, account in entry["houses"].items():
            economy.append([moon, actor] + [account.get(key) for key in ECONOMY_FIELDS])
            cities = {city["id"]: compact_city(city) for city in account["owned_cities"]}
            old_cities = previous_cities.get(actor, {})
            for city_id, city in cities.items():
                old = old_cities.get(city_id, {})
                changed = {
                    key: value for key, value in city.items() if key not in old or old[key] != value
                }
                removed = sorted(old.keys() - city.keys())
                if changed or removed:
                    city_changes.append(
                        {
                            "moon": moon,
                            "actor": actor,
                            "city": city_id,
                            "set": changed,
                            "unset": removed,
                        }
                    )
            for city_id in sorted(old_cities.keys() - cities.keys()):
                city_changes.append(
                    {
                        "moon": moon,
                        "actor": actor,
                        "city": city_id,
                        "no_longer_owned": True,
                    }
                )
            previous_cities[actor] = cities
            for order in account["orders"]:
                key = (actor, order["id"])
                if previous_orders.get(key) != order:
                    order_changes.append({"moon": moon, "actor": actor, "order": order})
                    previous_orders[key] = order
    # Orders sealed/cancelled between observations may only survive in the final register.
    for actor, account in archive["final_accounts"].items():
        for order in account["orders"]:
            if previous_orders.get((actor, order["id"])) != order:
                order_changes.append(
                    {
                        "moon": archive["game"]["final_moon"],
                        "actor": actor,
                        "source": "final_account",
                        "order": order,
                    }
                )
    return {
        "format": "yaara-condensed",
        "schema_version": 1,
        **{
            key: archive[key]
            for key in (
                "game",
                "scope",
                "language",
                "rule_versions",
                "coverage",
                "ranking",
            )
        },
        "reading_guide": {
            "economy": "Rows follow the columns header; null means unavailable, not zero. Tax is accrued levy, not income already paid.",
            "city_changes": "Apply set/unset per actor and city in order; no_longer_owned removes that city's previous observation. Changes span missing account Moons when coverage has gaps.",
            "order_changes": "Each entry is a changed observation of an order ID, not an additional purchase. Cost is a quote/commitment; cancellation and invalidation must be considered before treating it as spending.",
            "reports": "Complete recipient letters in Moon/record order. Multiple recipients can describe the same battle; do not count letters as battles.",
            "limitations": "No reconstruction of missing history, alert response times, private combat rolls or hypothetical outcomes. Monthly balances alone do not establish raid profitability or causes of losses. Repeated mission snapshots and UI/map descriptions are omitted; surviving missions remain in final accounts.",
        },
        "economy": {"columns": ["moon", "actor", *ECONOMY_FIELDS], "rows": economy},
        "city_changes": city_changes,
        "order_changes": order_changes,
        "reports": archive["reports"],
        "final_accounts": {
            actor: {
                key: value
                for key, value in account.items()
                if key not in {"owned_cities", "orders"}
            }
            | {"owned_cities": [compact_city(city) for city in account["owned_cities"]]}
            for actor, account in archive["final_accounts"].items()
        },
    }
