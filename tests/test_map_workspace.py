"""Acceptance contracts specified before the map workspace implementation."""

import uuid
from copy import deepcopy

import pytest
from django.test import Client
from django.urls import reverse

from simulation import engine, services
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]
REQ = "Owner October 26: map-first local decisions and precise, illustrated courrier"


def open_board(user, language="fr"):
    game = services.create_game(user, "Map decisions", opponents="passive")
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    return game, client, reverse("game", args=[game.id])


@case("map-workspace-entry", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_entry(user, language):
    game, client, url = open_board(user, language)
    html = client.get(url).content.decode()
    assert "map-workspace" in html
    assert html.count('<line class="map-connection') == 12
    assert html.count('class="map-city ') == 9
    assert "user-scalable=no" not in html
    assert ("Nouvelles" if language == "fr" else "News") in html


@case("map-local-work", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_local_work(user, language):
    game, client, url = open_board(user, language)
    response = client.get(url, {"tab": "map", "city": "c1", "action": "irrigation"})
    assert response.status_code == 200
    assert response.context["local_work"]["id"] == "c1"
    assert response.context["activity"] == "irrigation"
    html = response.content.decode()
    assert '<input type="hidden" name="cities" value="c1">' in html
    assert 'type="checkbox"' not in html
    assert 'data-local-work="c1"' in html
    assert "300" in html


@case("map-switch-family", REQ)
def test_switch_family(user):
    game, client, url = open_board(user)
    html = client.get(url, {"tab": "map", "city": "c1", "action": "storage"}).content.decode()
    assert "?tab=map&amp;city=c2&amp;action=storage#map-context" in html
    assert 'name="men_c1"' not in html


@case("map-preview-context", REQ)
def test_preview_context(user):
    game, client, url = open_board(user)
    before = deepcopy(game.state)
    response = client.post(
        reverse("preview", args=[game.id]), {"kind": "irrigation", "cities": "c1"}
    )
    assert response.status_code == 200
    html = response.content.decode()
    assert "map-workspace" in html
    assert 'name="payload"' in html
    assert 'class="panel-close" href="' in html
    assert "?tab=map&amp;action=irrigation&amp;city=c1#map-context" in html
    assert "c1" in html
    game.refresh_from_db()
    assert game.state == before


@case("map-mail-route", REQ)
def test_mail_route(user):
    game, client, url = open_board(user)
    order = engine.confirm_order(
        game.state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c3": 20}}, "own-march"
    )
    engine.advance_month(game.state, "departure")
    game.save()
    response = client.get(url, {"tab": "mail", "mail": "schedule"})
    assert response.status_code == 200
    html = response.content.decode()
    assert f"#mission-{order['id']}" in html
    assert 'data-march-state="outbound"' in html


@case("map-attention-overflow", REQ)
def test_overflow(user):
    game, client, url = open_board(user)
    game.state["cities"]["c1"]["stock"] = 2400000
    game.save()
    html = client.get(url, {"tab": "mail"}).content.decode()
    assert 'data-alert-kind="overflow"' in html
    assert "city=c1#city-stocks" in html
    assert "illustration-harvest" in html


@case("map-attention-repair", REQ)
def test_repair_tracking(user):
    game, client, url = open_board(user)
    game.state["cities"]["c1"].update(damaged=True, integrity=50)
    engine.confirm_order(game.state, "p1", {"kind": "repair", "cities": ["c1"]}, str(uuid.uuid4()))
    game.save()
    response = client.get(url, {"tab": "mail"})
    assert not any(item["kind"] == "damage" for item in response.context["attention"]["items"])
    html = client.get(url, {"tab": "mail", "mail": "schedule"}).content.decode()
    assert "#order-" in html


@case("map-public-intelligence", REQ)
@pytest.mark.parametrize("watch", [0, 1, 2])
def test_private_route(user, watch):
    game, client, url = open_board(user)
    game.state["cities"]["c3"]["watch"] = watch
    engine.confirm_order(
        game.state, "p2", {"kind": "raid", "target": "c3", "contributions": {"c4": 45}}, "secret"
    )
    engine.advance_month(game.state, "departure")
    game.save()
    response = client.get(url)
    assert response.context["marches"] == []
    html = response.content.decode()
    assert ('data-threat-city="c3"' in html) == bool(watch)
    assert "secret" not in html


@case("map-mail-invalid", REQ)
def test_invalid_mail(user):
    game, client, url = open_board(user)
    assert client.get(url, {"tab": "mail", "mail": "unknown"}).status_code == 404


@case("map-readonly-actions", REQ)
@pytest.mark.parametrize("condition", ["paused", "finished", "eliminated"])
@pytest.mark.parametrize("activity", ["irrigation", "convoy", "expedition"])
def test_readonly_actions(user, condition, activity):
    game, client, url = open_board(user)
    if condition == "paused":
        game.paused = True
    elif condition == "finished":
        game.state.update(
            status="finished",
            result={"standings": engine.standings(game.state), "expeditions_in_transit": 0},
        )
    else:
        game.state["players"]["p1"]["eliminated"] = True
    game.save()
    before = deepcopy(game.state)
    city = "c4" if activity == "expedition" else "c1"
    html = client.get(url, {"tab": "map", "city": city, "action": activity}).content.decode()
    assert f'action="{reverse("preview", args=[game.id])}"' not in html
    game.refresh_from_db()
    assert game.state == before


@case("map-conquered-city", REQ)
def test_conquered_city(user):
    game, client, url = open_board(user)
    game.state["cities"]["c4"].update(owner="p1", restricted_fideles=100, restricted_until=5)
    game.save()
    response = client.get(url, {"tab": "map", "city": "c4"})
    assert response.context["selected"]["owned"]
    html = response.content.decode()
    assert "Fidèles hérités" in html
    assert "city=c4&amp;action=works" in html
    assert 'name="men_c4"' not in html
    local = client.get(url, {"tab": "map", "city": "c4", "action": "storage"})
    assert local.context["local_work"]["id"] == "c4"


@case("map-permanent-overview", "Owner: permanent half-screen workspace on entry and Council")
@pytest.mark.parametrize("tab", ["map", "domain", "prologue"])
def test_permanent_workspace(user, tab):
    game, client, url = open_board(user)
    response = client.get(url, {"tab": tab})
    html = response.content.decode()
    assert response.context["workspace"] is True
    assert html.count('id="map-context"') == 1
    assert 'class="map-workspace"' in html
    assert 'class="chapter-heading compact-heading"' not in html
    assert 'class="council-layout"' not in html
    if tab != "prologue":
        assert 'class="context-sheet realm-sheet"' in html
        if tab == "domain":
            assert 'id="turn-page"' in html
        else:
            assert 'class="map-guide-key"' in html
            assert 'id="recent-letters"' not in html
            assert 'class="map-reference"' not in html
