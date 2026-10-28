"""Post-playtest form feedback remains visible in focused action sheets."""

import re
from copy import deepcopy

import pytest
from django.urls import reverse

from simulation import engine
from tests.cases import case
from tests.test_map_workspace import open_board

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case(
    "feedback-threatened-origin-quote",
    "Owner: incoming attacks and siege-reserve warnings do not prevent an affordable expedition review",
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("stock", [900000, 50000], ids=["adequate-reserves", "siege-warning"])
def test_threatened_origin_quote(user, language, stock):
    game, client, url = open_board(user, language)
    game.state["cities"]["c3"]["watch"] = 1
    engine.confirm_order(
        game.state,
        "p2",
        {"kind": "raid", "target": "c3", "contributions": {"c4": 20}},
        "incoming-feedback",
    )
    engine.advance_month(game.state, "feedback-enemy-departure")
    game.state["cities"]["c3"]["stock"] = stock
    game.save()
    before = deepcopy(game.state)
    preparation = client.get(url, {"city": "c4", "action": "expedition", "men_c3": 20})
    origin = next(
        city for city in preparation.context["view"]["owned_cities"] if city["id"] == "c3"
    )
    assert origin["incoming_warnings"]
    assert bool(origin["expedition_siege_shortfall"]) == (stock == 50000)
    response = client.post(
        reverse("preview", args=[game.id]),
        {"kind": "raid", "target": "c4", "men_c3": "20"},
    )
    assert response.status_code == 200
    assert response.context["payload"]
    assert response.context["order"]["contributions"] == {"c3": 20}
    game.refresh_from_db()
    assert game.state == before


@case(
    "feedback-rejected-expedition-inline",
    "Owner: rejected troop preparation returns its quantities and explains the rejection inside the focused sheet",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_rejected_expedition_inline(user, language):
    game, client, _ = open_board(user, language)
    before = deepcopy(game.state)
    response = client.post(
        reverse("preview", args=[game.id]),
        {"kind": "raid", "target": "c4", "men_c3": "19"},
        follow=True,
    )
    assert response.status_code == 200
    html = response.content.decode()
    sheet = html.split('id="map-context"', 1)[1]
    feedback = re.search(
        r'<[^>]*class="sheet-feedback"[^>]*role="alert"[^>]*>(.*?)</div>', sheet, re.S
    )
    assert feedback, "The rejection must remain inside the visible action sheet."
    assert ("au moins 20" if language == "fr" else "at least 20") in feedback.group(1)
    assert re.search(r'name="men_c3"[^>]*value="19"', sheet)
    assert html.count("au moins 20" if language == "fr" else "at least 20") == 1
    game.refresh_from_db()
    assert game.state == before


@case(
    "feedback-manual-closure-quiet",
    "Owner: successful or repeated manual Moon closure returns to the map without a closure popup",
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("repeat", [False, True], ids=["first-closure", "duplicate-closure"])
def test_manual_closure_quiet(user, language, repeat):
    game, client, _ = open_board(user, language)
    url = reverse("advance", args=[game.id])
    if repeat:
        client.post(url, {"month": "1"}, follow=True)
    response = client.post(url, {"month": "1"}, follow=True)
    assert response.status_code == 200
    assert list(response.context["messages"]) == []
    assert 'class="notice success"' not in response.content.decode()
    assert 'class="notice info"' not in response.content.decode()
    game.refresh_from_db()
    assert game.state["month"] == 2


@case(
    "feedback-manual-closure-error",
    "Owner: suppressing Moon-closure success notices preserves actionable errors and leaves the game unchanged",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_manual_closure_error(user, language):
    game, client, _ = open_board(user, language)
    before = deepcopy(game.state)
    response = client.post(reverse("advance", args=[game.id]), {"month": "invalid"}, follow=True)
    assert response.status_code == 200
    assert 'class="notice error"' in response.content.decode()
    assert any(message.level == 40 and str(message) for message in response.context["messages"])
    game.refresh_from_db()
    assert game.state == before
