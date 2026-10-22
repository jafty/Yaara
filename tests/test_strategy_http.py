import json

import pytest
from django.test import Client
from django.urls import reverse

from simulation import engine, services
from simulation.models import Report
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case(
    "strategy-native-preparation",
    "Owner: compare origins and contextual help in the attack panel, not on the map",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_preparation(user, language):
    game = services.create_game(user, "Preparation", opponents="passive")
    game.state["cities"]["c1"].update(forge=2, siege=1, transport=2)
    game.state["cities"]["c4"].update(stock=1234567, tax=2345678, watch=2)
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    response = client.get(
        reverse("game", args=[game.id]), {"tab": "wars", "city": "c4", "men_c1": 50}
    )
    assert response.status_code == 200
    text = response.content.decode()
    assert "data-origin-means" in text and "data-raid-break-even" in text
    assert 'class="ledger-help"' in text and "<summary>" in text
    assert response.context["expedition_cost"] == 55000
    own = response.context["view"]["owned_cities"][0]
    assert (own["expedition_remaining"], own["expedition_food"]) == (845000, 475000)
    assert "1234567" not in text and "2345678" not in text
    assert "cohort_equipment" not in json.dumps(response.context["view"])


@case(
    "strategy-native-convoy",
    "Prompt I: ordinary signed preview and seal for local resource convoys",
)
def test_convoy(user):
    game = services.create_game(user, "Convoy", opponents="passive")
    client = Client()
    client.force_login(user)
    response = client.post(
        reverse("preview", args=[game.id]),
        {"kind": "convoy", "origin": "c1", "target": "c2", "cargo": "100000"},
    )
    assert response.status_code == 200
    assert response.context["order"]["cost"] == 110000
    assert "500" in response.content.decode()
    game.refresh_from_db()
    assert not game.state["orders"]
    sealed = client.post(
        reverse("confirm", args=[game.id]), {"payload": response.context["payload"]}
    )
    assert "tab=wars" in sealed.url
    register = client.get(sealed.url)
    assert [order["kind"] for order in register.context["section_orders"]] == ["convoy"]
    game.refresh_from_db()
    assert game.state["orders"][0]["funding"] == {"c1": 110000}
    for _ in range(3):
        game.refresh_from_db()
        services.tick(game.id, game.state["month"], user)
    game.refresh_from_db()
    assert game.state["cities"]["c2"]["stock"] == 1000000


@case(
    "strategy-dated-observations",
    "Prompt K: target knowledge comes only from dated immutable recipient reports",
)
def test_dated_observation(user):
    game = services.create_game(user, "Observation", opponents="passive")
    engine.confirm_order(
        game.state, "p1", {"kind": "raid", "target": "c4", "contributions": {"c1": 100}}, "raid"
    )
    engine.advance_month(game.state, "seen")
    events, _ = engine.advance_month(game.state, "seen")
    saved = [Report.objects.create(game=game, month=2, **event) for event in events]
    game.save()
    before = list(Report.objects.filter(game=game).values("id", "title", "body", "content"))
    client = Client()
    client.force_login(user)
    response = client.get(reverse("game", args=[game.id]), {"tab": "wars", "city": "c4"})
    observations = response.context["target_observations"]
    assert len(observations) == 1 and observations[0]["month"] == 2
    assert observations[0]["id"] in {row.pk for row in saved if row.recipient == "p1"}
    assert list(Report.objects.filter(game=game).values("id", "title", "body", "content")) == before
    letters = client.get(reverse("game", args=[game.id]), {"tab": "letters"}).content.decode()
    assert "tab=city&amp;city=c4" in letters


@case(
    "strategy-work-reserve-alert",
    "Owner: siege shortfall is visible before a local construction is sealed",
)
def test_work_alert(user):
    game = services.create_game(user, "Reserves", opponents="passive")
    game.state["cities"]["c1"]["stock"] = 600000
    game.save()
    client = Client()
    client.force_login(user)
    response = client.post(
        reverse("preview", args=[game.id]), {"kind": "irrigation", "cities": ["c1"]}
    )
    assert response.status_code == 200
    funding = response.context["funding"][0]
    assert (funding["remaining"], funding["siege_shortfall"]) == (300000, 200000)
    assert 'class="reserve-warning"' in response.content.decode()
