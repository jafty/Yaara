"""Language selection at the HTTP boundary; game commands keep their semantics."""

from copy import deepcopy
from uuid import uuid4

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

from simulation import services
from simulation.models import Report
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case(
    "raid-financial-letter-http",
    "Owner: bilingual raid letters distinguish military success and actual cash deficit with each payer's cost",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_raid_financial_letter_http(user, language):
    game = services.create_game(user, "Raid accounts", opponents="passive")
    game.state["cities"]["c4"].update(fideles=0, stock=300000)
    game.save()
    services.confirm(
        user,
        game.id,
        {"kind": "raid", "target": "c4", "contributions": {"c1": 10, "c2": 10, "c3": 10}},
        uuid4(),
        1,
    )
    for moon in (1, 2, 3):
        services.tick(game.id, moon, user)
    client = Client()
    client.force_login(user)
    html = client.get(
        reverse("game", args=[game.pk]), {"tab": "letters"}, HTTP_ACCEPT_LANGUAGE=language
    ).content.decode()
    if language == "fr":
        assert "Pillage réussi à Sefra" in html
        assert "Solde provisoire : déficit de 50\u202f000 Mesures" in html
        assert "Solde final des Mesures : déficit de 50\u202f000 Mesures" in html
        assert "Tamesh : 31\u202f667 Mesures payées" in html
    else:
        assert "Successful raid at Sefra" in html
        assert "Provisional balance: deficit of 50,000 Measures" in html
        assert "Final Measures balance: deficit of 50,000 Measures" in html
        assert "Tamesh: 31,667 Measures paid" in html
    council = client.get(
        reverse("game", args=[game.pk]), HTTP_ACCEPT_LANGUAGE=language
    ).content.decode()
    assert (
        "Solde final des Mesures : déficit de 50 000 Mesures"
        if language == "fr"
        else "Final Measures balance: deficit of 50,000 Measures"
    ) in council
    assert all(
        "Coût payé" not in report.body
        for report in Report.objects.filter(game=game, recipient="p2")
    )


@case(
    "language-selection",
    "Language decision: explicit selection persists and translates pages without changing the game",
)
@pytest.mark.parametrize(
    "language,heading",
    [
        pytest.param("fr", "Le conseil de votre maison", id="french"),
        pytest.param("en", "Your house council", id="english"),
    ],
)
def test_language_selection(user, game, language, heading):
    client = Client()
    client.force_login(user)
    before = deepcopy(game.state)
    response = client.post(
        reverse("set_language"),
        {"language": language, "next": reverse("game", args=[game.pk])},
        follow=True,
    )
    assert response.status_code == 200
    assert client.cookies[settings.LANGUAGE_COOKIE_NAME].value == language
    assert f'<html lang="{language}">' in response.content.decode()
    assert heading in response.content.decode()
    game.refresh_from_db()
    assert game.state == before


@case(
    "language-new-game-form",
    "Language decision: form labels and initial values use the selected language",
)
def test_english_game_form(user):
    client = Client()
    client.force_login(user)
    response = client.get(reverse("new_game"), HTTP_ACCEPT_LANGUAGE="en")
    assert "Name of your reign" in response.content.decode()
    assert "Your house" in response.content.decode()
    assert "The chronicles of Yaara" in response.content.decode()


@case(
    "language-legacy-report",
    "Archive decision: old unstructured reports and user-supplied names remain verbatim",
)
def test_legacy_reports_and_names_are_not_translated(user, game):
    game.title = "Confirmé"
    game.save(update_fields=["title"])
    Report.objects.create(
        game=game,
        recipient="p1",
        month=0,
        kind="work",
        title="Ancienne lettre",
        body="Améliorer le grenier",
    )
    client = Client()
    client.force_login(user)
    response = client.get(
        reverse("game", args=[game.pk]) + "?tab=letters", HTTP_ACCEPT_LANGUAGE="en"
    )
    text = response.content.decode()
    assert "Confirmé" in text
    assert "Améliorer le grenier" in text
    assert "The seal is yours" in text
    assert "I have opened the records of your three cities." in text


@case(
    "language-projection",
    "Language decision: translated JSON labels preserve identifiers and opponent secrecy",
)
def test_english_projection(user, game):
    client = Client()
    client.force_login(user)
    response = client.get(reverse("state", args=[game.pk]), HTTP_ACCEPT_LANGUAGE="en")
    view = response.json()["view"]
    assert view["equipment"] == "Ordinary equipment"
    assert view["work_actions"][0]["kind"] == "irrigation"
    assert view["work_actions"][0]["label"] == "Build canals"
    assert all("stock" not in city for city in view["cities"] if not city["owned"])


@case(
    "language-javascript",
    "Language decision: interactive mission help and calendar notices are translated",
)
def test_english_javascript_catalog():
    response = Client().get(reverse("javascript-catalog"), HTTP_ACCEPT_LANGUAGE="en")
    assert "The month is closed. We await news." in response.content.decode()
    assert "Our people will try to take the villages" in response.content.decode()
