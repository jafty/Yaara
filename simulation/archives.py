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
