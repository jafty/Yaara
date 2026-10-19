"""One building list with shared in-world names in both languages."""

import re

import pytest
from django.test import Client
from django.urls import reverse

from simulation import engine, services
from simulation.projections import player_view
from tests.cases import case


@pytest.mark.logic
@case(
    "work-named-upgrades", "Owner: building upgrades use in-world names instead of numeric levels"
)
@pytest.mark.parametrize(
    "kind,level,name,cost,duration",
    [
        ("irrigation", 1, "Premiers canaux", 2400000, 6),
        ("irrigation", 2, "Réseau de canaux", 4800000, 12),
        ("storage", 1, "Grand grenier", 500000, 4),
        ("storage", 2, "Silos de réserve", 1200000, 8),
        ("walls", 1, "Enceinte de terre crue", 1200000, 8),
        ("walls", 2, "Grande enceinte", 9600000, 20),
        ("repair", 1, "Enceinte de terre crue", 240000, 3),
        ("repair", 2, "Grande enceinte", 1920000, 6),
        ("forge", 1, "Forge de la cité", 600000, 8),
        ("forge", 2, "Forge des maîtres", 1400000, 14),
    ],
)
def test_named_upgrade(kind, level, name, cost, duration):
    """Given a city ready for {kind} work at tier {level}.
    When the available works are projected.
    Then the quote and city choice use the building name {name} with unchanged prices.
    """
    state = engine.new_state(opponents="passive")
    city = state["cities"]["c1"]
    city["walls" if kind == "repair" else kind] = level if kind == "repair" else level - 1
    city["damaged"] = kind == "repair"
    action = next(item for item in player_view(state, "p1")["work_actions"] if item["kind"] == kind)
    choice = next(item for item in action["cities"] if item["id"] == "c1")
    price = next(item for item in action["prices"] if item["level"] == level)
    assert choice["work_name"] == price["name"] == name
    assert (price["cost"], price["duration"]) == (cost, duration)


@pytest.mark.logic
@case(
    "work-legacy-forge-choice",
    "Owner: legacy realm forges join the work list without a rule migration",
)
@pytest.mark.parametrize("level,busy", [(0, False), (1, False), (1, True), (2, False)])
def test_legacy_forge_choice(level, busy):
    """Given legacy realm equipment at tier {level} with busy status {busy}.
    When the work list is projected.
    Then it contains one forge choice preserving realm scope and its availability.
    """
    state = engine.new_state(forge_version=1)
    state["players"]["p1"]["equipment"] = level
    if busy:
        state["works"].append(
            {"kind": "equipment", "actor": "p1", "status": "active", "finish_month": 15}
        )
    actions = player_view(state, "p1")["work_actions"]
    assert sum(item["kind"] in ("forge", "equipment") for item in actions) == 1
    action = next(item for item in actions if item["kind"] == "equipment")
    assert action["selectable"] == (level < 2 and not busy)
    assert (
        action["equipment"]
        == ["Équipement ordinaire", "Équipement renforcé", "Équipement supérieur"][level]
    )
    assert not action.get("cities")
    assert [price["name"] for price in action["prices"]] == (
        [["Forge de la cité", "Forge des maîtres"][level]] if level < 2 else []
    )
    assert state["players"]["p1"]["equipment"] == level


@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@case("work-single-list", "Owner: Works has one main heading and forge shares the building list")
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("forge_version", [1, 2])
def test_single_list(user, language, forge_version):
    game = services.create_game(
        user, "Named works", forge_version=forge_version, opponents="passive"
    )
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    page = client.get(reverse("game", args=[game.id]), {"tab": "constructions"})
    html = page.content.decode()
    choices = re.search(
        r'<section class="work-choices".*?</section>\s*<section', html, re.S
    ).group()
    assert html.count("<h1>") == 1
    assert 'id="works-heading"' not in html
    assert "Du travail de la forge" not in html and "The work of the forge" not in html
    assert "Niveau " not in html and "Level " not in html
    assert ('id="work-forge"' in choices) == (forge_version == 2)
    assert ('id="work-equipment"' in choices) == (forge_version == 1)
    assert ("Grand grenier" if language == "fr" else "Great granary") in choices
    assert ("Forge de la cité" if language == "fr" else "City forge") in choices
    assert "data-work-form" in choices
    assert ('name="kind" value="equipment"' in choices) == (forge_version == 1)


