"""Council news, compact dates and local preparation accounts."""

import re
from uuid import uuid4

import pytest
from django.test import Client
from django.urls import reverse

from simulation import services
from simulation.models import Report
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case(
    "council-sealing-receipts",
    "Owner: Council omits sealing receipts while retaining departure, withdrawal and invalidation news and the immutable full archive",
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize("status", ["sealed", "departed", "cancelled", "invalidated"])
@pytest.mark.parametrize("original_archive", [False, True], ids=["structured", "original"])
def test_sealing_receipts(user, language, status, original_archive):
    game = services.create_game(user, "Receipt news", opponents="passive")
    moon = 1 if status == "sealed" else 30
    game.state["month"] = moon
    game.save()
    order = services.confirm(
        user, game.id, {"kind": "raid", "target": "c4", "contributions": {"c3": 20}}, uuid4(), moon
    )
    receipt = Report.objects.get(game=game, title="Décret scellé")
    if original_archive:
        receipt.content = {}
        receipt.save()
    if status == "cancelled":
        services.cancel(user, game.id, order["id"])
    elif status == "invalidated":
        game.refresh_from_db()
        game.state["cities"]["c3"]["stock"] = 0
        game.save()
    if status != "sealed":
        services.tick(game.id, moon, user)
    before = list(Report.objects.filter(game=game).values())
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    page = client.get(reverse("game", args=[game.id]))
    news = page.context["reports"]
    assert receipt.pk not in [report["id"] for report in news]
    expected = {
        "sealed": None,
        "departed": "Votre décret entre en vigueur",
        "cancelled": "Décret retiré",
        "invalidated": "Ordre invalidé",
    }[status]
    if expected:
        event = Report.objects.get(game=game, title=expected)
        assert event.pk in [report["id"] for report in news]
    else:
        assert page.context["view"]["sealed_count"] == 1
        assert "70" in page.content.decode() and 'id="orders-heading"' in page.content.decode()
    archive = client.get(reverse("game", args=[game.id]), {"tab": "letters"})
    assert f'id="report-{receipt.pk}"' in archive.content.decode()
    assert list(Report.objects.filter(game=game).values()) == before


@case(
    "council-receipt-kind-guard",
    "Owner: suppress only sealing order receipts, not unrelated event titles",
)
def test_receipt_kind_guard(user):
    game = services.create_game(user, "Guard", opponents="passive")
    event = Report.objects.create(
        game=game,
        recipient="p1",
        month=1,
        kind="work",
        title="Décret scellé",
        body="Distinct work event",
    )
    client = Client()
    client.force_login(user)
    page = client.get(reverse("game", args=[game.id]))
    assert event.pk in [report["id"] for report in page.context["reports"]]


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
