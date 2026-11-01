"""Bilingual read-only interfaces for automatic consolidation."""

import pytest
from django.test import Client
from django.urls import reverse

from simulation import services
from tests.cases import case
from tests.test_consolidation_projection import occupied_state

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]
REQ = (
    "Owner November 1: captured-city funds remain available for defense while new orders are frozen"
)


@case("consolidation-funding-warning-http", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_funding_warning_http(user, language):
    game = services.create_game(user, "Occupation accounts", opponents="passive")
    game.state = occupied_state()
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    response = client.get(reverse("game", args=[game.id]), {"tab": "wars", "city": "c5"})
    assert response.status_code == 200
    city = next(city for city in response.context["view"]["owned_cities"] if city["id"] == "c4")
    assert city["available_stock"] == 0
    assert city["expedition_food"] == 520000
    assert city["expedition_siege_shortfall"] == 0
    html = response.content.decode()
    assert 'data-defense-stock="900000"' in html
    assert 'data-occupiers="40"' in html
    assert ("Consolidation en cours" if language == "fr" else "Consolidation in progress") in html


@case("consolidation-register-http", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_register_http(user, language):
    game = services.create_game(user, "Occupation register", opponents="passive")
    game.state = occupied_state()
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    url = reverse("game", args=[game.id])
    response = client.get(url, {"tab": "mail", "mail": "schedule"})
    assert response.status_code == 200
    html = response.content.decode()
    assert ("En garnison" if language == "fr" else "On garrison duty") in html
    release = next(event for event in response.context["schedule"] if event["moon"] == 6)
    assert release["label"] == (
        "Départ automatique de la garnison" if language == "fr" else "Automatic garrison departure"
    )
    assert not response.context["marches"]
    help_html = client.get(url, {"tab": "help"}).content.decode()
    assert (
        "sans frais ni réservation d’hommes"
        if language == "fr"
        else "without fees or troop reservations"
    ) in help_html
    assert (
        "aucune nouvelle connexion" if language == "fr" else "do not need to log in again"
    ) in help_html
    assert (
        "après les besoins courants des foyers et de l’administration"
        if language == "fr"
        else "after routine household and administration needs"
    ) in help_html
    assert (
        "aucun retrait supplémentaire n’est appliqué chaque lune"
        if language == "fr"
        else "no additional deduction is applied each Moon"
    ) in help_html
    assert (
        "500 Mesures par personne présente couvre un mois de siège"
        if language == "fr"
        else "500 Measures per person present covers one Moon of siege"
    ) in help_html
