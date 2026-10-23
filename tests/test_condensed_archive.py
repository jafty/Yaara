"""Retroactive condensed downloads preserve evidence and existing permissions."""

import json
from copy import deepcopy

import pytest
from django.test import Client
from django.urls import reverse
from django.utils.translation import override

from simulation.archives import condense_archive, reign_archive
from simulation.models import TickExecution
from tests.cases import case
from tests.test_reign_archive import finish

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case("condensed-retroactive", "Owner: condense existing completed games without rewriting history")
@pytest.mark.parametrize("scope", ["player", "all"])
@override("fr")
def test_retroactive(game, user, scope):
    finish(game, user)
    original = reign_archive(game, user, "p1", scope)
    before = deepcopy(original)
    client = Client()
    client.force_login(user)
    response = client.get(
        reverse("reign_archive", args=[game.pk]), {"scope": scope, "format": "compact"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data == condense_archive(original)
    assert original == before
    assert data["format"] == "yaara-condensed"
    assert data["ranking"] == original["ranking"]
    assert data["reports"] == original["reports"]
    assert set(data["final_accounts"]) == set(original["final_accounts"])
    assert len(data["economy"]["rows"]) == 2 * len(original["final_accounts"])
    assert "compact.json" in response["Content-Disposition"]
    assert response["Cache-Control"] == "private, no-store"
    assert len(response.content) < len(json.dumps(original, ensure_ascii=False).encode())
    game.refresh_from_db()
    assert reign_archive(game, user, "p1", scope) == before


@case("condensed-gaps", "Owner: missing old accounts stay explicit and never become zero balances")
def test_gaps(game, user):
    finish(game, user)
    TickExecution.objects.filter(game=game).update(trace={})
    data = condense_archive(reign_archive(game, user, "p1", "player"))
    assert data["coverage"]["missing_account_moons"] == [1, 2]
    assert data["economy"]["rows"] == []
    assert data["final_accounts"]["p1"]["stock"] > 0
    assert data["reports"]


@case(
    "condensed-transitions",
    "Owner: retain changes, ownership loss and final orders without repeated history",
)
def test_transitions(game, user):
    finish(game, user)
    archive = reign_archive(game, user, "p1", "player")
    account = archive["accounts"][0]["houses"]["p1"]
    order = {"id": "o1", "kind": "raid", "cost": 95000, "status": "executed"}
    account["orders"] = [order]
    archive["accounts"][1]["houses"]["p1"] = deepcopy(account)
    later = archive["accounts"][1]["houses"]["p1"]
    later["owned_cities"][0]["stock"] -= 100
    later["owned_cities"].pop()
    archive["final_accounts"]["p1"]["orders"] = [order]
    data = condense_archive(archive)
    assert len(data["order_changes"]) == 1
    assert data["order_changes"][0]["order"]["cost"] == 95000
    change = next(row for row in data["city_changes"] if row["moon"] == 2 and row["city"] == "c1")
    assert change["set"] == {"stock": later["owned_cities"][0]["stock"]}
    assert {"moon": 2, "actor": "p1", "city": "c3", "no_longer_owned": True} in data["city_changes"]
    assert "territory" not in str(data["city_changes"])


@case(
    "condensed-access",
    "Owner: compact format preserves archive completion and membership boundaries",
)
@pytest.mark.parametrize(
    "variation", ["active", "outsider", "member-all", "member-own", "anonymous"]
)
def test_access(game, user, variation):
    from django.contrib.auth import get_user_model

    from simulation.models import Participant

    if variation != "active":
        finish(game, user)
    client = Client()
    client.force_login(user)
    if variation in {"outsider", "member-all", "member-own"}:
        other = get_user_model().objects.create_user("compact-reader")
        if variation.startswith("member"):
            Participant.objects.create(game=game, user=other, actor="p2")
        client.force_login(other)
    if variation == "anonymous":
        client.logout()
    response = client.get(
        reverse("reign_archive", args=[game.pk]),
        {"format": "compact", "scope": "all" if variation == "member-all" else "player"},
    )
    assert response.status_code == {"anonymous": 302, "member-own": 200}.get(variation, 403)
    if variation == "member-own":
        assert set(response.json()["final_accounts"]) == {"p2"}


@case(
    "condensed-final-orders",
    "Owner: retain final-only and changed orders even without monthly history",
)
def test_final_orders(game, user):
    finish(game, user)
    archive = reign_archive(game, user, "p1", "player")
    archive["accounts"] = []
    order = {"id": "cancelled", "kind": "raid", "cost": 95000, "status": "cancelled"}
    archive["final_accounts"]["p1"]["orders"] = [order]
    data = condense_archive(archive)
    assert data["order_changes"] == [
        {"moon": 2, "actor": "p1", "source": "final_account", "order": order}
    ]
    assert "orders" not in data["final_accounts"]["p1"]
