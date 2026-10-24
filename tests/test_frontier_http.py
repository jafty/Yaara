"""Real persistence and bilingual disclosure checks for the frontier rules."""

import pytest
from django.test import Client
from django.urls import reverse

from simulation import engine, services
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]
REQ = "Owner October 24: paid warnings preserve private seals and disclose only earned intelligence"


@case("frontier-warning-http", REQ)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("watch", [0, 1, 2])
@pytest.mark.parametrize("departed", [False, True], ids=["sealed", "departed"])
def test_warning_http(user, language, watch, departed):
    game = services.create_game(user, "Frontier intelligence", opponents="passive")
    game.state["cities"]["c3"]["watch"] = watch
    engine.confirm_order(
        game.state,
        "p2",
        {
            "kind": "raid",
            "target": "c3",
            "contributions": {"c4": 45},
        },
        "hostile",
    )
    game.save()
    if departed:
        services.tick(game.id, 1, user)
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    url = reverse("game", args=[game.id])
    html = client.get(url).content.decode()
    visible = departed and watch > 0
    assert ('data-threat-city="c3"' in html) == visible
    assert game.reports.filter(recipient="p1", kind="warning").count() == int(visible)
    if visible:
        assert (
            "Expected arrival: Month 2." if language == "en" else "Arrivée prévue : lune 2."
        ) in html
    game.refresh_from_db()
    # Read the real authorized JSON boundary rather than the aggregate.
    view = client.get(url + "state/").json()["view"]
    city = next(c for c in view["owned_cities"] if c["id"] == "c3")
    assert bool(city["incoming_warnings"]) == visible
    if visible:
        assert ("kind" in city["incoming_warnings"][0]) == (watch == 2)
    assert all("stock" not in c for c in view["cities"] if not c["owned"])
    assert "combativity" not in str(view)
    help_text = client.get(url, {"tab": "help"}).content.decode()
    assert (
        "Sealed orders remain secret"
        if language == "en"
        else "Les ordres seulement scellés restent secrets"
    ) in help_text


@case(
    "frontier-restriction-http",
    "Owner October 24: conquered troops and their release Moon are explicit in own accounts",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_restriction_http(user, language):
    game = services.create_game(user, "Integration", opponents="passive")
    game.state["cities"]["c4"].update(owner="p1", restricted_fideles=100, restricted_until=5)
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    url = reverse("game", args=[game.id])
    phrase = "inherited Faithful" if language == "en" else "Fidèles hérités"
    assert phrase in client.get(url).content.decode()
    assert phrase in client.get(url, {"tab": "city", "city": "c4"}).content.decode()
