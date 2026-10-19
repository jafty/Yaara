import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.db import close_old_connections, connection, connections, transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from simulation import engine, services
from simulation.models import (
    CommandReceipt,
    Game,
    Participant,
    Report,
    TargetEngagement,
    TickExecution,
)
from simulation.rules import RuleError
from tests.cases import case
from tests.stubs import FailingBoundary, FixedClock

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("test_static_storage")]


@pytest.fixture
def clock(monkeypatch):
    clock = FixedClock(datetime(2030, 1, 1, tzinfo=datetime_timezone.utc))
    monkeypatch.setattr(services.timezone, "now", clock)
    return clock


@pytest.fixture
def confirmed_raid(user, game):
    spec = {"kind": "raid", "target": "c4", "contributions": {"c3": 45}}
    request_id = uuid.uuid4()
    first = services.confirm(user, game.id, spec, request_id, 0)
    return spec, request_id, first


@case(
    "confirmation-retry-is-idempotent",
    "Design §26.2 Panne: retry after commit returns one receipt and target claim",
)
@pytest.mark.django_db
def test_confirmation_retry_is_idempotent(user, game, confirmed_raid):
    spec, request_id, first = confirmed_raid
    assert services.confirm(user, game.id, spec, request_id, 0) == first
    assert CommandReceipt.objects.count() == 1
    assert TargetEngagement.objects.count() == 1


@case(
    "cancellation-releases-database-target",
    "Design §26.2 Cible exclusive: cancellation removes the persisted target engagement",
)
@pytest.mark.django_db
def test_cancellation_releases_database_target(user, game, confirmed_raid):
    _, _, first = confirmed_raid
    services.cancel(user, game.id, first["id"])
    assert not TargetEngagement.objects.exists()


@case(
    "cancelled-receipt-retry-is-idempotent",
    "Design §26.2 Panne: cancelled receipt replay cannot reacquire a target",
)
@pytest.mark.django_db
def test_cancelled_receipt_retry_is_idempotent(user, game, confirmed_raid):
    spec, request_id, first = confirmed_raid
    services.cancel(user, game.id, first["id"])
    assert services.confirm(user, game.id, spec, request_id, 0)["status"] == "cancelled"
    assert CommandReceipt.objects.count() == 1
    assert not TargetEngagement.objects.exists()


@case(
    "tick-transaction-rolls-back",
    "Design §26.2 Panne: failed persistence rolls back state and tick execution",
)
@pytest.mark.django_db
def test_tick_transaction_rolls_back(user, game, monkeypatch):
    before = deepcopy(game.state)
    monkeypatch.setattr(services, "persist", FailingBoundary("simulated storage failure"))
    with pytest.raises(RuntimeError, match="storage failure"):
        services.tick(game.id, 1, user)
    game.refresh_from_db()
    assert game.state == before
    assert TickExecution.objects.count() == 0


@case(
    "tick-retry-does-not-resolve-twice",
    "Design §26.2 Deux ticks: retry after commit does not tax twice",
)
@pytest.mark.django_db
def test_tick_retry_does_not_resolve_twice(user, game):
    first, executed = services.tick(game.id, 1, user)
    assert executed
    second, executed = services.tick(game.id, 1, user)
    assert first.pk == second.pk and not executed
    game.refresh_from_db()
    assert game.state["month"] == 1
    assert game.state["cities"]["c1"]["tax"] == 100000


@case(
    "command-rolls-back-after-save-if-reporting-fails",
    "Design §26.2 Panne: failed report write rolls back saved state and receipt",
)
@pytest.mark.django_db
def test_command_rolls_back_after_save_if_reporting_fails(user, game, monkeypatch):
    monkeypatch.setattr(services.Report.objects, "bulk_create", FailingBoundary("disk full"))
    with pytest.raises(RuntimeError, match="disk full"):
        services.confirm(user, game.id, {"kind": "walls", "cities": ["c1"]}, uuid.uuid4(), 0)
    game.refresh_from_db()
    assert game.state["orders"] == []
    assert game.revision == 0
    assert not CommandReceipt.objects.exists()


