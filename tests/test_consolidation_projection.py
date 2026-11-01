"""Recipient projections and stationary occupation presentation contracts."""

from copy import deepcopy

import pytest
from django.template.loader import render_to_string
from django.utils.translation import override

from simulation import engine
from simulation.cartography import schedule, workspace_context
from simulation.presentation import localize
from simulation.projections import player_view
from tests.cases import case

pytestmark = pytest.mark.logic
REQ = "Owner November 1: automatic occupation is visible only to its house and reserves defense stores"


def occupied_state():
    state = engine.new_state(opponents="passive", strategy_version=3)
    state["month"] = 3
    state["cities"]["c1"]["fideles"] = 60
    state["cities"]["c4"].update(owner="p1", consolidation_until=6)
    state["expeditions"].append(
        {
            "id": "capture:occupation",
            "order_id": "capture",
            "actor": "p1",
            "kind": "occupation",
            "status": "occupying",
            "target": "c4",
            "launch_city": "c3",
            "cohorts": {"c1": 40},
            "cohort_equipment": {"c1": 100},
            "combat_month": 2,
            "release_month": 6,
            "return_month": 7,
            "loot": 0,
            "return_routes": {},
            "arrived_origins": [],
        }
    )
    return state


@case("consolidation-own-defense-ledger", REQ)
def test_own_defense_ledger():
    """Given a captured city with forty occupiers and a frozen nine-hundred-thousand store.
    When its owner reads the city accounts during consolidation.
    Then no money is spendable but the real supplies feed the local people and occupiers.
    """
    state = occupied_state()
    before = deepcopy(state)
    view = player_view(state, "p1")
    city = next(city for city in view["owned_cities"] if city["id"] == "c4")
    assert city["consolidating"] and city["consolidation_until"] == 6
    assert city["occupying_fideles"] == 40
    assert (city["stock"], city["available_stock"], city["defense_stock"]) == (900000, 0, 900000)
    assert (city["siege_food"], city["siege_shortfall"], city["siege_months"]) == (520000, 0, 1)
    assert view["available_stock"] == 2700000
    convoy = next(city for city in view["convoy_origins"] if city["id"] == "c4")
    assert convoy["consolidating"] and not convoy["available"]
    assert next(city for city in view["owned_cities"] if city["id"] == "c1")["absent"] == 40
    assert state == before


@case("consolidation-private-ledger", REQ)
def test_private_ledger():
    """Given occupation details and frozen wealth inside another house's captured city.
    When a rival reads the map before and after those private details change.
    Then its city projection stays identical and reveals no occupation mission or treasury.
    """
    state = occupied_state()
    before = player_view(state, "p2")
    state["cities"]["c4"].update(stock=7, consolidation_until=11)
    state["expeditions"][0]["cohorts"]["c1"] = 13
    after = player_view(state, "p2")
    assert before["cities"][3] == after["cities"][3]
    assert after["missions"] == []
    assert not {
        "occupying_fideles",
        "consolidating",
        "consolidation_until",
        "defense_stock",
    }.intersection(after["cities"][3])
    assert "combativity" not in str(after)


@case("consolidation-ledger-release", REQ)
def test_ledger_release():
    """Given a captured city at the opening of its announced release Moon.
    When its owner reads the local funds before issuing a new order.
    Then its preserved store becomes fully spendable without inventing a new deposit.
    """
    state = occupied_state()
    state["month"] = 6
    city = next(city for city in player_view(state, "p1")["owned_cities"] if city["id"] == "c4")
    assert not city["consolidating"]
    assert city["available_stock"] == city["stock"] == 900000


@case("consolidation-stationary-map", REQ)
def test_stationary_map():
    """Given forty Faithful stationed in a conquered city until Moon six.
    When their house reads the map and schedule during Moon three.
    Then no marching arrow or past combat is shown and release and return remain dated.
    """
    view = localize(player_view(occupied_state(), "p1"))
    context = workspace_context(view)
    assert context["marches"] == []
    mission = view["missions"][0]
    assert mission["occupying"] and mission["release_month"] == 6
    events = [event for event in schedule(view) if event["anchor"] == "mission-capture:occupation"]
    assert [event["moon"] for event in events] == [6, 7]
    assert events[0]["label"] != "Arrivée prévue"


@case("consolidation-return-map", REQ)
def test_return_map():
    """Given an occupation detachment released and returning toward its original city.
    When its house reads the map after the automatic departure.
    Then the return arrow leaves the occupied city without announcing another battle.
    """
    state = occupied_state()
    state["month"] = 7
    state["expeditions"][0]["status"] = "returning"
    view = localize(player_view(state, "p1"))
    mission = view["missions"][0]
    assert not mission["occupying"] and mission["returning"]
    marches = workspace_context(view)["marches"]
    assert len(marches) == 1
    assert (marches[0]["origin"]["id"], marches[0]["target"]["id"], marches[0]["state"]) == (
        "c4",
        "c1",
        "returning",
    )
    events = [event for event in schedule(view) if event["anchor"] == "mission-capture:occupation"]
    assert [event["moon"] for event in events] == [7]


@case("consolidation-mission-language", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_mission_language(language):
    """Given a stationary occupation detachment and its announced automatic departure.
    When the mission register is rendered in {language}.
    Then it describes the garrison and release without presenting a past battle as forthcoming.
    """
    with override(language):
        view = localize(player_view(occupied_state(), "p1"))
        html = render_to_string("simulation/missions.html", {"view": view})
    assert ("En garnison" if language == "fr" else "On garrison duty") in html
    assert ("automatiquement" if language == "fr" else "automatically") in html
    assert ("Le combat est prévu" if language == "fr" else "Combat is expected") not in html
    assert "6" in html and "7" in html


@case("consolidation-return-language", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_return_language(language):
    """Given an occupation detachment already released to return home.
    When its mission register is rendered in {language}.
    Then the men are described as returning rather than still holding the conquered city.
    """
    state = occupied_state()
    state["expeditions"][0]["status"] = "returning"
    with override(language):
        view = localize(player_view(state, "p1"))
        html = render_to_string("simulation/missions.html", {"view": view})
    assert (
        "rentrent vers leurs cités" if language == "fr" else "return toward their cities"
    ) in html
    assert ("En garnison" if language == "fr" else "On garrison duty") not in html
    assert ("Le combat est prévu" if language == "fr" else "Combat is expected") not in html


@case("consolidation-city-language", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_city_language(language):
    """Given a captured city's spendable funds are frozen for consolidation.
    When its own city overview is rendered in {language}.
    Then the accounts explain the defense reserve and automatic end of the restriction.
    """
    with override(language):
        view = localize(player_view(occupied_state(), "p1"))
        selected = next(city for city in view["owned_cities"] if city["id"] == "c4")
        html = render_to_string(
            "simulation/city_overview.html", {"view": view, "selected": selected}
        )
    assert ("Consolidation" if language == "fr" else "Consolidation") in html
    assert ("défense" if language == "fr" else "defense") in html
    assert "6" in html
