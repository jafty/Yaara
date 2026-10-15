import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from unittest.mock import patch

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
from simulation.projections import player_view
from simulation.rules import RuleError


@pytest.mark.django_db
def test_confirmation_idempotency_and_target_constraint(user, game):
    spec = {"kind": "raid", "target": "c4", "contributions": {"c3": 45}}
    request_id = uuid.uuid4()
    first = services.confirm(user, game.id, spec, request_id, 0)
    again = services.confirm(user, game.id, spec, request_id, 0)
    assert first == again
    assert CommandReceipt.objects.count() == 1
    assert TargetEngagement.objects.count() == 1
    services.cancel(user, game.id, first["id"])
    assert TargetEngagement.objects.count() == 0
    assert services.confirm(user, game.id, spec, request_id, 0)["status"] == "cancelled"
    assert CommandReceipt.objects.count() == 1


@pytest.mark.django_db
def test_tick_retry_and_complete_transaction_rollback(user, game):
    before = deepcopy(game.state)
    with patch(
        "simulation.services.persist", side_effect=RuntimeError("simulated storage failure")
    ):
        with pytest.raises(RuntimeError):
            services.tick(game.id, 1, user)
    game.refresh_from_db()
    assert game.state == before
    assert TickExecution.objects.count() == 0
    first, executed = services.tick(game.id, 1, user)
    assert executed
    second, executed = services.tick(game.id, 1, user)
    assert first.pk == second.pk and not executed
    game.refresh_from_db()
    assert game.state["month"] == 1
    assert game.state["cities"]["c1"]["tax"] == 100000


@pytest.mark.django_db
def test_command_rolls_back_after_save_if_reporting_fails(user, game):
    with patch(
        "simulation.services.Report.objects.bulk_create", side_effect=RuntimeError("disk full")
    ):
        with pytest.raises(RuntimeError):
            services.confirm(user, game.id, {"kind": "walls", "cities": ["c1"]}, uuid.uuid4(), 0)
    game.refresh_from_db()
    assert game.state["orders"] == []
    assert game.revision == 0
    assert not CommandReceipt.objects.exists()


@pytest.mark.django_db
def test_authorization_across_games_and_reports(user, game):
    stranger = get_user_model().objects.create_user("stranger")
    other = services.create_game(stranger, "Private")
    with pytest.raises(PermissionDenied):
        services.confirm(stranger, game.id, {"kind": "walls", "cities": ["c1"]}, uuid.uuid4(), 0)
    with pytest.raises(PermissionDenied):
        services.tick(game.id, 1, stranger)
    client = Client()
    client.force_login(user)
    assert client.get(reverse("game", args=[other.id])).status_code == 403
    assert client.get(reverse("state", args=[other.id])).status_code == 403
    Report.objects.create(
        game=game,
        recipient="p2",
        month=0,
        kind="private",
        title="Hidden rival report",
        body="Secret military plan",
    )
    response = client.get(reverse("game", args=[game.id]) + "?tab=letters")
    assert response.status_code == 200
    assert b"Hidden rival report" not in response.content
    assert b"Secret military plan" not in response.content


def test_projection_has_no_enemy_stats_seed_or_combativity():
    state = engine.new_state()
    engine.confirm_order(
        state, "p2", {"kind": "raid", "target": "c3", "contributions": {"c4": 45}}, "secret-order"
    )
    projection = player_view(state, "p1")
    enemy = next(city for city in projection["cities"] if city["id"] == "c4")
    assert not set(enemy) & {
        "population",
        "fideles",
        "stock",
        "tax",
        "irrigation",
        "storage",
        "works",
    }
    assert all("population" not in rank for rank in projection["ranking"])
    serialized = json.dumps(projection)
    assert "combativity" not in serialized
    assert "secret-order" not in serialized
    assert "cohorts" not in serialized


