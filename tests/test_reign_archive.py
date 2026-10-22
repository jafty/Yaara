"""End-of-reign reading and analysis preserve recipient boundaries and history."""

from copy import deepcopy

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils.translation import override

from simulation import services
from simulation.models import Participant, Report, TickExecution
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


def finish(game, user):
    game.state["config"]["reign_months"] = 2
    game.save()
    services.tick(game.pk, 1, user)
    services.tick(game.pk, 2, user)
    game.refresh_from_db()


@case(
    "archive-tick-accounts", "Owner: immutable monthly accounts for each house, without combativity"
)
def test_tick_accounts(game, user):
    execution, _ = services.tick(game.pk, 1, user)
    accounts = execution.trace["chronicle"]["houses"]
    assert set(accounts) == {"p1", "p2", "p3"}
    assert accounts["p1"]["population"] == 3000
    assert {city["id"] for city in accounts["p1"]["owned_cities"]} == {"c1", "c2", "c3"}
    before = deepcopy(execution.trace)
    services.tick(game.pk, 1, user)
    execution.refresh_from_db()
    assert execution.trace == before
    assert "strength" not in str(accounts) and "combativity" not in str(accounts)


@case(
    "archive-scoped-export",
    "Owner: complete chronological letters and accounts for one or all houses",
)
@pytest.mark.parametrize("scope", ["player", "all"])
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("calendar_version", [1, 2])
def test_export(game, user, scope, language, calendar_version):
    game.state["calendar_version"] = calendar_version
    game.state["month"] = 0 if calendar_version == 1 else 1
    game.save()
    finish(game, user)
    for recipient in ("p1", "p2", "p3"):
        Report.objects.create(
            game=game,
            recipient=recipient,
            month=1,
            kind="order",
            title=recipient,
            body=f"Private {recipient}",
        )
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    before = deepcopy(game.state)
    reports_before = list(Report.objects.filter(game=game).values())
    with override(language):
        response = client.get(
            reverse("reign_archive", args=[game.pk]), {"scope": scope, "format": "json"}
        )
    assert response.status_code == 200
    assert "attachment" in response["Content-Disposition"]
    data = response.json()
    assert data["schema_version"] == 1
    assert data["language"] == language
    assert data["coverage"]["missing_account_moons"] == []
    assert [row["moon"] for row in data["accounts"]] == [1, 2]
    actors = {"p1", "p2", "p3"} if scope == "all" else {"p1"}
    assert {row["recipient"] for row in data["reports"]} == actors
    assert set(data["accounts"][0]["houses"]) == actors
    assert set(data["final_accounts"]) == actors
    assert [row["month"] for row in data["reports"]] == sorted(
        row["month"] for row in data["reports"]
    )
    assert "seed" not in data and "trace" not in data
    game.refresh_from_db()
    assert game.state == before
    assert list(Report.objects.filter(game=game).values()) == reports_before


@case(
    "archive-access",
    "Owner: archives require completion, membership and owner for all-house access",
)
@pytest.mark.parametrize(
    "variation",
    [
        "active",
        "paused",
        "outsider",
        "anonymous",
        "member-all",
        "member-own",
        "bad-scope",
        "bad-format",
        "post",
    ],
)
def test_access(game, user, variation):
    client = Client()
    client.force_login(user)
    scope = "all" if variation == "member-all" else "player"
    if variation not in {"active", "paused"}:
        finish(game, user)
    if variation == "paused":
        game.paused = True
        game.save()
    if variation in {"outsider", "member-all", "member-own"}:
        other = get_user_model().objects.create_user("reader")
        if variation.startswith("member"):
            Participant.objects.create(game=game, user=other, actor="p2")
        client.force_login(other)
    if variation == "anonymous":
        client.logout()
    url = reverse("reign_archive", args=[game.pk])
    response = (
        client.post(url)
        if variation == "post"
        else client.get(
            url,
            {
                "scope": "p2" if variation == "bad-scope" else scope,
                "format": "xml" if variation == "bad-format" else "json",
            },
        )
    )
    expected = {
        "anonymous": 302,
        "member-own": 200,
        "post": 405,
        "bad-scope": 404,
        "bad-format": 404,
    }.get(variation, 403)
    assert response.status_code == expected
    if variation == "member-own":
        assert set(response.json()["final_accounts"]) == {"p2"}


@case("archive-legacy-gap", "Owner: never fabricate missing historical monthly accounts")
def test_legacy(game, user):
    finish(game, user)
    TickExecution.objects.filter(game=game, month=1).update(trace={"private": "never export"})
    client = Client()
    client.force_login(user)
    data = client.get(reverse("reign_archive", args=[game.pk]), {"format": "json"}).json()
    assert data["coverage"]["missing_account_moons"] == [1]
    assert [row["moon"] for row in data["accounts"]] == [2]
    assert "never export" not in str(data)
    welcome = next(row for row in data["reports"] if row["kind"] == "welcome")
    assert welcome["month"] == 1
    assert welcome["recorded_month"] == 0


@case(
    "archive-complete-letters",
    "Owner: the literary log includes every preserved letter without a preview limit",
)
def test_complete_letters(game, user):
    finish(game, user)
    Report.objects.bulk_create(
        [
            Report(
                game=game,
                recipient="p1",
                month=1,
                kind="order",
                title=f"Letter {index}",
                body=f"Complete body {index}",
            )
            for index in range(110)
        ]
    )
    client = Client()
    client.force_login(user)
    response = client.get(reverse("reign_archive", args=[game.pk]))
    assert (
        len(response.context["archive"]["reports"])
        == Report.objects.filter(game=game, recipient="p1").count()
    )
    assert "Complete body 109" in response.content.decode()


@case("archive-reading", "Owner: bilingual native end-of-reign archive and download links")
@pytest.mark.usefixtures("test_static_storage")
@pytest.mark.parametrize("language", ["fr", "en"])
def test_reading(game, user, language):
    finish(game, user)
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    with override(language):
        response = client.get(reverse("reign_archive", args=[game.pk]), {"scope": "all"})
        council = client.get(reverse("game", args=[game.pk]))
    assert response.status_code == 200
    title = "Le livre du règne" if language == "fr" else "The book of the reign"
    assert title in response.content.decode()
    assert "scope=all&amp;format=json" in response.content.decode()
    assert reverse("reign_archive", args=[game.pk]) in council.content.decode()
    assert len(response.context["archive"]["reports"]) == Report.objects.filter(game=game).count()


@case("archive-tick-rollback", "Owner: monthly accounts and letters share the tick transaction")
def test_rollback(game, user, monkeypatch):
    original = deepcopy(game.state)

    def fail(*args, **kwargs):
        raise RuntimeError("archive write failure")

    monkeypatch.setattr(services, "chronicle_accounts", fail)
    with pytest.raises(RuntimeError, match="archive write failure"):
        services.tick(game.pk, 1, user)
    game.refresh_from_db()
    assert game.state == original
    assert not TickExecution.objects.filter(game=game).exists()
