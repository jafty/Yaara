"""Council news, compact dates and local preparation accounts."""

import re

import pytest
from django.test import Client
from django.urls import reverse

from simulation import services
from simulation.models import Report
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case("council-complete-moon-news", "Owner: preview every last-Moon event without a count limit")
@pytest.mark.parametrize("closed,count", [(0, 7), (1, 7), (12, 105)])
@pytest.mark.parametrize("calendar_version", [1, 2])
def test_complete_moon_news(user, closed, count, calendar_version):
    game = services.create_game(
        user, "News", opponents="passive", calendar_version=calendar_version
    )
    game.state["month"] = closed + int(calendar_version == 2)
    game.save()
    Report.objects.filter(game=game).delete()
    moon = closed or int(calendar_version == 2)
    expected = [
        Report.objects.create(
            game=game, recipient="p1", month=moon, kind="battle", title=f"Event {i}", body="News"
        ).pk
        for i in range(count)
    ]
    Report.objects.create(
        game=game, recipient="p2", month=moon, kind="battle", title="PRIVATE", body="PRIVATE"
    )
    if closed > 1:
        Report.objects.create(
            game=game, recipient="p1", month=1, kind="battle", title="OLD", body="OLD"
        )
    client = Client()
    client.force_login(user)
    page = client.get(reverse("game", args=[game.id]))
    assert [row["id"] for row in page.context["reports"]] == expected[::-1]
    assert b"PRIVATE" not in page.content and b">OLD<" not in page.content
    archive = client.get(reverse("game", args=[game.id]), {"tab": "letters"})
    assert all(f'id="report-{pk}"' in archive.content.decode() for pk in expected)


@case("council-quiet-moon", "Owner: a quiet closed Moon does not repeat older events")
def test_quiet_moon(user):
    game = services.create_game(user, "Quiet", opponents="passive")
    game.state["month"] = 3
    game.save()
    client = Client()
    client.force_login(user)
    assert client.get(reverse("game", args=[game.id])).context["reports"] == []


@case("header-moon-number", "Owner: the resource header shows the current Moon with its icon")
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("finished", [False, True])
@pytest.mark.parametrize("calendar_version", [1, 2])
def test_header_moon(user, language, finished, calendar_version):
    game = services.create_game(
        user, "Moon", opponents="passive", calendar_version=calendar_version
    )
    game.state["month"] = 24 if finished else 12 + int(calendar_version == 2)
    game.state["status"] = "finished" if finished else "active"
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    html = client.get(reverse("game", args=[game.id])).content.decode()
    ribbon = re.search(r'<div class="resource-ribbon".*?</div>', html, re.S).group()
    assert 'data-icon="moon"' in ribbon
    assert f"<strong>{24 if finished else 13}</strong>" in ribbon
    assert ("Lune" if language == "fr" else "Moon") in ribbon
    assert "Récolte dans" not in ribbon and "Harvest in" not in ribbon


@case("council-local-preparation", "Owner: each city shows its accrued unavailable levy in Council")
@pytest.mark.parametrize("language", ["fr", "en"])
def test_local_preparation(user, language):
    game = services.create_game(user, "Levies", opponents="passive")
    for city, tax in zip(("c1", "c2", "c3"), (12345, 45678, 78901)):
        game.state["cities"][city]["tax"] = tax
    game.save()
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    html = client.get(reverse("game", args=[game.id])).content.decode()
    for city, tax in zip(("c1", "c2", "c3"), (12345, 45678, 78901)):
        entry = re.search(rf'id="city-{city}".*?</li>', html, re.S).group()
        assert f"<dd>{tax}</dd>" in entry.replace("\xa0", "").replace(",", "")
        assert ("Prélèvement en préparation" if language == "fr" else "Accruing levy") in entry
    assert ("encore indisponibles" if language == "fr" else "not yet available") in html


@case("news-event-icons", "Owner: report types have decorative icons while titles remain readable")
@pytest.mark.parametrize(
    "kind,icon",
    [
        ("battle", "blades"),
        ("return", "return"),
        ("work", "works"),
        ("harvest", "grain"),
        ("order", "book"),
        ("sovereignty", "council"),
        ("result", "council"),
        ("welcome", "book"),
        ("unknown", "book"),
    ],
)
def test_event_icons(user, kind, icon):
    game = services.create_game(user, "Icons", opponents="passive")
    report = Report.objects.create(
        game=game, recipient="p1", month=1, kind=kind, title="Visible title", body="News"
    )
    client = Client()
    client.force_login(user)
    html = client.get(reverse("game", args=[game.id])).content.decode()
    entry = re.search(rf'id="report-{report.pk}".*?</article>', html, re.S).group()
    assert f'data-icon="{icon}"' in entry and 'aria-hidden="true"' in entry
    assert "Visible title" in entry
