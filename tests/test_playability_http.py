"""Native current-rule pages and command boundaries."""

import json
import re

import pytest
from django.test import Client
from django.urls import reverse

from simulation import services
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case(
    "playability-current-pages",
    "Owner GO: bilingual illustrated family pages replace nested work disclosures",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_current_pages(user, language):
    game = services.create_game(user, "Current", opponents="passive")
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    url = reverse("game", args=[game.id])
    catalogue = client.get(url, {"tab": "constructions"}).content.decode()
    assert catalogue.count('class="work-card ledger-note"') == 8
    assert "work-selection" not in catalogue and 'id="active-works"' not in catalogue
    assert "action=repair" not in catalogue
    family = client.get(url, {"tab": "constructions", "action": "irrigation"})
    text = family.content.decode()
    assert text.count('name="cities"') == 3
    assert ("Channels and small dikes" if language == "en" else "Rigoles et petites digues") in text
    assert ("Validate action" if language == "en" else "Valider l’action") in text
    preview = client.post(
        reverse("preview", args=[game.id]), {"kind": "irrigation", "cities": ["c1", "c2"]}
    )
    assert preview.status_code == 200 and preview.context["order"]["cost"] == 600000
    game.refresh_from_db()
    assert game.state["orders"] == []
    client.post(reverse("confirm", args=[game.id]), {"payload": preview.context["payload"]})
    game.refresh_from_db()
    assert game.state["orders"][0]["funding"] == {"c1": 300000, "c2": 300000}


@case(
    "playability-direct-attack",
    "Owner GO: a map target directly exposes one native radio-based preparation form",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_direct_attack(user, language):
    game = services.create_game(user, "Attack", opponents="passive")
    game.state["cities"]["c4"].update(stock=1234567, tax=2345678, forge=3, watch=2)
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    response = client.get(reverse("game", args=[game.id]), {"tab": "wars", "city": "c4"})
    text = response.content.decode()
    assert text.count('class="expedition-form"') == 1
    assert text.count('type="radio" name="kind"') == 2
    assert 'id="mission-target" value="c4"' in text
    assert '<select name="target"' not in text
    assert "data-expedition-kind" not in text
    assert "1234567" not in text and "2345678" not in text
    opponent = next(c for c in response.context["view"]["cities"] if c["id"] == "c4")
    assert not {"stock", "tax", "forge", "watch", "combativity"}.intersection(opponent)
    assert "cohort_equipment" not in json.dumps(response.context["view"])


@case(
    "playability-unversioned-creation",
    "Owner GO: current creation has no rules selector and ignores obsolete version form fields",
)
def test_creation(user):
    client = Client()
    client.force_login(user)
    page = client.get(reverse("new_game"))
    assert b'name="version"' not in page.content
    assert b"V0" not in page.content and b"V1" not in page.content
    response = client.post(
        reverse("new_game"),
        {
            "title": "Current",
            "player_name": "House",
            "version": "V0",
            "opponents": "passive",
            "reign_months": 120,
            "mode": "manual",
            "interval_minutes": 10,
        },
    )
    assert response.status_code == 302
    from simulation.models import Game

    game = Game.objects.get(owner=user)
    assert game.state["rules"] == "V1" and game.state["economy_version"] == 3


@case(
    "playability-restored-fortification",
    "Owner GO: repair shows partial wall damage and its explicit local opportunity cost",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_repair_page(user, language):
    game = services.create_game(user, "Repair", opponents="passive")
    game.state["cities"]["c1"].update(walls=3, damaged=True)
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    page = client.get(reverse("game", args=[game.id]), {"tab": "constructions", "action": "repair"})
    assert page.status_code == 200
    action = page.context["action"]
    first = action["cities"][0]
    assert first["cost"] == 480000 and first["duration"] == 8
    assert len(re.findall(r'name="cities"', page.content.decode())) == 3
    assert first["current_damaged"]