@case(
    "stranger-cannot-command-game",
    "Design §26.2 Plusieurs parties: only members may command or tick their game",
)
@pytest.mark.django_db
@pytest.mark.parametrize("command", ["confirm", "tick"])
def test_stranger_cannot_command_game(user, game, command):
    stranger = get_user_model().objects.create_user("stranger")
    with pytest.raises(PermissionDenied):
        if command == "confirm":
            services.confirm(
                stranger, game.id, {"kind": "walls", "cities": ["c1"]}, uuid.uuid4(), 0
            )
        else:
            services.tick(game.id, 1, stranger)
    game.refresh_from_db()
    assert game.state["month"] == 0 and not game.state["orders"]


@case(
    "other-game-is-private",
    "Design §26.2 Plusieurs parties: cross-game identifiers cannot expose private state",
)
@pytest.mark.django_db
@pytest.mark.parametrize("route", ["game", "state"])
def test_other_game_is_private(user, route):
    stranger = get_user_model().objects.create_user("stranger")
    other = services.create_game(stranger, "Private", calendar_version=1, map_version=1)
    client = Client()
    client.force_login(user)
    assert client.get(reverse(route, args=[other.id])).status_code == 403


@case(
    "rival-reports-are-private",
    "Design §26.2 Information: letters are recipient-specific immutable projections",
)
@pytest.mark.django_db
def test_rival_reports_are_private(user, game):
    Report.objects.create(
        game=game,
        recipient="p2",
        month=0,
        kind="private",
        title="Hidden rival report",
        body="Secret military plan",
    )
    client = Client()
    client.force_login(user)
    response = client.get(reverse("game", args=[game.id]) + "?tab=letters")
    assert response.status_code == 200
    assert b"Hidden rival report" not in response.content
    assert b"Secret military plan" not in response.content


@case(
    "reading-or-preview-does-not-mutate",
    "Design commands: reading and quoting never mutate authoritative state",
)
@pytest.mark.django_db
@pytest.mark.parametrize("route", ["game", "state", "preview"])
def test_reading_or_preview_does_not_mutate(user, game, route):
    client = Client()
    client.force_login(user)
    before = deepcopy(game.state)
    url = reverse(route, args=[game.id])
    response = (
        client.post(url, {"kind": "walls", "cities": ["c1"]})
        if route == "preview"
        else client.get(url)
    )
    assert response.status_code == 200
    game.refresh_from_db()
    assert game.state == before and game.revision == 0
    assert not CommandReceipt.objects.exists()


@case(
    "signed-preview-confirmation",
    "Design commands: a signed preview creates one command despite duplicate HTTP delivery",
)
@pytest.mark.django_db
@pytest.mark.parametrize("deliveries", [pytest.param(1, id="initial"), pytest.param(2, id="retry")])
def test_signed_preview_confirmation(user, game, deliveries):
    client = Client()
    client.force_login(user)
    response = client.post(reverse("preview", args=[game.id]), {"kind": "walls", "cities": ["c1"]})
    payload = response.context["payload"]
    for _ in range(deliveries):
        assert (
            client.post(reverse("confirm", args=[game.id]), {"payload": payload}).status_code == 302
        )
    game.refresh_from_db()
    assert len(game.state["orders"]) == 1
    assert CommandReceipt.objects.count() == 1


@case("get-cannot-advance", "HTTP command boundary: GET requests cannot advance a game")
@pytest.mark.django_db
def test_get_cannot_advance(user, game):
    client = Client()
    client.force_login(user)
    assert client.get(reverse("advance", args=[game.id])).status_code == 405
    game.refresh_from_db()
    assert game.state["month"] == 0


@case("advance-requires-csrf", "HTTP command boundary: a tick POST requires a CSRF token")
@pytest.mark.django_db
def test_advance_requires_csrf(user, game):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    assert client.post(reverse("advance", args=[game.id]), {"month": 1}).status_code == 403
    game.refresh_from_db()
    assert game.state["month"] == 0