@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@case("work-forge-folio-name", "Owner: city forge descriptions use named buildings at every tier")
@pytest.mark.parametrize("level", [0, 1, 2])
@pytest.mark.parametrize("language", ["fr", "en"])
def test_forge_folio_name(user, level, language):
    game = services.create_game(user, "Forge folio", opponents="passive")
    game.state["cities"]["c1"]["forge"] = level
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    html = client.get(
        reverse("game", args=[game.id]), {"tab": "city", "city": "c1"}
    ).content.decode()
    expected = (
        ["Atelier d’armes", "Forge de la cité", "Forge des maîtres"]
        if language == "fr"
        else ["Weapons workshop", "City forge", "Master smiths’ forge"]
    )[level]
    assert expected in html
    assert "de niveau" not in html and "Level " not in html


@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@case(
    "work-readonly-list",
    "Merged works remain readable without forms while a reign cannot accept orders",
)
@pytest.mark.parametrize("forge_version", [1, 2])
@pytest.mark.parametrize("state", ["paused", "finished"])
def test_readonly_list(user, forge_version, state):
    game = services.create_game(
        user, "Readonly works", forge_version=forge_version, opponents="passive"
    )
    if state == "paused":
        game.paused = True
    else:
        game.state["month"] = 120
        engine.advance_month(game.state, game.seed)
    game.save()
    client = Client()
    client.force_login(user)
    page = client.get(reverse("game", args=[game.id]), {"tab": "constructions"})
    html = page.content.decode()
    assert ('id="work-forge"' in html) == (forge_version == 2)
    assert ('id="work-equipment"' in html) == (forge_version == 1)
    assert 'class="work-choices"' in html
    assert "data-work-form" not in html
    assert 'name="kind" value="equipment"' not in html


@pytest.mark.logic
@case(
    "work-legacy-shortfall",
    "Forge usability: the available realm funds determine an exact shortfall",
)
@pytest.mark.parametrize("funds,shortfall", [(1799999, 1), (1800000, 0), (1800001, 0)])
def test_legacy_shortfall(funds, shortfall):
    """Given a realm forge quote with {funds} free Measures.
    When the work list is projected.
    Then its explicit missing amount is {shortfall} and no funds are reserved.
    """
    state = engine.new_state(forge_version=1)
    for city in state["cities"].values():
        if city["owner"] == "p1":
            city["stock"] = funds if city["id"] == "c1" else 0
    assert player_view(state, "p1")["equipment_shortfall"] == shortfall
    assert not state["orders"]


@pytest.mark.integration
@pytest.mark.usefixtures("test_static_storage")
@case(
    "work-legacy-submit-visible",
    "Forge usability: always show the action and explain insufficient funds",
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("affordable", [False, True])
def test_legacy_submit_visible(user, language, affordable):
    game = services.create_game(user, "Forge funds", forge_version=1, opponents="passive")
    if not affordable:
        game.state["cities"]["c1"]["stock"] = 599999
        game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    html = client.get(reverse("game", args=[game.id]), {"tab": "constructions"}).content.decode()
    form = next(
        form for form in re.findall(r"<form\b.*?</form>", html, re.S) if 'value="equipment"' in form
    )
    button = re.search(r"<button\b.*?</button>", form, re.S).group()
    assert 'type="submit"' in button and "primary-action" in button
    assert ("disabled" in button) != affordable
    if not affordable:
        assert ("1 Measures" if language == "en" else "1 Mesures") in form
        assert ("missing" if language == "en" else "Il manque") in form
