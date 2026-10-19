"""Mixed city stages remain visible with actionable, recipient-safe benefits."""

import re
import uuid
from copy import deepcopy

import pytest
from django.test import Client
from django.urls import reverse

from simulation import engine, services
from simulation.projections import player_view
from tests.cases import case


@pytest.mark.logic
@case(
    "works-mixed-stages",
    "Owner: each city shows its current building, next upgrade and concrete benefit",
)
def test_mixed_stages():
    """Given granaries at ordinary, enlarged and completed stages.
    When the storage choices are projected.
    Then all cities remain visible with correct transitions, benefits and availability.
    """
    state = engine.new_state(opponents="passive")
    state["cities"]["c2"]["storage"] = 1
    state["cities"]["c3"]["storage"] = 2
    before = deepcopy(state)
    action = next(
        item for item in player_view(state, "p1")["work_actions"] if item["kind"] == "storage"
    )
    assert action["selectable"]
    first, second, final = action["cities"]
    assert (first["current_name"], first["work_name"], first["cost"], first["duration"]) == (
        "Grenier de la cité",
        "Grand grenier",
        500000,
        4,
    )
    assert (
        str(first["benefit"])
        == "Capacité du grenier : 2\u202f400\u202f000 → 3\u202f600\u202f000 Mesures."
    )
    assert (second["current_name"], second["work_name"], second["cost"], second["duration"]) == (
        "Grand grenier",
        "Silos de réserve",
        1200000,
        8,
    )
    assert (
        str(second["benefit"])
        == "Capacité du grenier : 3\u202f600\u202f000 → 6\u202f000\u202f000 Mesures."
    )
    assert final["current_name"] == "Silos de réserve"
    assert final["status"] == "completed" and not final["available"]
    assert final["reason"] == "Cet ouvrage est achevé."
    assert state == before


@pytest.mark.logic
@case(
    "works-busy-stages",
    "Owner: busy city rows keep their upgrade quote and explain active or sealed work",
)
def test_busy_stages():
    """Given canal teams active in Qasr and promised in Tamesh while Namar has silos.
    When storage choices are projected.
    Then all rows stay readable with their quotes and commitment reasons but none is selectable.
    """
    state = engine.new_state(opponents="passive")
    for city in state["cities"].values():
        city["stock"] = 2400000
    engine.confirm_order(state, "p1", {"kind": "irrigation", "cities": ["c1"]}, "canals")
    engine.advance_month(state, "works")
    engine.confirm_order(state, "p1", {"kind": "irrigation", "cities": ["c2"]}, "sealed")
    state["cities"]["c2"]["storage"] = 1
    state["cities"]["c3"]["storage"] = 2
    action = next(
        item for item in player_view(state, "p1")["work_actions"] if item["kind"] == "storage"
    )
    first, second, final = action["cities"]
    assert not action["selectable"]
    assert first["status"] == second["status"] == "busy"
    assert first["cost"] == 500000 and second["cost"] == 1200000
    assert first["reason"] == "Chantier en cours : Premiers canaux, jusqu’à la lune 7."
    assert second["reason"] == "Un décret scellé réserve déjà ces équipes."
    assert final["status"] == "completed"


@pytest.mark.logic
@case(
    "works-restrictions",
    "Owner: unavailable rows explain completion, intact walls or prerequisite repairs",
)
@pytest.mark.parametrize(
    "kind,walls,damaged,status",
    [
        ("walls", 1, True, "unavailable"),
        ("walls", 2, True, "completed"),
        ("repair", 0, False, "unavailable"),
        ("repair", 1, False, "unavailable"),
    ],
    ids=["repair-before-upgrade", "great-wall-complete", "no-wall-to-repair", "intact-wall"],
)
def test_restrictions(kind, walls, damaged, status):
    """Given {kind} choices for a city with wall stage {walls} and damage {damaged}.
    When the building list is projected.
    Then the city remains visible as {status} without a fictitious quote or mutation.
    """
    state = engine.new_state()
    state["cities"]["c1"].update(walls=walls, damaged=damaged)
    before = deepcopy(state)
    action = next(item for item in player_view(state, "p1")["work_actions"] if item["kind"] == kind)
    row = action["cities"][0]
    assert row["status"] == status and not row["available"]
    assert row["reason"] == (
        "Cette cité n’a pas d’enceinte à réparer."
        if kind == "repair" and not walls
        else "Cet ouvrage est achevé."
        if status == "completed"
        else "Il faut réparer l’enceinte avant de la renforcer."
        if kind == "walls"
        else "Cette enceinte ne nécessite aucune réparation."
    )
    assert not row["work_name"] and row["cost"] == 0
    assert state == before


