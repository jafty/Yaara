"""Presentation contracts for the owner's mobile planning revision."""

import re
from copy import deepcopy
from uuid import uuid4

import pytest
from django.urls import reverse

from simulation import engine
from simulation.models import Report
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
    "Owner: granary shows stock, capacity and spendable means when reserved",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_city_free_means(user, language):
    game, client, url = open_board(user, language)
    engine.confirm_order(game.state, "p1", {"kind": "irrigation", "cities": ["c1"]}, "works")
    game.save()
    html = client.get(url, {"city": "c1"}).content.decode()
    means = re.search(r'<dl class="city-resources".*?</dl>', html, re.S).group()
    assert re.search(r"<strong>900\D000</strong>", means)
    assert re.search(r"2\D400\D000", means)
    assert re.search(r"600\D000", means)
    assert ("Mesures libres" if language == "fr" else "Available measures") in means
    assert 'data-icon="grain"' in means and 'data-icon="warrior"' in means
    assert (
        'class="visually-hidden">Grenier' in means
        if language == "fr"
        else 'class="visually-hidden">Granary' in means
    )
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


@case("planning-news-count", "Owner: the envelope announces recipient news for the latest moon")
@pytest.mark.parametrize("language", ["fr", "en"])
def test_news_count(user, language):
    game, client, url = open_board(user, language)
    Report.objects.filter(game=game).delete()
    for recipient, kind, title in [
        ("p1", "battle", "News"),
        ("p1", "order", "Décret scellé"),
        ("p2", "battle", "Private"),
    ]:
        Report.objects.create(
            game=game, recipient=recipient, month=1, kind=kind, title=title, body="Report"
        )
    html = client.get(url).content.decode()
    assert 'data-news-count="1"' in html
    assert 'data-news-ids="' in html
    assert 'data-mail-key="' in html
    assert 'data-alert-count="0"' in html
    mail = client.get(url, {"tab": "mail"}).content.decode()
    assert 'data-news-count="1"' in mail


@case("planning-schedule-no-duplicate-index", "Owner: deadlines show detailed commitments once")
@pytest.mark.parametrize("language", ["fr", "en"])
def test_schedule_no_duplicate_index(user, language):
    game, client, url = open_board(user, language)
    order_id = str(uuid4())
    engine.confirm_order(game.state, "p1", {"kind": "irrigation", "cities": ["c1"]}, order_id)
    game.save()
    html = client.get(url, {"tab": "mail", "mail": "schedule"}).content.decode()
    assert 'class="milestones"' not in html
    assert f'id="order-{order_id}"' in html
    assert 'id="harvest-accounts"' in html
    assert ("Lune 12" if language == "fr" else "Moon 12") in html
