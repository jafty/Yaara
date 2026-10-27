"""Contracts for the owner's mockup-led city sheets, specified before implementation."""

from copy import deepcopy

import pytest
from django.urls import reverse

from simulation import engine
from tests.cases import case
from tests.test_map_workspace import open_board

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]
REQ = "Owner October 27: furnished mockup as UX base, retained features and palette"


@case("mockup-house-hud", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_house_hud(user, language):
    game, client, url = open_board(user, language)
    response = client.get(url)
    html = response.content.decode()
    assert 'class="house-identity"' in html
    assert response.context["view"]["realm"] in html
    assert 'class="harvest-link"' in html
    assert "?tab=mail&amp;mail=schedule#harvest-accounts" in html


@case("mockup-city-direct-work", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_city_direct_work(user, language):
    game, client, url = open_board(user, language)
    before = deepcopy(game.state)
    html = client.get(url, {"city": "c1"}).content.decode()
    assert 'class="context-sheet city-sheet"' in html
    assert 'class="sheet-heading"' in html and 'class="sheet-body"' in html
    assert 'id="city-granary"' in html and "<meter " in html
    assert 'class="city-capabilities"' in html
    assert 'data-local-work="c1"' in html
    assert 'name="kind" value="irrigation"' in html
    assert 'type="checkbox"' not in html
    game.refresh_from_db()
    assert game.state == before


@case("mockup-city-work-availability", REQ)
@pytest.mark.parametrize("condition", ["poor", "busy", "paused"])
def test_work_availability(user, condition):
    game, client, url = open_board(user)
    if condition == "poor":
        game.state["cities"]["c1"]["stock"] = 0
    elif condition == "busy":
        engine.confirm_order(game.state, "p1", {"kind": "irrigation", "cities": ["c1"]}, "crew")
    else:
        game.paused = True
    game.save()
    response = client.get(url, {"city": "c1"})
    html = response.content.decode()
    if condition == "paused":
        assert f'action="{reverse("preview", args=[game.id])}"' not in html
    else:
        assert 'data-local-work="c1"' in html
        assert 'type="submit" disabled' in html
    if condition == "busy":
        assert "?tab=mail&amp;mail=schedule#order-" in html


@case("mockup-enemy-direct-preparation", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_enemy_preparation(user, language):
    game, client, url = open_board(user, language)
    response = client.get(url, {"city": "c4"})
    html = response.content.decode()
    assert 'class="expedition-form"' in html
    assert 'name="kind" value="raid"' in html
    assert 'name="kind" value="capture"' in html
    assert "data-contingent-controls" in html
    assert 'class="order-actions"' in html
    assert 'id="city-granary"' not in html
    assert "data-local-work=" not in html


@case("mockup-enemy-unreachable", REQ)
def test_unreachable(user):
    game, client, url = open_board(user)
    html = client.get(url, {"city": "c5"}).content.decode()
    assert 'class="expedition-form"' not in html
    assert 'id="city-granary"' not in html
    assert "data-local-work=" not in html


@case("mockup-mail-frame", REQ)
@pytest.mark.parametrize("section", ["attention", "schedule", "chronicle"])
def test_mail_frame(user, section):
    game, client, url = open_board(user)
    html = client.get(url, {"tab": "mail", "mail": section}).content.decode()
    assert 'class="courrier-window"' in html
    assert 'class="context-sheet mail-panel"' in html
    assert 'class="sheet-body"' in html
    assert 'class="sheet-tabs"' in html
    assert html.count('id="context-title"') == 1
