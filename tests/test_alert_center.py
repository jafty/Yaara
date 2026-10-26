"""Persistent alerts reuse authorized, current city accounts without writing state."""

import re
import uuid
from copy import deepcopy
from html import unescape
from urllib.parse import urlsplit

import pytest
from django.test import Client
from django.urls import reverse

from simulation import engine, services
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case(
    "alerts-precise-destination",
    "Owner: alert links land on the relevant accounts or repair section",
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize(
    "issue,anchor",
    [
        ("threat", "city-defenses"),
        ("reserves", "city-stocks"),
        ("repair", "work-selection"),
        ("repair_watch", "work-selection"),
        ("repair_shelter", "work-selection"),
        ("sealed", "orders-heading"),
        ("active", "active-works"),
    ],
)
def test_alert_destination(user, language, issue, anchor):
    game, client, url = open_game(user, language)
    if issue == "threat":
        engine.confirm_order(
            game.state,
            "p2",
            {"kind": "raid", "target": "c3", "contributions": {"c4": 20}},
            "incoming",
        )
    elif issue == "reserves":
        game.state["cities"]["c3"]["stock"] = 100
    else:
        if issue in ("repair_watch", "repair_shelter"):
            family = issue.removeprefix("repair_")
            game.state["cities"]["c3"].update(**{family: 1}, damaged_works=[family])
        else:
            game.state["cities"]["c3"].update(damaged=True, integrity=50)
        if issue in ("sealed", "active"):
            engine.confirm_order(
                game.state, "p1", {"kind": "repair", "cities": ["c3"]}, str(uuid.uuid4())
            )
            if issue == "active":
                engine.advance_month(game.state, "departure")
    game.save()
    original = deepcopy(game.state)
    html = client.get(url, {"tab": "domain"}).content.decode()
    alert = re.search(r"<li[^>]*data-alert-kind=.*?</li>", html, re.S)[0]
    link = unescape(re.search(r'href="([^"]+)"', alert)[1])
    destination = urlsplit(link)
    assert destination.fragment == anchor
    target = client.get(link).content.decode()
    assert target.count(f'id="{anchor}"') == 1
    if issue not in ("sealed", "active"):
        assert re.search(rf'<[^>]+id="{anchor}"[^>]+tabindex="-1"', target)
    if issue.startswith("repair"):
        assert re.search(r'<input[^>]+name="cities"[^>]+value="c3"[^>]+\bchecked', target)
    game.refresh_from_db()
    assert game.state == original


def open_game(user, language, economy=4):
    game = services.create_game(
        user, "Alert centre", opponents="passive", economy_version=economy, strategy_version=1
    )
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    return game, client, reverse("game", args=[game.id])


@case("alerts-damaged-building", "Owner: damage is visible in the header, city list and details")
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize(
    "family,repair", [("walls", "repair"), ("watch", "repair_watch"), ("shelter", "repair_shelter")]
)
def test_damaged_building(user, language, family, repair):
    game, client, url = open_game(user, language)
    if family == "walls":
        game.state["cities"]["c1"].update(damaged=True, integrity=50)
    else:
        game.state["cities"]["c1"].update(**{family: 1}, damaged_works=[family])
    game.save()
    before = deepcopy(game.state)
    for query in ({"tab": "domain"}, {"tab": "wars"}, {"tab": "city", "city": "c1"}):
        text = client.get(url, query).content.decode()
        assert 'data-alert-count="1"' in text
        assert text.count('data-alert-kind="damage"') == 1
        alert = re.search(r'<li[^>]*data-alert-kind="damage".*?</li>', text, re.S)[0]
        assert "Qasr" in alert
        assert f"action={repair}&amp;city=c1" in alert
        assert ("Damaged structure" if language == "en" else "Ouvrage endommagé") in alert
        assert ("Inspect repair" if language == "en" else "Examiner la réparation") in alert
        if query.get("tab") == "domain":
            assert 'class="damage-state"' in text
        if query.get("tab") == "city":
            assert f'data-damaged-building="{family}"' in text
    game.refresh_from_db()
    assert game.state == before


@case(
    "alerts-repair-lifecycle", "Owner: damage alerts persist during repairs and clear on completion"
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("stage", ["needed", "sealed", "active", "cancelled", "completed"])
def test_repair_lifecycle(user, language, stage):
    game, client, url = open_game(user, language)
    game.state["cities"]["c1"].update(damaged=True, integrity=50)
    if stage != "needed":
        order = engine.confirm_order(
            game.state, "p1", {"kind": "repair", "cities": ["c1"]}, str(uuid.uuid4())
        )
        if stage == "cancelled":
            engine.cancel_order(game.state, "p1", order["id"])
        for _ in range(3 if stage == "completed" else int(stage == "active")):
            engine.advance_month(game.state, "repair")
    game.save()
    text = client.get(url, {"tab": "domain"}).content.decode()
    assert f'data-alert-count="{0 if stage in ("completed", "sealed", "active") else 1}"' in text
    if stage == "completed":
        assert 'data-alert-kind="damage"' not in text
    elif stage in ("sealed", "active"):
        phase = "reserved" if stage == "sealed" else "active"
        assert f'data-repair-phase="{phase}"' in text
        assert ("#orders-heading" if stage == "sealed" else "#active-works") in text
        assert ("Expected finish: Moon 3" if language == "en" else "Fin prévue : lune 3") in text
    else:
        assert 'data-repair-phase="none"' in text


@case(
    "alerts-centralized-state", "Owner: current actionable alerts are ordered, owned and persistent"
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize(
    "scenario", ["quiet", "combined", "paused", "finished", "enemy-damage", "legacy"]
)
def test_centralized_state(user, language, scenario):
    game, client, url = open_game(user, language, 1 if scenario == "legacy" else 4)
    if scenario in ("combined", "paused", "finished"):
        game.state["cities"]["c1"].update(damaged=True, integrity=50)
        game.state["cities"]["c2"]["stock"] = 100
        engine.confirm_order(
            game.state,
            "p2",
            {"kind": "raid", "target": "c3", "contributions": {"c4": 20}},
            str(uuid.uuid4()),
        )
    if scenario == "paused":
        game.paused = True
    if scenario == "finished":
        game.state.update(
            status="finished",
            result={"standings": engine.standings(game.state), "expeditions_in_transit": 0},
        )
    if scenario == "enemy-damage":
        game.state["cities"]["c4"].update(watch=2, damaged_works=["watch"], stock=1234567)
    if scenario == "legacy":
        game.state["cities"]["c1"].update(walls=1, damaged=True)
    game.save()
    original = deepcopy(game.state)
    for tab in ("domain", "wars", "constructions"):
        text = client.get(url, {"tab": tab}).content.decode()
        kinds = re.findall(r'data-alert-kind="([a-z]+)"', text)
        expected = (
            ["threat", "damage", "reserves"]
            if scenario in ("combined", "paused")
            else ["damage"]
            if scenario == "legacy"
            else []
        )
        assert kinds == expected
        assert f'data-alert-count="{len(expected)}"' in text
        assert '?tab=mail"' in text
        assert "1234567" not in text
    game.refresh_from_db()
    assert game.state == original
