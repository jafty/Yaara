"""The literary layout exposes events and decisions before secondary navigation."""

import re
from copy import deepcopy
from html import unescape

import pytest
from django.test import Client
from django.urls import reverse

from simulation import services
from simulation.messages import describe, message
from simulation.models import Report
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@pytest.fixture
def folio(user, request):
    game = services.create_game(user, "Les chroniques de Yaara", opponents="passive")
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = request.param
    return game, client, reverse("game", args=[game.pk])


@case("layout-council-priority", "Redesign: news and forthcoming events precede city accounts")
@pytest.mark.parametrize("folio", ["fr", "en"], indirect=True)
def test_council_priority(folio):
    game, client, url = folio
    original = deepcopy(game.state)
    text = client.get(url).content.decode()
    assert text.index('id="recent-letters"') < text.index('id="upcoming-heading"')
    assert text.index('id="upcoming-heading"') < text.index('id="city-ledgers"')
    assert 'href="#upcoming-heading"' in text and 'href="#city-ledgers"' in text
    heading = re.search(r'<header class="chapter-heading.*?</header>', text, re.S).group()
    assert "illustration-council" in heading
    game.refresh_from_db()
    assert game.state == original


@case("layout-resource-labels", "Redesign: icons and exact values retain visible resource names")
@pytest.mark.parametrize("folio", ["fr", "en"], indirect=True)
def test_resource_labels(folio):
    _, client, url = folio
    text = client.get(url).content.decode()
    ribbon = re.search(r'<div class="resource-ribbon".*?</div>', text, re.S).group()
    assert all(f'data-icon="{icon}"' in ribbon for icon in ("grain", "warrior", "moon"))
    captions = re.findall(r'<span class="resource-caption">(.*?)</span>', ribbon)
    assert captions == (
        ["Measures", "Faithful", "Moon"]
        if client.cookies["django_language"].value == "en"
        else ["Mesures", "Fidèles", "Lune"]
    )
    assert ribbon.count("<strong>") == 3


@case("layout-report-reading-order", "Redesign: report title precedes art and prose precedes links")
@pytest.mark.parametrize("folio", ["fr", "en"], indirect=True)
def test_report_reading_order(folio):
    game, client, url = folio
    report = Report.objects.create(
        game=game,
        recipient="p1",
        month=1,
        kind="battle",
        title="A dated encounter",
        body="An immutable account.\n\n" + "word " * 45 + "END-OF-LETTER",
        content={
            "title": describe(message("A dated encounter")),
            "body": describe(message("An immutable account.\n\n" + "word " * 45 + "END-OF-LETTER")),
            "city_id": "c4",
            "scene": "offensive-raid-success",
        },
    )
    original = deepcopy(report.content)
    for compact in (True, False):
        text = client.get(url, {"tab": "domain" if compact else "letters"}).content.decode()
        entry = re.search(
            rf'<article class="letter-entry" id="report-{report.pk}">.*?</article>', text, re.S
        ).group()
        assert entry.index("An immutable account.") < entry.index("?tab=city")
        if compact:
            assert entry.index("An immutable account.") < entry.index(
                f"?tab=letters#report-{report.pk}"
            )
        else:
            assert entry.index("A dated encounter") < entry.index(
                "illustration-offensive-raid-success"
            )
            assert "END-OF-LETTER" in entry
            assert "?tab=domain" in entry
    report.refresh_from_db()
    assert report.content == original


@case("layout-map-reference", "Redesign: map reading advice is a native optional disclosure")
@pytest.mark.parametrize("folio", ["fr", "en"], indirect=True)
def test_map_reference(folio):
    _, client, url = folio
    text = client.get(url, {"tab": "wars", "city": "c4"}).content.decode()
    legend = re.search(r'<details class="map-reference">.*?</details>', text, re.S).group()
    assert "<summary>" in legend and "map-states" in legend
    assert not re.search(r"<details[^>]*\bopen", legend)
    assert "target-knowledge" not in legend and "expedition-form" not in legend
    assert 'id="map-context"' in text and 'id="mission-target"' in text


@case("layout-named-quotes", "Redesign: every catalogue quote pairs its upgrade name and price")
@pytest.mark.parametrize("folio", ["fr", "en"], indirect=True)
def test_named_quotes(folio):
    _, client, url = folio
    response = client.get(url, {"tab": "constructions"})
    text = response.content.decode()
    assert 'illustration-work"' not in text
    for action in response.context["view"]["work_actions"]:
        if action["repair"] and not action["prices"]:
            continue
        card = re.search(rf'<a id="work-{action["kind"]}".*?</a>', text, re.S).group()
        quotes = re.findall(r'<span class="work-price">(.*?)</span>', card, re.S)
        assert len(quotes) == len(action["prices"])
        for quote, price in zip(quotes, action["prices"], strict=True):
            assert str(price["name"]) in unescape(quote)
            figures = re.sub(r"[^0-9]", "", unescape(re.sub(r"<[^>]+>", "", quote)))
            assert figures == f"{price['cost']}{price['duration']}"


@case(
    "layout-family-decision", "Redesign: work heading precedes art and batch selection stays direct"
)
@pytest.mark.parametrize("folio", ["fr", "en"], indirect=True)
def test_family_decision(folio):
    _, client, url = folio
    text = client.get(url, {"tab": "constructions", "action": "storage"}).content.decode()
    assert text.index('id="work-selection"') < text.index("illustration-storage")
    assert text.count('name="cities"') == 3
    assert 'class="primary-action" type="submit"' in text


@case(
    "layout-report-anchor", "Redesign: report anchors use unformatted identifiers in both languages"
)
@pytest.mark.parametrize("folio", ["fr", "en"], indirect=True)
def test_report_anchor(folio):
    game, client, url = folio
    report = Report.objects.create(
        pk=100000,
        game=game,
        recipient="p1",
        month=1,
        kind="battle",
        title="A preserved report",
        body="Full historical prose",
    )
    for tab in ("domain", "letters"):
        text = client.get(url, {"tab": tab}).content.decode()
        assert f'id="report-{report.pk}"' in text
        if tab == "domain":
            assert f'href="?tab=letters#report-{report.pk}"' in text
