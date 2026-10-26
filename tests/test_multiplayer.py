"""Shared rooms preserve seat identity, player secrecy and common deadlines."""

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.db import close_old_connections, connection, connections, transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from simulation import multiplayer, services
from simulation.archives import reign_archive
from simulation.models import Game, SeatIdentity, SharedInvitation, TickExecution
from simulation.rules import RuleError
from tests.cases import case
from tests.stubs import FixedClock
from tests.test_application import concurrent_calls

pytestmark = [
    pytest.mark.integration,
    pytest.mark.django_db,
    pytest.mark.usefixtures("test_static_storage"),
]


@pytest.fixture
def operator(user):
    user.user_permissions.add(Permission.objects.get(codename="manage_multiplayer_games"))
    return get_user_model().objects.get(pk=user.pk)


@pytest.fixture
def room(operator):
    return multiplayer.create_shared(
        operator, "Three houses", play_window="Saturday 20–22 UTC", auto_start=False
    )


@pytest.fixture
def seats(operator, room):
    rows = []
    for actor in ("p1", "p2", "p3"):
        invitation = multiplayer.issue_invitation(operator, room.pk, actor)
        identity = multiplayer.claim_invitation(multiplayer.invitation_token(invitation))
        rows.append(identity)
    return rows


@case("mp-create-operator", "Shared contract: nonplaying operator creates three human houses")
def test_create_room(operator, room):
    assert room.kind == "multiplayer" and room.lobby_status == "waiting"
    assert room.paused and room.deadline is None
    assert not room.memberships.exists()
    assert all(not row["bot"] for row in room.state["players"].values())
    assert len(room.state["cities"]) == 9


@case("mp-create-forbidden", "Shared contract: ordinary users cannot create official rooms")
def test_create_denied(user):
    with pytest.raises(PermissionDenied):
        multiplayer.create_shared(user, "Forbidden")


@case("mp-invite-get-readonly", "Shared contract: invitation landing never claims on GET")
def test_invite_get(operator, room):
    invitation = multiplayer.issue_invitation(operator, room.pk, "p2")
    response = Client().get(
        reverse("shared_invite", args=[multiplayer.invitation_token(invitation)])
    )
    assert response.status_code == 200 and b"data-seat-entry" in response.content
    assert not room.memberships.exists()
    assert b"same-origin" in response.content


@case("mp-invite-post-csrf", "Shared contract: automatic seat entry remains CSRF protected")
def test_invite_csrf(operator, room):
    invitation = multiplayer.issue_invitation(operator, room.pk, "p1")
    client = Client(enforce_csrf_checks=True)
    url = reverse("shared_invite", args=[multiplayer.invitation_token(invitation)])
    assert client.post(url).status_code == 403
    client.get(url)
    response = client.post(url, {"csrfmiddlewaretoken": client.cookies["csrftoken"].value})
    assert response.status_code == 302 and room.memberships.count() == 1


@case("mp-seat-replay", "Shared contract: secret invitation restores one persistent seat")
def test_seat_replay(operator, room):
    invitation = multiplayer.issue_invitation(operator, room.pk, "p1")
    token = multiplayer.invitation_token(invitation)
    first = multiplayer.claim_invitation(token)
    second = multiplayer.claim_invitation(token)
    assert first.pk == second.pk and room.memberships.count() == 1
    assert not first.has_usable_password() and not first.is_staff
    assert SeatIdentity.objects.filter(user=first).exists()


@case(
    "mp-account-alias",
    "Shared contract: registered login reaches linked seat without token login power",
)
def test_account_alias(operator, room, user):
    invitation = multiplayer.issue_invitation(operator, room.pk, "p2")
    seat = multiplayer.claim_invitation(multiplayer.invitation_token(invitation), account=user)
    assert seat.pk != user.pk and services.membership(room, user) == "p2"
    client = Client()
    client.force_login(user)
    response = client.get(reverse("shared_lobby", args=[room.pk]))
    assert response.status_code == 200


@case("mp-account-two-seats", "Shared contract: registered account cannot alias two houses")
def test_account_two_seats(operator, room, user):
    first = multiplayer.issue_invitation(operator, room.pk, "p1")
    second = multiplayer.issue_invitation(operator, room.pk, "p2")
    multiplayer.claim_invitation(multiplayer.invitation_token(first), account=user)
    with pytest.raises(RuleError):
        multiplayer.claim_invitation(multiplayer.invitation_token(second), account=user)


