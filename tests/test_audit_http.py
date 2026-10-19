"""Audit acceptance cases at the authorized application and presentation boundary."""

import re
import uuid
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from simulation import services
from simulation.models import Report, TickExecution
from tests.cases import case

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@case(
    "audit-scheduled-start",
    "Owner: automatic games begin only after explicit start and retries preserve deadlines",
)
def test_scheduled_start(user):
    game = services.create_game(user, "Start", mode="scheduled", opponents="passive")
    assert game.paused and game.deadline is None and game.state["awaiting_start"]
    client = Client()
    client.force_login(user)
    assert client.get(reverse("start", args=[game.id])).status_code == 405
    client.post(reverse("start", args=[game.id]))
    game.refresh_from_db()
    assert not game.paused and not game.state["awaiting_start"]
    assert timezone.now() < game.deadline <= timezone.now() + timedelta(minutes=10)
    deadline = game.deadline
    client.post(reverse("start", args=[game.id]))
    game.refresh_from_db()
    assert game.deadline == deadline


@case(
    "audit-cron-deadline", "Owner: cron resolves due UTC deadlines once, without a browser request"
)
def test_cron_deadline(user):
    game = services.create_game(user, "Cron", mode="scheduled", opponents="passive")
    services.start_calendar(user, game.id)
    game.refresh_from_db()
    game.deadline = timezone.now() - timedelta(seconds=1)
    game.save()
    original = game.deadline
    call_command("tick_due")
    call_command("tick_due")
    game.refresh_from_db()
    assert game.state["month"] == 2 and TickExecution.objects.filter(game=game).count() == 1
    assert game.deadline == original + timedelta(minutes=10)


@case("audit-news-links", "Owner: Council excerpts link to the complete authorized report")
@pytest.mark.parametrize("language", ["fr", "en"])
def test_full_report_link(user, language):
    game = services.create_game(user, "Reports", opponents="passive")
    report = Report.objects.create(
        game=game,
        recipient="p1",
        month=1,
        kind="battle",
        title="A raid",
        body="word " * 40 + "END-OF-REPORT",
    )
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = language
    html = client.get(reverse("game", args=[game.id])).content.decode()
    assert f"?tab=letters#report-{report.pk}" in html and 'href="#city-ledgers"' in html
    assert html.index('id="recent-letters"') < html.index('id="city-ledgers"')
    full = client.get(reverse("game", args=[game.id]), {"tab": "letters"}).content.decode()
    assert "END-OF-REPORT" in full and f'id="report-{report.pk}"' in full


@case("audit-close-discovery", "Owner: all main pages link to the Council closure review")
@pytest.mark.parametrize("tab", ["domain", "wars", "constructions", "city", "help"])
def test_closure_link(user, tab):
    game = services.create_game(user, "Close", opponents="passive")
    client = Client()
    client.force_login(user)
    html = client.get(reverse("game", args=[game.id]), {"tab": tab, "city": "c1"}).content.decode()
    assert "?tab=domain#turn-page" in html


@case("audit-start-authorization", "Owner: only the game owner can start its scheduled clock")
def test_start_authorization(user):
    from django.contrib.auth import get_user_model

    other = get_user_model().objects.create_user("start-stranger")
    game = services.create_game(user, "Private clock", mode="scheduled")
    client = Client()
    client.force_login(other)
    assert client.post(reverse("start", args=[game.id])).status_code == 403
    game.refresh_from_db()
    assert game.deadline is None and game.paused


@case(
    "audit-order-dates",
    "Owner: order history distinguishes future execution, active works, completion and cancellation",
)
@pytest.mark.parametrize("status", ["confirmed", "active", "completed", "cancelled", "invalidated"])
def test_order_dates(user, status):
    game = services.create_game(user, "Dates", opponents="passive")
    identifier = uuid.uuid4()
    services.confirm(user, game.id, {"kind": "storage", "cities": ["c1"]}, identifier, 1)
    if status == "cancelled":
        services.cancel(user, game.id, str(identifier))
    elif status != "confirmed":
        if status == "invalidated":
            game.refresh_from_db()
            game.state["cities"]["c1"]["stock"] = 0
            game.save()
        for moon in range(1, 6 if status == "completed" else 2):
            services.tick(game.id, moon, user)
    client = Client()
    client.force_login(user)
    client.cookies["django_language"] = "fr"
    html = client.get(reverse("game", args=[game.id])).content.decode()
    entry = re.search(r'<article class="order-entry">(.*?)</article>', html, re.S).group(1)
    assert "Entrée en vigueur prévue" not in entry
    if status == "confirmed":
        assert "Entrée en vigueur à la clôture de la lune 1." in entry
    elif status in ("active", "completed"):
        assert "Entré en vigueur à la lune 1." in entry
        assert (
            "Achèvement prévu à la clôture de la lune 5."
            if status == "active"
            else "Travaux achevés à la lune 5."
        ) in entry
    else:
        assert "réservations sont libérées" in entry
        assert "Entré en vigueur" not in entry


@case(
    "audit-start-retry-paused", "Owner: retrying start must not resume a deliberately paused game"
)
def test_start_retry_paused(user):
    game = services.create_game(user, "Pause", mode="scheduled", opponents="passive")
    services.start_calendar(user, game.id)
    services.toggle_pause(user, game.id)
    services.start_calendar(user, game.id)
    game.refresh_from_db()
    assert game.paused and game.deadline is None


@case("audit-start-manual", "Owner: starting a calendar cannot convert an existing manual game")
def test_start_manual(user):
    game = services.create_game(user, "Manual", opponents="passive")
    client = Client()
    client.force_login(user)
    assert client.post(reverse("start", args=[game.id])).status_code == 403
    game.refresh_from_db()
    assert game.mode == "manual" and game.deadline is None
