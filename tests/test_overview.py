"""The opening folio exposes city accounts alongside events and deadlines."""

import uuid

import pytest
from django.test import Client
from django.urls import reverse

from simulation import services
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case(
    "overview-first-reign",
    "Owner: the Council opens with a city ledger, news, next steps and no repeated house accounts",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_overview_first_reign(user, language):
    game = services.create_game(user, "Briefing", opponents="passive", map_version=1)
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    page = client.get(reverse("game", args=[game.id]))
    content = page.content.decode()
    assert page.status_code == 200
    assert 'id="recent-letters"' in content
    assert 'id="upcoming-heading"' in content
    assert content.index('id="city-ledgers"') < content.index('id="recent-letters"')
    assert 'class="house-accounts"' not in content
    assert len(page.context["milestones"]) == 1
    assert page.context["milestones"][0]["moon"] == 12
    assert "tab=constructions" in content and "tab=wars" in content


@case(
    "overview-work-deadlines",
    "UX: sealed orders and active work deadlines link to their management folios",
)
def test_overview_work_deadlines(user):
    game = services.create_game(user, "Works", opponents="passive", map_version=1)
    services.confirm(user, game.id, {"kind": "storage", "cities": ["c1"]}, uuid.uuid4(), 1)
    client = Client()
    client.force_login(user)
    url = reverse("game", args=[game.id])
    sealed = client.get(url)
    assert sealed.context["milestones"][0]["moon"] == 1
    assert sealed.context["milestones"][0]["tab"] == "decrees"
    services.tick(game.id, 1, user)
    active = client.get(url)
    assert active.context["milestones"][0]["moon"] == 5
    assert active.context["milestones"][0]["tab"] == "constructions"
    works = client.get(url, {"tab": "constructions"})
    assert works.status_code == 200
    assert b"Qasr" in works.content
    assert works.context["construction_count"] == 1


@case(
    "overview-military-deadlines",
    "UX: a departed raid shows combat then return dates without rival private state",
)
def test_overview_military_deadlines(user):
    game = services.create_game(user, "Campaign", opponents="passive", map_version=1)
    services.confirm(
        user,
        game.id,
        {"kind": "raid", "target": "c4", "contributions": {"c3": 45}},
        uuid.uuid4(),
        1,
    )
    services.tick(game.id, 1, user)
    client = Client()
    client.force_login(user)
    url = reverse("game", args=[game.id])
    page = client.get(url)
    military = [row for row in page.context["milestones"] if row["tab"] == "wars"]
    assert [row["moon"] for row in military] == [2, 3]
    wars = client.get(url, {"tab": "wars"})
    assert wars.status_code == 200
    assert b"Sefra" in wars.content
    assert all("stock" not in city for city in wars.context["view"]["cities"] if not city["owned"])


@case(
    "overview-finished-reign",
    "UX: a finished reign has reports and results without future milestones",
)
def test_overview_finished_reign(user):
    game = services.create_game(
        user, "Finished", opponents="passive", reign_months=24, map_version=1
    )
    for moon in range(1, 25):
        services.tick(game.id, moon, user)
    client = Client()
    client.force_login(user)
    page = client.get(reverse("game", args=[game.id]))
    assert page.context["view"]["finished"]
    assert page.context["milestones"] == []
    assert b'id="upcoming-heading"' not in page.content
    assert b'class="epilogue"' in page.content