@case(
    "mp-invite-rotation", "Shared contract: rotation invalidates old secret link and seat session"
)
def test_rotation(operator, room):
    invitation = multiplayer.issue_invitation(operator, room.pk, "p1")
    old = multiplayer.invitation_token(invitation)
    client = Client()
    client.post(reverse("shared_invite", args=[old]))
    invitation = multiplayer.issue_invitation(operator, room.pk, "p1")
    assert client.get(reverse("shared_lobby", args=[room.pk])).status_code == 403
    with pytest.raises(PermissionDenied):
        multiplayer.resolve_invitation(old)
    response = client.post(
        reverse("shared_invite", args=[multiplayer.invitation_token(invitation)])
    )
    assert response.status_code == 302
    assert client.get(reverse("shared_lobby", args=[room.pk])).status_code == 200


@case("mp-invite-revoked", "Shared contract: revocation rejects the secret link")
def test_revoked(operator, room):
    invitation = multiplayer.issue_invitation(operator, room.pk, "p1")
    token = multiplayer.invitation_token(invitation)
    multiplayer.revoke_invitation(operator, room.pk, "p1")
    with pytest.raises(PermissionDenied):
        multiplayer.resolve_invitation(token)


@case("mp-start-needs-three", "Shared contract: start requires three claimed houses")
def test_incomplete_start(operator, room):
    with pytest.raises(RuleError):
        multiplayer.start_shared(operator, room.pk)
    room.refresh_from_db()
    assert room.paused and room.deadline is None


@case("mp-start-full-interval", "Shared contract: all claimed houses receive full first interval")
def test_full_first_interval(operator, room, seats, monkeypatch):
    instant = datetime(2030, 1, 1, 12, 9, 59, tzinfo=datetime_timezone.utc)
    monkeypatch.setattr(services.timezone, "now", FixedClock(instant))
    multiplayer.start_shared(operator, room.pk)
    room.refresh_from_db()
    assert room.deadline == instant + timedelta(minutes=10)
    assert not room.paused and room.lobby_status == "running"
    assert room.state["month"] == 1
    assert room.reports.filter(kind="calendar").count() == 3


@case("mp-start-replay", "Shared contract: repeated start cannot postpone deadline")
def test_start_replay(operator, room, seats):
    multiplayer.start_shared(operator, room.pk)
    room.refresh_from_db()
    deadline = room.deadline
    multiplayer.start_shared(operator, room.pk)
    room.refresh_from_db()
    assert room.deadline == deadline
    assert room.reports.filter(kind="calendar").count() == 3


@case(
    "mp-five-minute-final-moons",
    "Owner October 26: five-minute shared reigns close Moons 119 and 120, including tied results",
)
@pytest.mark.parametrize("calendar_version", [1, 2], ids=["legacy", "open-moon"])
@pytest.mark.parametrize("outcome", ["tie", "population", "cities"])
@pytest.mark.parametrize("delay", [0, 120], ids=["on-time", "cron-delay"])
def test_five_minute_final_moons(
    operator, room, seats, monkeypatch, calendar_version, outcome, delay
):
    instant = datetime(2026, 10, 26, 12, 0, tzinfo=datetime_timezone.utc)
    clock = FixedClock(instant + timedelta(seconds=delay))
    monkeypatch.setattr(services.timezone, "now", clock)
    multiplayer.start_shared(operator, room.pk)
    room.refresh_from_db()
    room.interval_minutes = 5
    room.state["calendar_version"] = calendar_version
    room.state["month"] = 119 if calendar_version == 2 else 118
    if outcome == "population":
        room.state["cities"]["c1"]["population"] += 100
    elif outcome == "cities":
        room.state["cities"]["c4"]["owner"] = "p1"
    room.deadline = instant
    room.save()

    call_command("tick_due")
    room.refresh_from_db()
    assert room.state["month"] == (120 if calendar_version == 2 else 119)
    assert room.state["status"] == "active" and room.state["result"] is None
    assert not room.paused and room.deadline == instant + timedelta(minutes=5)
    assert list(room.ticks.values_list("month", flat=True)) == [119]

    monkeypatch.setattr(
        services.timezone, "now", FixedClock(instant + timedelta(minutes=5, seconds=delay))
    )
    call_command("tick_due")
    call_command("tick_due")
    room.refresh_from_db()
    assert room.state["status"] == "finished" and room.state["month"] == 120
    assert room.deadline is None and not room.paused
    assert room.state["result"]["month"] == 120
    ranks = [row["rank"] for row in room.state["result"]["standings"]]
    assert ranks == {"tie": [1, 1, 1], "population": [1, 2, 2], "cities": [1, 2, 3]}[outcome]
    assert set(
        room.reports.filter(title="Le règne est achevé").values_list("recipient", flat=True)
    ) == {"p1", "p2", "p3"}
    execution, executed = services.tick(room.pk, 120)
    assert not executed and execution.month == 120
    assert TickExecution.objects.filter(game=room).count() == 2


