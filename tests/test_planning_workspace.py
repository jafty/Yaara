"""Presentation contracts for the owner's mobile planning revision."""

import re
from copy import deepcopy

import pytest
from django.urls import reverse

from simulation import engine
from tests.cases import case
from tests.test_map_workspace import open_board

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]
REQ = "Owner: readable decision pane, usable army preparation, regular fields and envelope news"


@case("planning-expandable-sheet", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("section", ["map", "city", "mail", "review"])
def test_expandable_sheet(user, language, section):
    game, client, url = open_board(user, language)
    before = deepcopy(game.state)
    if section == "review":
        response = client.post(
            reverse("preview", args=[game.id]), {"kind": "irrigation", "cities": "c1"}
        )
    else:
        params = {"city": "c1"} if section == "city" else {"tab": section}
        response = client.get(url, params)
    html = response.content.decode()
    assert html.count("data-sheet-expand") == 1
    assert 'aria-controls="map-context" aria-expanded="false"' in html
    assert ("Agrandir le panneau" if language == "fr" else "Expand panel") in html
    assert 'class="sheet-body"' in html
    game.refresh_from_db()
    assert game.state == before


@case("planning-native-army", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_native_army(user, language):
    game, client, url = open_board(user, language)
    before = deepcopy(game.state)
    response = client.get(url, {"city": "c4", "men_c1": "10", "men_c3": "20"})
    html = response.content.decode()
    assert 'id="expedition-form"' in html
    assert 'class="mission-timeline"' in html
    assert 'class="order-actions" data-army-summary' in html
    assert 'type="submit" form="expedition-form"' in html
    assert re.search(r'id="army-total">30</strong>', html)
    assert re.search(r'id="army-cost">35\D000</strong>', html)
    assert 'aria-describedby="mission-help"' in html
    assert 'type="range"' not in html
    for city in response.context["view"]["owned_cities"]:
        field = re.search(rf'<input id="men-{city["id"]}"[^>]+>', html).group()
        assert 'type="number"' in field and 'inputmode="numeric"' in field
        assert f'max="{city["available_fideles"]}"' in field
        assert 'aria-label="' in field
    game.refresh_from_db()
    assert game.state == before


@case("planning-envelope-news", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_envelope_news(user, language):
    _, client, url = open_board(user, language)
    html = client.get(url).content.decode()
    header = re.search(r'<header class="reign-header">.*?</header>', html, re.S).group()
    assert 'data-icon="envelope"' in header
    assert 'data-icon="bell"' not in header
    assert 'data-alert-count="0"' in header
    assert ("Nouvelles" if language == "fr" else "News") in header
    assert 'class="visually-hidden"' in header


@case("planning-compact-city-identity", "Owner: city and owner share the compact sheet heading")
@pytest.mark.parametrize("language", ["fr", "en"])
def test_compact_city_identity(user, language):
    _, client, url = open_board(user, language)
    response = client.get(url, {"city": "c1"})
    html = response.content.decode()
    heading = re.search(r'<header class="sheet-heading">.*?</header>', html, re.S).group()
    assert 'id="context-title" tabindex="-1">Qasr</h1>' in heading
    assert 'class="sheet-owner"' in heading
    assert response.context["selected"]["owner_name"] in heading


@case(
    "planning-city-free-means",
    "Owner: one ledger row shows spendable means, accounts retain detail",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_city_free_means(user, language):
    game, client, url = open_board(user, language)
    engine.confirm_order(game.state, "p1", {"kind": "irrigation", "cities": ["c1"]}, "works")
    game.save()
    html = client.get(url, {"city": "c1"}).content.decode()
    means = re.search(r'<dl class="city-resources".*?</dl>', html, re.S).group()
    assert re.search(r"<strong>600\D000</strong>", means)
    assert "<strong>100</strong>" in means
    assert "<meter" not in html and 'class="city-capabilities"' not in html
    accounts = client.get(url, {"city": "c1", "action": "accounts"}).content.decode()
    assert 'id="city-stocks"' in accounts
    assert re.search(r"2\D400\D000", accounts)
    assert re.search(r"300\D000", accounts)


@case("planning-convoy-fields", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_convoy_fields(user, language):
    _, client, url = open_board(user, language)
    html = client.get(url, {"city": "c1", "action": "convoy"}).content.decode()
    assert 'class="convoy-fields"' in html
    for field in ("origin", "target", "cargo"):
        assert f'<label for="convoy-{field}">' in html
    assert 'id="convoy-cargo" name="cargo" min="1" max="500000"' in html