@case(
    "stale-preview-rejects-without-extra-reservation",
    "Design §26.2 Cible exclusive: a stale preview is rejected without new receipt",
)
@pytest.mark.django_db
def test_stale_preview_rejects_without_extra_reservation(user, game):
    services.confirm(user, game.id, {"kind": "storage", "cities": ["c2"]}, uuid.uuid4(), 0, 0)
    with pytest.raises(RuleError, match="devis"):
        services.confirm(user, game.id, {"kind": "walls", "cities": ["c1"]}, uuid.uuid4(), 0, 0)
    assert CommandReceipt.objects.count() == 1


@case(
    "scheduled-calendar",
    "Design scheduled games: server-controlled deadlines, pause/resume, bounded lateness",
)
@pytest.mark.django_db
@pytest.mark.parametrize(
    "scenario",
    ["manual-forbidden", "early", "paused", "resume", "on-time", "deadline-equality", "late-pause"],
)
def test_scheduled_calendar(user, clock, scenario):
    game = services.create_game(
        user, "Timed", mode="scheduled", opponents="passive", calendar_version=1, map_version=1
    )
    if scenario == "manual-forbidden":
        with pytest.raises(PermissionDenied):
            services.tick(game.id, 1, user)
    elif scenario == "early":
        with pytest.raises(RuleError, match="pas encore"):
            services.tick(game.id, 1)
    elif scenario in ("paused", "resume"):
        services.toggle_pause(user, game.id)
        game.refresh_from_db()
        assert game.paused and game.deadline is None
        if scenario == "paused":
            with pytest.raises(RuleError, match="pause"):
                services.confirm(
                    user, game.id, {"kind": "walls", "cities": ["c1"]}, uuid.uuid4(), 0
                )
        else:
            services.toggle_pause(user, game.id)
            game.refresh_from_db()
            assert not game.paused and game.deadline == clock() + timedelta(minutes=10)
    else:
        delay = {
            "on-time": timedelta(seconds=5),
            "deadline-equality": timedelta(0),
            "late-pause": timedelta(minutes=11),
        }[scenario]
        original_deadline = clock() - delay
        Game.objects.filter(pk=game.pk).update(deadline=original_deadline)
        execution, executed = services.tick(game.id, 1)
        game.refresh_from_db()
        if scenario == "late-pause":
            assert execution is None and not executed
            assert game.paused and game.deadline is None and game.state["month"] == 0
        else:
            assert executed and game.state["month"] == 1
            assert game.deadline == original_deadline + timedelta(minutes=10)


@case(
    "calendar-command-resolves-only-due-games",
    "Design calendar: repeated tick_due resolves only due scheduled games",
)
@pytest.mark.django_db
@pytest.mark.parametrize("scenario", ["due", "manual", "future"])
def test_calendar_command_resolves_only_due_games(user, clock, scenario):
    game = services.create_game(
        user,
        "Calendar",
        mode="manual" if scenario == "manual" else "scheduled",
        opponents="passive",
        calendar_version=1,
        map_version=1,
    )
    if scenario == "due":
        Game.objects.filter(pk=game.pk).update(deadline=clock() - timedelta(seconds=2))
    call_command("tick_due")
    call_command("tick_due")
    game.refresh_from_db()
    expected = int(scenario == "due")
    assert game.state["month"] == expected
    assert TickExecution.objects.filter(game=game).count() == expected


def concurrent_calls(callables):
    barrier = threading.Barrier(len(callables))

    def invoke(callback):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return callback()
        except RuleError as error:
            return error
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=len(callables)) as executor:
        return list(executor.map(invoke, callables))


