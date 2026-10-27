"""Recruitment presentation makes commitment and the next actual action explicit."""

import re
import uuid
from copy import deepcopy

import pytest
from django.test import Client
from django.urls import reverse

from simulation import services
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@pytest.fixture
def council(user):
    game = services.create_game(user, "First decisions", opponents="passive")
    client = Client()
    client.force_login(user)
    return game, client, reverse("game", args=[game.id])


@case(
    "oasis-current-setup-facts",
    "Recruitment: the setup page describes current starting means and affordable capture attempts",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_setup_facts(user, language):
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    response = client.get(reverse("new_game"))
    html = response.content.decode()
    assert response.context["initial_stock_per_city"] == 900_000
    assert response.context["initial_total_stock"] == 2_700_000
    assert response.context["initial_capture_minimum_cost"] == 210_000
    facts = re.search(r"<section[^>]*data-starting-means.*?</section>", html, re.S).group()
    normalized_facts = re.sub(r"[\s,]", "", facts)
    assert all(value in normalized_facts for value in ("900000", "2700000", "210000"))
    assert (
        "Capturing is deliberately beyond your initial reserves"
        if language == "en"
        else "La capture est volontairement hors de portée"
    ) not in html


@case(
    "oasis-first-decisions",
    "Recruitment: a first Council offers works and expeditions without changing the reign",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_first_decisions(council, language):
    game, client, url = council
    before = deepcopy(game.state)
    client.cookies["django_language"] = language
    html = client.get(url, {"tab": "domain"}).content.decode()
    opening = re.search(r"<section[^>]*data-first-decisions.*?</section>", html, re.S).group()
    assert "?tab=constructions" in opening and "?tab=wars" in opening
    assert ("Choose a work" if language == "en" else "Choisir un chantier") in opening
    assert ("Prepare an expedition" if language == "en" else "Préparer une expédition") in opening
    game.refresh_from_db()
    assert game.state == before and game.revision == 0


@case(
    "oasis-review-is-not-sealing",
    "Recruitment: preparation promises a review and does not reserve until the actual seal",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_review_not_sealing(council, language):
    game, client, url = council
    client.cookies["django_language"] = language
    html = client.get(url, {"tab": "constructions", "action": "irrigation"}).content.decode()
    assert 'class="primary-action work-review" type="submit"' in html
    review = client.post(
        reverse("preview", args=[game.id]), {"kind": "irrigation", "cities": ["c1"]}
    )
    assert review.status_code == 200
    game.refresh_from_db()
    assert game.state["orders"] == []
    assert game.state["cities"]["c1"]["stock"] == 900_000


@case(
    "oasis-sealed-next-closure",
    "Recruitment: sealed manual orders link to explicit Moon closure while still awaiting departure",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_sealed_next_closure(council, user, language):
    game, client, url = council
    services.confirm(user, game.id, {"kind": "irrigation", "cities": ["c1"]}, uuid.uuid4(), 1)
    game.refresh_from_db()
    before = deepcopy(game.state)
    client.cookies["django_language"] = language
    html = client.get(url, {"tab": "constructions"}).content.decode()
    notice = re.search(r"<aside[^>]*data-next-closure.*?</aside>", html, re.S).group()
    assert f"{url}?tab=domain#turn-page" in notice
    assert ("Review Moon closure" if language == "en" else "Passer à la clôture") in notice
    game.refresh_from_db()
    assert game.state == before
    assert game.state["orders"][0]["status"] == "confirmed"
    assert not game.state["works"]


@case(
    "oasis-started-clears-next-closure",
    "Recruitment: after closure the next-step cue clears and the actual work schedule remains visible",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_started_clears_next_closure(council, user, language):
    game, client, url = council
    services.confirm(user, game.id, {"kind": "irrigation", "cities": ["c1"]}, uuid.uuid4(), 1)
    services.tick(game.id, 1, user)
    client.cookies["django_language"] = language
    html = client.get(url, {"tab": "constructions"}).content.decode()
    assert "data-next-closure" not in html
    assert 'id="active-works"' in html and "Qasr" in html
    game.refresh_from_db()
    assert game.state["works"][0]["finish_month"] == 4


@case(
    "oasis-archive-secondary-exports",
    "Recruitment: the readable book stays primary while authorised JSON downloads remain optional",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_archive_secondary_exports(council, language):
    game, client, _ = council
    game.state["status"] = "finished"
    game.save()
    client.cookies["django_language"] = language
    html = client.get(reverse("reign_archive", args=[game.id])).content.decode()
    exports = re.search(r"<details[^>]*data-archive-exports.*?</details>", html, re.S).group()
    assert "format=compact" in exports and "format=json" in exports
    assert not re.match(r"<details[^>]*\bopen\b", exports)
    assert 'class="correspondence"' in html


@case(
    "oasis-target-reservation-copy",
    "Saved rules: attack review describes concurrent targets only for frontier-version games",
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("strategy_version", [1, 2])
def test_target_reservation_copy(user, language, strategy_version):
    game = services.create_game(
        user, "Target admission", opponents="passive", strategy_version=strategy_version
    )
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    response = client.post(
        reverse("preview", args=[game.id]),
        {"kind": "raid", "target": "c4", "men_c3": 30},
    )
    assert response.status_code == 200
    html = response.content.decode()
    if strategy_version == 2:
        assert (
            "Several expeditions may target the same city"
            if language == "en"
            else "Plusieurs expéditions peuvent viser la même cité"
        ) in html
        assert (
            "The first accepted seal claims the target"
            if language == "en"
            else "Le premier sceau accepté engage la cible"
        ) not in html
    else:
        assert (
            "The first accepted seal claims the target"
            if language == "en"
            else "Le premier sceau accepté engage la cible"
        ) in html