@pytest.mark.logic
@case(
    "works-benefit-details",
    "Owner: exact economic changes and qualitative military improvements explain each upgrade",
)
@pytest.mark.parametrize(
    "kind,current,expected",
    [
        ("irrigation", 0, "Impôt par habitant présent : 100 → 200 Mesures par lune."),
        ("irrigation", 1, "Impôt par habitant présent : 200 → 300 Mesures par lune."),
        ("forge", 0, "Armement : Équipement ordinaire → Équipement renforcé."),
        ("forge", 1, "Armement : Équipement renforcé → Équipement supérieur."),
        ("walls", 0, "La garnison locale sera mieux protégée contre les captures."),
        ("repair", 1, "L’enceinte retrouvera toute sa protection, sans être agrandie."),
    ],
    ids=["first-canals", "canal-network", "city-forge", "master-forge", "walls", "repair"],
)
def test_benefit_details(kind, current, expected):
    """Given {kind} work at current stage {current}.
    When its improvement is described.
    Then the benefit is {expected} without revealing numerical combativity.
    """
    state = engine.new_state()
    city = state["cities"]["c1"]
    city["walls" if kind == "repair" else kind] = current
    city["damaged"] = kind == "repair"
    action = next(item for item in player_view(state, "p1")["work_actions"] if item["kind"] == kind)
    assert action["cities"][0]["benefit"] == expected
    assert action["purpose"] and action["advice"]


@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@case(
    "works-mixed-batch-http",
    "Owner: one mixed-stage batch preserves all rows and seals the correct distinct upgrades",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_mixed_batch_http(user, language):
    game = services.create_game(user, "Mixed stages", opponents="passive")
    game.state["cities"]["c2"]["storage"] = 1
    game.state["cities"]["c3"]["storage"] = 2
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    page = client.get(reverse("game", args=[game.id]), {"tab": "constructions"})
    action = next(
        item for item in page.context["view"]["work_actions"] if item["kind"] == "storage"
    )
    assert len(action["cities"]) == 3
    html = page.content.decode()
    assert (
        "Grenier de la cité → Grand grenier" in html
        if language == "fr"
        else "City granary → Great granary" in html
    )
    assert (
        "Le conseil des bâtisseurs" in html if language == "fr" else "The builders’ counsel" in html
    )
    preview = client.post(
        reverse("preview", args=[game.id]), {"kind": "storage", "cities": ["c1", "c2"]}
    )
    assert preview.status_code == 200
    assert preview.context["order"]["cost"] == 1700000
    assert [task["level"] for task in preview.context["order"]["tasks"]] == [1, 2]
    client.post(reverse("confirm", args=[game.id]), {"payload": preview.context["payload"]})
    game.refresh_from_db()
    assert len(game.state["orders"]) == 1
    assert sum(engine.reservations(game.state)[0].values()) == 1700000


@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@case(
    "works-all-completed-http",
    "Owner: fully upgraded cities remain readable without a misleading order form",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_all_completed_http(user, language):
    game = services.create_game(user, "Finished buildings", opponents="passive")
    for city in game.state["cities"].values():
        city["storage"] = 2
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    page = client.get(reverse("game", args=[game.id]), {"tab": "constructions"})
    action = next(
        item for item in page.context["view"]["work_actions"] if item["kind"] == "storage"
    )
    assert len(action["cities"]) == 3 and not action["selectable"]
    assert all(row["status"] == "completed" for row in action["cities"])
    assert action["prices"] == []
    storage = re.search(
        r'<details class="work-selection" id="work-storage".*?</article>',
        page.content.decode(),
        re.S,
    ).group()
    assert storage.count('data-work-status="completed"') == 3
    assert "<form" not in storage
    assert all(name in storage for name in ("Qasr", "Tamesh", "Namar"))


@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@case(
    "works-all-busy-http",
    "Owner: unavailable construction teams keep quotes, benefits and dates in a read-only list",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_all_busy_http(user, language):
    game = services.create_game(user, "Busy builders", opponents="passive")
    for city in game.state["cities"].values():
        city["stock"] = 2400000
    engine.confirm_order(
        game.state, "p1", {"kind": "irrigation", "cities": ["c1"]}, str(uuid.uuid4())
    )
    engine.advance_month(game.state, "builders")
    engine.confirm_order(
        game.state, "p1", {"kind": "irrigation", "cities": ["c2"]}, str(uuid.uuid4())
    )
    game.state["cities"]["c3"]["storage"] = 2
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    page = client.get(reverse("game", args=[game.id]), {"tab": "constructions"})
    storage = re.search(
        r'<details class="work-selection" id="work-storage".*?</article>',
        page.content.decode(),
        re.S,
    ).group()
    assert storage.count('data-work-status="busy"') == 2
    assert storage.count('data-work-status="completed"') == 1
    assert "<form" not in storage
    assert ("jusqu’à la lune 7" if language == "fr" else "until Moon 7") in storage
    assert ("Un décret scellé" if language == "fr" else "A sealed decree") in storage
    assert (
        "2\u202f400\u202f000 → 3\u202f600\u202f000 Mesures"
        if language == "fr"
        else "2,400,000 → 3,600,000 Measures"
    ) in storage