@case(
    "postgres-competing-confirmations",
    "Design §26.2 Double dépense, double chantier, cible exclusive: real simultaneous confirmations",
)
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("scenario", ["spend", "slot", "target"])
def test_postgres_competing_confirmations(user, scenario):
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL row locks")
    game = services.create_game(
        user, "Concurrent", opponents="passive", calendar_version=1, map_version=1
    )
    if scenario == "spend":
        specs = [{"kind": "walls", "cities": ["c1"]}, {"kind": "walls", "cities": ["c2"]}]
    elif scenario == "slot":
        specs = [{"kind": "storage", "cities": ["c1"]}, {"kind": "walls", "cities": ["c1"]}]
    else:
        for city in game.state["cities"].values():
            city["stock"] = 2_400_000
        # Both participants border c4; the unique target covers all attackers/types.
        game.state["cities"]["c5"]["owner"] = "p3"
        game.save()
        specs = [
            {"kind": "raid", "target": "c4", "contributions": {"c3": 45}},
            {"kind": "capture", "target": "c4", "contributions": {"c5": 80}},
        ]
    second_user = user
    if scenario == "target":
        second_user = get_user_model().objects.create_user("other-attacker")
        Participant.objects.create(game=game, user=second_user, actor="p3")
    callbacks = [
        lambda: services.confirm(user, game.id, specs[0], uuid.uuid4(), 0),
        lambda: services.confirm(second_user, game.id, specs[1], uuid.uuid4(), 0),
    ]
    results = concurrent_calls(callbacks)
    assert sum(isinstance(result, RuleError) for result in results) == 1
    assert CommandReceipt.objects.filter(game=game).count() == 1
    game.refresh_from_db()
    assert len(game.state["orders"]) == 1
    engine.assert_invariants(game.state)
    if scenario == "target":
        assert TargetEngagement.objects.filter(game=game).count() == 1


@case(
    "postgres-two-ticks-pay-harvest-once",
    "Design §26.2 Deux ticks: real simultaneous year-end ticks produce one harvest",
)
@pytest.mark.django_db(transaction=True)
def test_postgres_two_ticks_pay_harvest_once(user):
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL row locks")
    game = services.create_game(
        user,
        "Concurrent ticks",
        version="V0",
        opponents="passive",
        calendar_version=1,
        map_version=1,
    )
    for month in range(1, 12):
        services.tick(game.id, month, user)
    results = concurrent_calls(
        [lambda: services.tick(game.id, 12, user), lambda: services.tick(game.id, 12, user)]
    )
    assert sum(result[1] for result in results) == 1
    game.refresh_from_db()
    assert game.state["cities"]["c1"]["stock"] == 1_800_000
    assert TickExecution.objects.filter(game=game, month=12).count() == 1


@case(
    "deadline-is-checked-after-waiting-for-postgres-lock",
    "Design §26.2 Clôture: deadline is rechecked after actual PostgreSQL lock wait",
)
@pytest.mark.django_db(transaction=True)
def test_deadline_is_checked_after_waiting_for_postgres_lock(user):
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL row locks")
    game = services.create_game(
        user, "Deadline", mode="scheduled", calendar_version=1, map_version=1
    )
    started = threading.Event()

    def command():
        close_old_connections()
        started.set()
        try:
            services.confirm(user, game.id, {"kind": "walls", "cities": ["c1"]}, uuid.uuid4(), 0)
        except RuleError as error:
            return str(error)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as executor:
        with transaction.atomic():
            locked = Game.objects.select_for_update().get(pk=game.pk)
            future = executor.submit(command)
            assert started.wait(timeout=5)
            deadline = time.monotonic() + 5
            waiting = False
            while time.monotonic() < deadline:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_stat_clear_snapshot()")
                    cursor.execute(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type = 'Lock' AND pid <> pg_backend_pid()"
                    )
                    waiting = cursor.fetchone()[0] > 0
                if waiting:
                    break
                time.sleep(0.01)
            assert waiting, "The second connection must actually wait on PostgreSQL"
            locked.deadline = timezone.now() - timedelta(seconds=1)
            locked.save(update_fields=["deadline"])
        assert "mois est clos" in future.result(timeout=5)
    assert not CommandReceipt.objects.filter(game=game).exists()