@case(
    "mp-paris-deadline-display",
    "Owner October 26: player and operator deadlines show Paris time with automatic winter/summer changes",
)
@pytest.mark.parametrize("language", ["fr", "en"])
@pytest.mark.parametrize(
    "instant,display,offset",
    [
        pytest.param(datetime(2026, 10, 26, 12, 5), "13:05", "+01:00", id="winter"),
        pytest.param(datetime(2026, 7, 26, 12, 5), "14:05", "+02:00", id="summer"),
        pytest.param(datetime(2026, 10, 25, 0, 55), "02:55", "+02:00", id="before-winter"),
        pytest.param(datetime(2026, 10, 25, 1, 0), "02:00", "+01:00", id="after-winter"),
        pytest.param(datetime(2026, 3, 29, 0, 55), "01:55", "+01:00", id="before-summer"),
        pytest.param(datetime(2026, 3, 29, 1, 0), "03:00", "+02:00", id="after-summer"),
    ],
)
def test_paris_deadline_display(operator, room, seats, language, instant, display, offset):
    multiplayer.start_shared(operator, room.pk)
    room.refresh_from_db()
    room.deadline = instant.replace(tzinfo=datetime_timezone.utc)
    room.save()
    client = Client()
    client.cookies["django_language"] = language
    label = "heure de Paris" if language == "fr" else "Paris time"
    with timezone.override("UTC"):
        client.force_login(operator)
        operator_html = client.get(reverse("shared_operator_room", args=[room.pk])).content.decode()
        client.logout()
        invitation = room.invitations.get(actor="p1")
        client.post(reverse("shared_invite", args=[multiplayer.invitation_token(invitation)]))
        client.cookies["django_language"] = language
        player_html = client.get(reverse("game", args=[room.pk])).content.decode()
        state = client.get(reverse("state", args=[room.pk])).json()
    for html in (operator_html, player_html):
        assert f">{display} ({label})</time>" in html
        assert f'{display}:00{offset}"' in html
    assert player_html.count(f">{display} ({label})</time>") == 1
    assert datetime.fromisoformat(state["game"]["deadline"]) == room.deadline
    room.refresh_from_db()
    assert room.deadline == instant.replace(tzinfo=datetime_timezone.utc)


@case("mp-member-clock-denied", "Shared contract: ordinary seat cannot manage shared calendar")
@pytest.mark.parametrize("action", ["start", "pause", "advance"])
def test_member_clock_denied(operator, room, seats, action):
    multiplayer.start_shared(operator, room.pk)
    with pytest.raises(PermissionDenied):
        if action == "start":
            services.start_calendar(seats[0], room.pk)
        elif action == "pause":
            services.toggle_pause(seats[0], room.pk)
        else:
            services.tick(room.pk, 1, seats[0])


@case("mp-waiting-command-denied", "Shared contract: waiting rooms cannot accept orders")
def test_waiting_order(operator, room, seats):
    with pytest.raises(RuleError):
        services.confirm(
            seats[0], room.pk, {"kind": "irrigation", "cities": ["c1"]}, uuid.uuid4(), 1
        )


