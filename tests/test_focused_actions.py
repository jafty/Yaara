"""Owner's proportional map and compact illustrated-action contracts."""

import re
from copy import deepcopy

import pytest

from tests.cases import case
from tests.test_map_workspace import open_board

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]
REQ = (
    "Owner: preserve map proportions; focused actions, conquest icons and compact illustrated works"
)


@case("focused-action-sheet", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("action", ["works", "irrigation", "convoy", "expedition"])
def test_focused_sheet(user, language, action):
    game, client, url = open_board(user, language)
    before = deepcopy(game.state)
    params = {"city": "c4"} if action == "expedition" else {"city": "c1", "action": action}
    html = client.get(url, params).content.decode()
    assert "data-focus-action" in html
    assert 'preserveAspectRatio="none"' not in html
    assert 'preserveAspectRatio="xMidYMid meet"' in html
    if action == "expedition":
        assert html.count('class="illustration illustration-army" aria-hidden="true"') == 1
        assert 'id="expedition-form"' in html
    if action != "expedition":
        close = re.search(r'<a class="panel-close".*?</a>', html, re.S).group()
        assert "city=c1" in close
        if action == "irrigation":
            assert "action=works" in close
        else:
            assert "action=works" not in close
    game.refresh_from_db()
    assert game.state == before


@case("focused-no-ui-arrows", "Owner: remove arrow decorations and use words for comparisons")
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("section", ["map", "city", "works", "army", "mail", "domain", "help"])
def test_no_ui_arrows(user, language, section):
    _, client, url = open_board(user, language)
    params = {
        "city": {"city": "c1"},
        "works": {"city": "c1", "action": "works"},
        "army": {"city": "c4"},
    }.get(section, {"tab": section})
    html = client.get(url, params).content.decode()
    assert not any(arrow in html for arrow in "←→↔↗↘⇒")
    assert "marker-end" not in html


@case("focused-conquest-choice", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_conquest_choice(user, language):
    _, client, url = open_board(user, language)
    html = client.get(url, {"city": "c4"}).content.decode()
    choices = re.search(r'<fieldset class="mission-options">.*?</fieldset>', html, re.S).group()
    assert 'data-icon="raid"' in choices and 'data-icon="conquer"' in choices
    assert ("Conquérir" if language == "fr" else "Conquer") in choices
    assert 'name="kind" value="capture"' in choices


@case("focused-illustrated-work", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_illustrated_work(user, language):
    game, client, url = open_board(user, language)
    before = deepcopy(game.state)
    html = client.get(url, {"city": "c1", "action": "works"}).content.decode()
    row = re.search(r'<article class="local-work-choice work-row".*?</article>', html, re.S).group()
    assert "illustration-building" in row
    assert ("<span>Améliorer</span>" if language == "fr" else "<span>Improve</span>") in row
    assert ("Vérifier l’ordre" if language == "fr" else "Review the order") not in row
    assert (
        'class="visually-hidden">lunes</span>' in row
        if language == "fr"
        else 'class="visually-hidden">Moons</span>' in row
    )
    assert 'data-icon="grain"' in row and 'data-icon="moon"' in row
    game.refresh_from_db()
    assert game.state == before


@case(
    "focused-rectangle-work-detail",
    "Owner: list artwork is square and work details retain a rectangle",
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize(
    "params",
    [
        {"city": "c1", "action": "irrigation"},
        {"tab": "constructions", "action": "irrigation"},
    ],
    ids=["local", "batch"],
)
def test_rectangle_work_detail(user, language, params):
    _, client, url = open_board(user, language)
    html = client.get(url, params).content.decode()
    assert "illustration-building-detail" in html


@case("focused-repair-verb", "Owner: damaged works use a repair action in the city catalogue")
@pytest.mark.parametrize("language", ["fr", "en"])
def test_repair_verb(user, language):
    game, client, url = open_board(user, language)
    game.state["cities"]["c1"].update(damaged=True, integrity=50)
    game.save()
    html = client.get(url, {"city": "c1", "action": "works"}).content.decode()
    row = re.search(r'<article[^>]*id="local-work-repair".*?</article>', html, re.S).group()
    assert ("<span>Réparer</span>" if language == "fr" else "<span>Repair</span>") in row


@case("desktop-focused-moon-review", "Owner: Moon closure opens a focused native review")
@pytest.mark.parametrize("language", ["fr", "en"])
def test_focused_moon_review(user, language):
    game, client, url = open_board(user, language)
    before = deepcopy(game.state)
    html = client.get(url, {"tab": "domain", "review": "moon"}).content.decode()
    sheet = html.split('id="map-context"', 1)[1]
    assert "data-focus-action" in sheet
    assert 'id="turn-page"' in sheet
    assert 'class="panel-close" href="?tab=map"' in sheet
    assert 'method="post"' in sheet and "/advance/" in sheet
    assert 'class="standings"' not in sheet
    assert "data-first-decisions" not in sheet
    assert "folio-tools" not in sheet
    game.refresh_from_db()
    assert game.state == before