@pytest.mark.django_db
def test_preview_confirm_csrf_and_unchanged_gets(user, game):
    client = Client()
    client.force_login(user)
    before = deepcopy(game.state)
    for url in [reverse("game", args=[game.id]), reverse("state", args=[game.id])]:
        assert client.get(url).status_code == 200
    game.refresh_from_db()
    assert game.state == before
    response = client.post(reverse("preview", args=[game.id]), {"kind": "walls", "cities": ["c1"]})
    assert response.status_code == 200
    assert Game.objects.get(pk=game.pk).state == before
    payload = response.context["payload"]
    assert client.post(reverse("confirm", args=[game.id]), {"payload": payload}).status_code == 302
    game.refresh_from_db()
    assert len(game.state["orders"]) == 1
    assert client.post(reverse("confirm", args=[game.id]), {"payload": payload}).status_code == 302
    assert CommandReceipt.objects.count() == 1
    assert client.get(reverse("advance", args=[game.id])).status_code == 405
    secure_client = Client(enforce_csrf_checks=True)
    secure_client.force_login(user)
    assert secure_client.post(reverse("advance", args=[game.id]), {"month": 1}).status_code == 403


@pytest.mark.django_db
def test_stale_preview_rejects_without_extra_reservation(user, game):
    services.confirm(user, game.id, {"kind": "storage", "cities": ["c2"]}, uuid.uuid4(), 0, 0)
    with pytest.raises(RuleError, match="devis"):
        services.confirm(user, game.id, {"kind": "walls", "cities": ["c1"]}, uuid.uuid4(), 0, 0)
    assert CommandReceipt.objects.count() == 1


@pytest.mark.django_db
def test_scheduled_deadline_lateness_pause_and_resume(user):
    game = services.create_game(user, "Timed", mode="scheduled")
    with pytest.raises(PermissionDenied):
        services.tick(game.id, 1, user)
    with pytest.raises(RuleError, match="pas encore"):
        services.tick(game.id, 1)
    services.toggle_pause(user, game.id)
    game.refresh_from_db()
    assert game.paused and game.deadline is None
    with pytest.raises(RuleError, match="pause"):
        services.confirm(user, game.id, {"kind": "walls", "cities": ["c1"]}, uuid.uuid4(), 0)
    services.toggle_pause(user, game.id)
    game.refresh_from_db()
    assert not game.paused and game.deadline > timezone.now()
    original_deadline = timezone.now() - timedelta(seconds=5)
    Game.objects.filter(pk=game.pk).update(deadline=original_deadline)
    services.tick(game.id, 1)
    game.refresh_from_db()
    assert game.deadline == original_deadline + timedelta(minutes=10)
    Game.objects.filter(pk=game.pk).update(deadline=timezone.now() - timedelta(minutes=11))
    execution, executed = services.tick(game.id, 2)
    assert execution is None and not executed
    game.refresh_from_db()
    assert game.paused and game.state["month"] == 1


@pytest.mark.django_db
def test_calendar_command_resolves_only_due_games(user):
    due = services.create_game(user, "Due", mode="scheduled", opponents="passive")
    manual = services.create_game(user, "Manual", opponents="passive")
    future = services.create_game(user, "Future", mode="scheduled", opponents="passive")
    Game.objects.filter(pk=due.pk).update(deadline=timezone.now() - timedelta(seconds=2))
    call_command("tick_due")
    call_command("tick_due")
    due.refresh_from_db()
    manual.refresh_from_db()
    future.refresh_from_db()
    assert due.state["month"] == 1
    assert manual.state["month"] == future.state["month"] == 0
    assert TickExecution.objects.filter(game=due).count() == 1


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


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("scenario", ["spend", "slot", "target"])
def test_postgres_competing_confirmations(user, scenario):
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL row locks")
    game = services.create_game(user, "Concurrent", opponents="passive")
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


@pytest.mark.django_db(transaction=True)
def test_postgres_two_ticks_pay_harvest_once(user):
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL row locks")
    game = services.create_game(user, "Concurrent ticks", version="V0", opponents="passive")
    for month in range(1, 12):
        services.tick(game.id, month, user)
    results = concurrent_calls(
        [lambda: services.tick(game.id, 12, user), lambda: services.tick(game.id, 12, user)]
    )
    assert sum(result[1] for result in results) == 1
    game.refresh_from_db()
    assert game.state["cities"]["c1"]["stock"] == 1_800_000
    assert TickExecution.objects.filter(game=game, month=12).count() == 1


@pytest.mark.django_db(transaction=True)
def test_deadline_is_checked_after_waiting_for_postgres_lock(user):
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL row locks")
    game = services.create_game(user, "Deadline", mode="scheduled")
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