@case(
    "mp-lobby-start-transition",
    "Shared contract: waiting player is sent into Council after operator starts",
)
def test_lobby_transition(operator, room, seats):
    client = Client()
    client.force_login(operator)
    assert client.get(reverse("shared_operator_room", args=[room.pk])).status_code == 200
    invitation = SharedInvitation.objects.get(game=room, actor="p2")
    client.post(reverse("shared_invite", args=[multiplayer.invitation_token(invitation)]))
    assert client.get(reverse("game", args=[room.pk])).url == reverse(
        "shared_lobby", args=[room.pk]
    )
    multiplayer.start_shared(operator, room.pk)
    assert client.get(reverse("shared_lobby", args=[room.pk])).url == reverse(
        "game", args=[room.pk]
    )


@case(
    "mp-rival-private-revision",
    "Shared contract: private rival orders do not invalidate own preview",
)
@pytest.mark.parametrize("rival_action", ["seal", "cancel"])
def test_rival_revision(operator, room, seats, rival_action):
    multiplayer.start_shared(operator, room.pk)
    first_revision = multiplayer.visible_revision(room, "p1")
    order = services.confirm(
        seats[1], room.pk, {"kind": "irrigation", "cities": ["c4"]}, uuid.uuid4(), 1
    )
    if rival_action == "cancel":
        services.cancel(seats[1], room.pk, order["id"])
    room.refresh_from_db()
    assert multiplayer.visible_revision(room, "p1") == first_revision
    own = services.confirm(
        seats[0], room.pk, {"kind": "irrigation", "cities": ["c1"]}, uuid.uuid4(), 1, first_revision
    )
    assert own["actor"] == "p1"


@case("mp-own-revision-stale", "Shared contract: own new commitment invalidates prior preview")
def test_own_revision(operator, room, seats):
    multiplayer.start_shared(operator, room.pk)
    revision = multiplayer.visible_revision(room, "p1")
    services.confirm(seats[0], room.pk, {"kind": "irrigation", "cities": ["c1"]}, uuid.uuid4(), 1)
    with pytest.raises(RuleError):
        services.confirm(
            seats[0], room.pk, {"kind": "irrigation", "cities": ["c2"]}, uuid.uuid4(), 1, revision
        )


@case("mp-operator-live-private", "Shared contract: nonplaying operator has no player view")
@pytest.mark.parametrize("route", ["game", "state"])
def test_operator_no_player_view(operator, room, seats, route):
    multiplayer.start_shared(operator, room.pk)
    client = Client()
    client.force_login(operator)
    assert client.get(reverse(route, args=[room.pk])).status_code == 403


@case("mp-home-own-actor", "Shared contract: home card counts requesting participant cities")
def test_home_actor(operator, room, seats):
    multiplayer.start_shared(operator, room.pk)
    room.refresh_from_db()
    room.state["cities"]["c1"]["owner"] = "p2"
    room.save()
    invitation = SharedInvitation.objects.get(game=room, actor="p2")
    client = Client()
    client.post(reverse("shared_invite", args=[multiplayer.invitation_token(invitation)]))
    response = client.get(reverse("home"))
    assert response.context["games"][0]["cities"] == 4


@case("mp-own-archive-only", "Shared contract: shared participant can read own completed book only")
def test_own_archive(operator, room, seats):
    room.state["status"] = "finished"
    room.save()
    assert reign_archive(room, seats[0], "p1", "player")["scope"] == "player"
    with pytest.raises(PermissionDenied):
        reign_archive(room, seats[0], "p1", "all")


@case(
    "mp-all-archive-operator", "Shared contract: all-house book is operator-only after completion"
)
def test_operator_archive(operator, room, seats):
    with pytest.raises(PermissionDenied):
        reign_archive(room, operator, None, "all")
    room.state["status"] = "finished"
    room.save()
    assert reign_archive(room, operator, None, "all")["scope"] == "all"
    client = Client()
    client.force_login(operator)
    response = client.get(reverse("reign_archive", args=[room.pk]), {"scope": "all"})
    assert response.status_code == 200
    assert response.context["has_personal_book"] is False
    body = response.content.decode()
    assert f'href="{reverse("shared_operator_room", args=[room.pk])}"' in body
    assert 'href="?scope=player"' not in body
    assert 'class="resource-ribbon"' not in body
    assert 'data-section="domain"' not in body


