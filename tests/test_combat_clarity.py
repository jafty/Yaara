"""Archived combat disclosures use saved facts without rewriting letters."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from django.utils.translation import override

from simulation.messages import describe, message
from simulation.presentation import report_view
from tests.cases import case


@case(
    "combat-outcome-readable",
    "Owner: both recipients can read military outcomes independently of loot",
)
@pytest.mark.integration
@pytest.mark.parametrize("kind", ["raid", "capture"])
@pytest.mark.parametrize("direction", ["offensive", "received"])
@pytest.mark.parametrize("outcome", ["success", "failure"])
@pytest.mark.parametrize("language", ["fr", "en"])
def test_outcome(kind, direction, outcome, language):
    report = SimpleNamespace(
        pk=1,
        month=2,
        kind="battle",
        title="Archive",
        body="Original",
        content={"title": "Archive", "body": "Original", "scene": f"{direction}-{kind}-{outcome}"},
    )
    original = deepcopy(report.content)
    with override(language):
        body = report_view(report)["body"]
    expected = {
        ("fr", "success"): "L’attaque a réussi",
        ("fr", "failure"): "L’attaque a échoué",
        ("en", "success"): "The attack succeeded",
        ("en", "failure"): "The attack failed",
    }
    assert expected[language, outcome] in body
    assert "Original" in body
    assert report.content == original


@case(
    "capture-archive-attacker",
    "Owner: restore public attacker identity from a unique saved capture mission",
)
@pytest.mark.integration
@pytest.mark.parametrize(
    "variation", ["unique", "missing", "ambiguous", "wrong-moon", "own-mission"]
)
def test_archived_capture_identity(variation):
    report = SimpleNamespace(
        pk=1,
        month=2,
        kind="battle",
        recipient="p2",
        title="",
        body="Original",
        content={"title": describe(message("La bataille de {p0}", p0="City")), "body": "Original"},
    )
    mission = {"kind": "capture", "target": "c4", "actor": "p1", "combat_month": 2}
    state = {
        "cities": {"c4": {"name": "City"}},
        "players": {"p1": {"name": "House"}},
        "expeditions": [mission],
    }
    if variation == "missing":
        state["expeditions"] = []
    elif variation == "ambiguous":
        state["expeditions"].append(dict(mission))
    elif variation == "wrong-moon":
        mission["combat_month"] = 3
    elif variation == "own-mission":
        mission["actor"] = "p2"
    original = deepcopy(state)
    with override("en"):
        body = report_view(report, state=state)["body"]
    assert ("House" in body) == (variation == "unique")
    assert state == original
    assert report.content["body"] == "Original"


@case(
    "combat-clarity-http",
    "Owner: Council and archived capture letters disclose attacker and outcome only to their recipient",
)
@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("tab", ["domain", "letters"])
def test_capture_http(user, monkeypatch, language, tab):
    from django.test import Client
    from django.urls import reverse

    from simulation import services
    from tests.test_news_illustrations import combat_news

    game = services.create_game(user, "Clarity", opponents="passive", economy_version=3)
    game.state, events = combat_news(monkeypatch, "capture", "held")
    game.memberships.update(actor="p2")
    services.persist(game, events)
    saved = list(game.reports.values("id", "content", "body"))
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    page = client.get(reverse("game", args=[game.id]), {"tab": tab})
    assert page.status_code == 200
    text = page.content.decode()
    assert (
        "The attackers bore the seal" if language == "en" else "Les assaillants portaient le sceau"
    ) in text
    assert ("The attack failed" if language == "en" else "L’attaque a échoué") in text
    assert "offensive-capture" not in text
    assert list(game.reports.values("id", "content", "body")) == saved
