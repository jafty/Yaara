"""Existing public threats and own crew commitments stay visible in the folios."""

import re
import uuid
from copy import deepcopy

import pytest
from django.test import Client
from django.urls import reverse

from simulation import engine, services
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case("ui-incoming-threat", "Owner: every folio warns of committed enemy attacks on owned cities")
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize(
    "stage",
    ["quiet", "confirmed", "active", "paused", "cancelled", "resolved", "finished", "outgoing"],
)
def test_incoming_threat(user, language, stage):
    game = services.create_game(user, "Threats", opponents="passive", strategy_version=1)
    if stage != "quiet":
        actor, target, origin = ("p1", "c4", "c3") if stage == "outgoing" else ("p2", "c3", "c4")
        engine.confirm_order(
            game.state,
            actor,
            {"kind": "raid", "target": target, "contributions": {origin: 20}},
            str(uuid.uuid4()),
        )
        if stage == "cancelled":
            engine.cancel_order(game.state, actor, game.state["orders"][0]["id"])
        if stage in ("active", "paused", "resolved"):
            engine.advance_month(game.state, "departure")
        if stage == "resolved":
            engine.advance_month(game.state, "combat")
        if stage == "paused":
            game.paused = True
        if stage == "finished":
            game.state["status"] = "finished"
            game.state["result"] = {
                "standings": engine.standings(game.state),
                "expeditions_in_transit": 0,
            }
    game.save()
    original = deepcopy(game.state)
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    for tab in ("domain", "wars", "constructions"):
        text = client.get(reverse("game", args=[game.id]), {"tab": tab}).content.decode()
        alerts = re.findall(r'<aside class="threat-notice".*?</aside>', text, re.S)
        if stage in ("confirmed", "active", "paused"):
            assert len(alerts) == 1
            assert 'data-threat-city="c3"' in alerts[0] and "Namar" in alerts[0]
            assert ("Enemy expedition" if language == "en" else "Expédition ennemie") in alerts[0]
            assert "tab=city&amp;city=c3" in alerts[0]
            wording = re.sub(r"<[^>]+>", "", alerts[0])
            assert "20" not in wording and "Sefra" not in wording
        else:
            assert alerts == []
    game.refresh_from_db()
    assert game.state == original


@case(
    "ui-city-crew-status", "Owner: city names show crew availability including sealed reservations"
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("stage", ["free", "sealed", "active", "completed", "cancelled"])
def test_crew_status(user, language, stage):
    game = services.create_game(user, "Crews", opponents="passive")
    if stage != "free":
        engine.confirm_order(
            game.state, "p1", {"kind": "irrigation", "cities": ["c2"]}, str(uuid.uuid4())
        )
        if stage == "cancelled":
            engine.cancel_order(game.state, "p1", game.state["orders"][0]["id"])
        for _ in range(4 if stage == "completed" else int(stage == "active")):
            engine.advance_month(game.state, "build")
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    url = reverse("game", args=[game.id])
    busy = stage in ("sealed", "active")
    expected = "occupied" if busy else "available"
    roster = client.get(url, {"tab": "domain"}).content.decode()
    identity = re.search(r'id="city-c2".*?<div class="city-identity">(.*?)</div>', roster, re.S)[1]
    assert "Tamesh" in identity and f'data-team-state="{expected}"' in identity
    label = (
        ("Crew occupied" if busy else "Crew available")
        if language == "en"
        else ("Équipe occupée" if busy else "Équipe libre")
    )
    assert label in identity
    choices = client.get(url, {"tab": "constructions", "action": "storage"}).content.decode()
    assert choices.count(f'data-team-state="{expected}"') == (1 if busy else 3)
    if not busy:
        assert "data-crew-phase" not in identity
    if busy:
        assert ("Expected finish: Moon 4" if language == "en" else "Fin prévue : lune 4") in roster


@case("ui-crew-assignment", "Owner: lists and city details name the crew's actual work and dates")
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("phase", ["sealed", "active"])
@pytest.mark.parametrize(
    "kind,french,english,finish",
    [
        ("irrigation", "Rigoles et petites digues", "Channels and small dikes", 4),
        ("forge", "Petit arsenal", "Small arsenal", 4),
        ("repair", "Défenses de la cité", "City defenses", 3),
    ],
    ids=["irrigation", "forge", "initial-defence-repair"],
)
def test_crew_assignment(user, language, phase, kind, french, english, finish):
    game = services.create_game(user, "Crew assignments", opponents="passive")
    if kind == "repair":
        game.state["cities"]["c2"].update(damaged=True, integrity=50)
    engine.confirm_order(game.state, "p1", {"kind": kind, "cities": ["c2"]}, str(uuid.uuid4()))
    if phase == "active":
        engine.advance_month(game.state, "begin")
    game.save()
    original = deepcopy(game.state)
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    name = english if language == "en" else french
    expected_phase = "reserved" if phase == "sealed" else "active"
    for query in (
        {"tab": "domain"},
        {"tab": "city", "city": "c2"},
        {"tab": "constructions", "action": "storage"},
    ):
        html = client.get(reverse("game", args=[game.id]), query).content.decode()
        assignments = re.findall(r'<span class="crew-assignment".*?</span>', html, re.S)
        assert len(assignments) == 1
        assert name in assignments[0] and f'data-crew-phase="{expected_phase}"' in assignments[0]
        assert (
            f"Expected finish: Moon {finish}" if language == "en" else f"Fin prévue : lune {finish}"
        ) in assignments[0]
        if query.get("tab") == "city":
            assert ("Start: Moon 1" if language == "en" else "Début : lune 1") in assignments[0]
        assert ("#orders-heading" if phase == "sealed" else "#active-works") in assignments[0]
    game.refresh_from_db()
    assert game.state == original