@case("mp-cancelled-no-tick", "Shared contract: cancelled room refuses all calendar activity")
def test_cancelled(operator, room, seats):
    multiplayer.cancel_shared(operator, room.pk)
    with pytest.raises(RuleError):
        multiplayer.start_shared(operator, room.pk)
    call_command("tick_due")
    room.refresh_from_db()
    assert room.state["month"] == 1 and room.lobby_status == "cancelled"


@case("mp-operator-bootstrap", "Shared contract: explicit command grants operator permission")
def test_bootstrap(user):
    call_command("grant_operator", user.username)
    user = get_user_model().objects.get(pk=user.pk)
    assert multiplayer.is_operator(user) and not user.is_superuser


@case(
    "mp-state-revision-private",
    "Shared contract: state JSON contains own revision rather than shared mutation counter",
)
def test_state_revision(operator, room, seats):
    multiplayer.start_shared(operator, room.pk)
    invite = SharedInvitation.objects.get(game=room, actor="p1")
    client = Client()
    client.post(reverse("shared_invite", args=[multiplayer.invitation_token(invite)]))
    before = client.get(reverse("state", args=[room.pk])).json()
    services.confirm(seats[1], room.pk, {"kind": "irrigation", "cities": ["c4"]}, uuid.uuid4(), 1)
    after = client.get(reverse("state", args=[room.pk])).json()
    assert before == after


@case(
    "mp-clock-pause-common",
    "Shared contract: nonplaying operator pauses everyone and preserves time",
)
def test_common_pause(operator, room, seats, monkeypatch):
    now = datetime(2030, 1, 1, tzinfo=datetime_timezone.utc)
    clock = FixedClock(now)
    monkeypatch.setattr(services.timezone, "now", clock)
    multiplayer.start_shared(operator, room.pk)
    monkeypatch.setattr(services.timezone, "now", FixedClock(now + timedelta(minutes=2)))
    services.toggle_pause(operator, room.pk)
    room.refresh_from_db()
    assert room.paused and room.remaining_seconds == 480
    services.toggle_pause(operator, room.pk)
    room.refresh_from_db()
    assert not room.paused and room.deadline == now + timedelta(minutes=10)


@case(
    "mp-token-session-isolation",
    "Shared contract: secret seat never signs in its associated registered account",
)
def test_secret_login_is_seat_only(operator, room, user):
    invitation = multiplayer.issue_invitation(operator, room.pk, "p1")
    seat = multiplayer.claim_invitation(multiplayer.invitation_token(invitation), account=user)
    client = Client()
    client.post(reverse("shared_invite", args=[multiplayer.invitation_token(invitation)]))
    assert int(client.session["_auth_user_id"]) == seat.pk != user.pk
    assert not seat.has_perm("simulation.manage_multiplayer_games")


@case(
    "mp-operator-own-seat-session",
    "Shared contract: operator joins own house without losing management access",
)
def test_operator_keeps_session(operator, room):
    invitation = room.invitations.get(actor="p1")
    client = Client()
    client.force_login(operator)
    client.post(reverse("shared_invite", args=[multiplayer.invitation_token(invitation)]))
    assert int(client.session["_auth_user_id"]) == operator.pk
    assert services.membership(room, operator) == "p1"
    assert client.get(reverse("shared_operator_room", args=[room.pk])).status_code == 200


@case(
    "mp-operator-waiting-status",
    "Shared contract: operator can see newly claimed houses without reloading",
)
def test_operator_status(operator, room):
    client = Client()
    client.force_login(operator)
    url = reverse("shared_operator_state", args=[room.pk])
    assert client.get(url).json()["can_start"] is False
    for invitation in room.invitations.all():
        multiplayer.claim_invitation(multiplayer.invitation_token(invitation))
    state = client.get(url).json()
    assert state["can_start"] and all(state["seats"].values())
    assert "token" not in str(state)


@case(
    "mp-seat-session-version-before-command",
    "Shared contract: stale seat grants cannot seal commands after rotation",
)
def test_rotated_command_rejected(operator, room, seats):
    multiplayer.start_shared(operator, room.pk)
    invitation = room.invitations.get(actor="p1")
    client = Client()
    client.post(reverse("shared_invite", args=[multiplayer.invitation_token(invitation)]))
    quote = client.post(
        reverse("preview", args=[room.pk]), {"kind": "irrigation", "cities": ["c1"]}
    )
    multiplayer.issue_invitation(operator, room.pk, "p1")
    response = client.post(
        reverse("confirm", args=[room.pk]), {"payload": quote.context["payload"]}
    )
    assert response.status_code == 403
    room.refresh_from_db()
    assert not room.state["orders"]


