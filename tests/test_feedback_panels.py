"""Compact city figures retain their meaning and linked local commitments."""

import re

import pytest
from django.template.loader import render_to_string
from django.utils.translation import override

from tests.cases import case
from tests.test_map_workspace import open_board

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case("feedback-city-stat-meaning", "Owner: city figures have an accessible general explanation")
@pytest.mark.parametrize("language", ["fr", "en"])
def test_city_stat_meaning(user, language):
    _, client, url = open_board(user, language)
    html = client.get(url, {"city": "c1"}).content.decode()
    explanation = re.search(r'<details class="city-stat-help">.*?</details>', html, re.S)
    assert explanation is not None
    text = explanation.group()
    assert ("Comprendre les chiffres" if language == "fr" else "Understand the figures") in text
    assert ("capacité totale" if language == "fr" else "total capacity") in text
    assert ("réservations" if language == "fr" else "reservations") in text
    assert ("Fidèles" if language == "fr" else "Faithful") in text
    assert ("prochaine récolte" if language == "fr" else "next harvest") in text


@case(
    "feedback-city-linked-deadline",
    "Owner: local deadlines keep their date and destination together",
)
def test_city_linked_deadlines():
    events = [
        {"moon": 3, "anchor": "mission-raiders", "label": "Combat prévu", "detail": "Nahr"},
        {"moon": 4, "anchor": "convoy-grain", "label": "Arrivée du convoi", "detail": "Qasr"},
    ]
    with override("fr"):
        html = render_to_string(
            "simulation/city_overview.html",
            {"selected": {"name": "Qasr", "population": 1000}, "city_panel_schedule": events},
        )
    deadlines = re.search(r'<div class="city-deadlines".*?</div>', html, re.S).group()
    links = re.findall(r"<li><a[^>]+>.*?</a></li>", deadlines, re.S)
    assert len(links) == 2
    assert "#mission-raiders" in links[0] and "Lune 3" in links[0]
    assert "Combat prévu · Nahr" in links[0]
    assert "#convoy-grain" in links[1] and "Lune 4" in links[1]
    assert "Arrivée du convoi" in links[1]
    assert " · Qasr" not in links[1]


@case("feedback-city-empty-deadlines", "Owner: an idle city does not reserve empty deadline space")
def test_city_empty_deadlines():
    with override("fr"):
        html = render_to_string(
            "simulation/city_overview.html",
            {"selected": {"name": "Qasr", "population": 1000}, "city_panel_schedule": []},
        )
    assert "data-city-deadlines" not in html
