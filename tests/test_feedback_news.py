"""Recipient news and unresolved warnings remain distinct but both count."""

import re

import pytest

from simulation.models import Report
from tests.cases import case
from tests.test_map_workspace import open_board

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case(
    "feedback-envelope-total", "Owner: envelope counts latest recipient news plus unresolved alerts"
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("news,damaged", [(0, False), (2, False), (0, True), (2, True)])
def test_envelope_total(user, language, news, damaged):
    game, client, url = open_board(user, language)
    Report.objects.filter(game=game).delete()
    game.state["cities"]["c1"].update(damaged=damaged, integrity=50 if damaged else 100)
    game.save()
    for index in range(news):
        Report.objects.create(
            game=game, recipient="p1", month=1, kind="battle", title=f"News {index}", body="News"
        )
    Report.objects.create(
        game=game, recipient="p2", month=1, kind="battle", title="Private news", body="Private"
    )
    response = client.get(url, {"tab": "mail"})
    html = response.content.decode()
    count = news + int(damaged)
    assert response.context["attention"]["count"] == int(damaged)
    assert f'data-news-count="{news}"' in html
    assert f'data-alert-count="{int(damaged)}"' in html
    assert re.search(rf"<strong data-notification-count[^>]*>{count}</strong>", html)
    assert ('class="mail-alert-count"' in html) == damaged
    assert "data-read-report=" in html if news else "data-read-report=" not in html
    assert "Private news" not in html


@case(
    "feedback-latest-target-observation",
    "Owner: show only the newest stored recipient encounter observation",
)
@pytest.mark.parametrize("tab", ["map", "wars"])
def test_latest_target_observation(user, tab):
    game, client, url = open_board(user)
    for month, recipient, observation in [
        (2, "p1", "OLD OBSERVATION"),
        (3, "p1", "EARLIER SAME MOON"),
        (3, "p1", "LATEST OBSERVATION"),
        (4, "p2", "PRIVATE OBSERVATION"),
    ]:
        Report.objects.create(
            game=game,
            recipient=recipient,
            month=month,
            kind="battle",
            title="Encounter",
            body="Archived report",
            content={
                "city_id": "c4",
                "title": "Encounter",
                "body": "Archived report",
                "observation": observation,
            },
        )
    before = list(Report.objects.filter(game=game).values())
    response = client.get(url, {"tab": tab, "city": "c4"})
    assert [item["observation"] for item in response.context["target_observations"]] == [
        "LATEST OBSERVATION"
    ]
    html = response.content.decode()
    assert "LATEST OBSERVATION" in html
    assert "OLD OBSERVATION" not in html and "EARLIER SAME MOON" not in html
    assert "PRIVATE OBSERVATION" not in html
    assert list(Report.objects.filter(game=game).values()) == before