@case("mp-start-revoked-seat", "Shared contract: start cannot strand a house behind a revoked link")
def test_revoked_start(operator, room, seats):
    multiplayer.revoke_invitation(operator, room.pk, "p2")
    with pytest.raises(RuleError):
        multiplayer.start_shared(operator, room.pk)
    assert not multiplayer.can_start(room)


@case(
    "mp-postgres-seat-replay-race",
    "Shared contract: simultaneous bearer entry creates exactly one seat identity",
)
@pytest.mark.django_db(transaction=True)
def test_concurrent_seat_claim(operator, room):
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL locks")
    token = multiplayer.invitation_token(room.invitations.get(actor="p1"))
    results = concurrent_calls(
        [lambda: multiplayer.claim_invitation(token), lambda: multiplayer.claim_invitation(token)]
    )
    assert results[0].pk == results[1].pk and room.memberships.count() == 1


@case(
    "mp-postgres-account-seats-race",
    "Shared contract: simultaneous seat links cannot grant two houses to one account",
)
@pytest.mark.django_db(transaction=True)
def test_concurrent_account_claim(operator, room):
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL locks")
    tokens = [
        multiplayer.invitation_token(room.invitations.get(actor=actor)) for actor in ("p1", "p2")
    ]
    results = concurrent_calls(
        [
            lambda token=token: multiplayer.claim_invitation(token, account=operator)
            for token in tokens
        ]
    )
    assert sum(isinstance(result, RuleError) for result in results) == 1
    assert room.memberships.count() == 1


@case(
    "mp-postgres-parallel-valid-orders",
    "Shared contract: independent human seals never conflict through shared revision",
)
@pytest.mark.django_db(transaction=True)
def test_concurrent_player_orders(operator, room, seats):
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL locks")
    multiplayer.start_shared(operator, room.pk)
    revision = multiplayer.visible_revision(room, "p1")
    results = concurrent_calls(
        [
            lambda: services.confirm(
                seats[0],
                room.pk,
                {"kind": "irrigation", "cities": ["c1"]},
                uuid.uuid4(),
                1,
                revision,
            ),
            lambda: services.confirm(
                seats[1],
                room.pk,
                {"kind": "irrigation", "cities": ["c4"]},
                uuid.uuid4(),
                1,
                revision,
            ),
        ]
    )
    assert all(isinstance(result, dict) for result in results)
    room.refresh_from_db()
    assert len(room.state["orders"]) == 2


@case(
    "mp-postgres-revoke-waiting-command",
    "Shared contract: command waiting on lock rechecks rotated seat grant",
)
@pytest.mark.django_db(transaction=True)
def test_revocation_during_wait(operator, room, seats):
    if connection.vendor != "postgresql":
        pytest.skip("Requires real PostgreSQL locks")
    multiplayer.start_shared(operator, room.pk)
    client = Client()
    invitation = room.invitations.get(actor="p1")
    client.post(reverse("shared_invite", args=[multiplayer.invitation_token(invitation)]))
    quote = client.post(
        reverse("preview", args=[room.pk]), {"kind": "irrigation", "cities": ["c1"]}
    )
    payload = quote.context["payload"]
    started = threading.Event()

    def seal():
        close_old_connections()
        try:
            started.set()
            return client.post(reverse("confirm", args=[room.pk]), {"payload": payload}).status_code
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as executor:
        with transaction.atomic():
            Game.objects.select_for_update().get(pk=room.pk)
            future = executor.submit(seal)
            assert started.wait(timeout=5)
            until = time.monotonic() + 5
            waiting = False
            while time.monotonic() < until:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_stat_clear_snapshot()")
                    cursor.execute(
                        "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND pid<>pg_backend_pid()"
                    )
                    waiting = cursor.fetchone()[0] > 0
                if waiting:
                    break
                time.sleep(0.01)
            assert waiting, "The command must really wait for the game lock"
            multiplayer.issue_invitation(operator, room.pk, "p1")
        assert future.result(timeout=5) == 403
    room.refresh_from_db()
    assert not room.state["orders"]
