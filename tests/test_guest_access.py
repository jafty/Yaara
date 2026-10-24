"""Guest entry and claims retain the ordinary private-game authorization boundary."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from threading import Barrier, Event

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections, connection, connections
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from simulation import guest_services, services
from simulation.guest_models import GuestCreationBucket, GuestIdentity
from simulation.models import Game, Participant, Report, SeatIdentity
from simulation.rules import RuleError
from tests.cases import case

pytestmark = [
    pytest.mark.integration,
    pytest.mark.django_db,
    pytest.mark.usefixtures("test_static_storage"),
]


@pytest.fixture
def guest(settings):
    settings.GUEST_PLAY_ENABLED = True
    return guest_services.start_guest(uuid.uuid4(), "test-network")


@case("guest-start-current-preset", "Guest access: one private full current manual solo")
def test_guest_preset(guest):
    assert guest.game.mode == "manual" and guest.game.deadline is None
    assert guest.game.state["config"]["reign_months"] == 120
    assert guest.game.state["economy_version"] == 4
    assert guest.game.state["strategy_version"] == 2
    assert sum(city["stock"] for city in guest.game.state["cities"].values()) == 8_100_000
    assert list(guest.game.memberships.values_list("actor", flat=True)) == ["p1"]
    assert not guest.user.has_usable_password()
    assert not guest.user.is_staff and not guest.user.is_superuser
    assert guest_services.is_guest(guest.user)
    assert Report.objects.filter(game=guest.game).count() == 1


@case("guest-start-retry", "Guest access: duplicate start intent returns the same saved game")
def test_guest_retry(guest):
    again = guest_services.start_guest(guest.start_key, "test-network")
    assert again.pk == guest.pk and again.game_id == guest.game_id
    assert Game.objects.count() == 1 and get_user_model().objects.count() == 1


@case("guest-start-disabled", "Guest access: operator flag closes new creation")
def test_disabled(settings):
    settings.GUEST_PLAY_ENABLED = False
    with pytest.raises(PermissionDenied):
        guest_services.start_guest(uuid.uuid4(), "test-network")
    assert not Game.objects.exists() and not GuestIdentity.objects.exists()


@case("guest-start-throttle", "Guest access: shared database creation budget is enforced")
def test_throttle(guest, settings):
    settings.GUEST_STARTS_PER_HOUR = 1
    with pytest.raises(RuleError):
        guest_services.start_guest(uuid.uuid4(), "test-network")
    assert Game.objects.count() == 1
    assert guest_services.start_guest(guest.start_key, "test-network").pk == guest.pk


@case("guest-start-rollback", "Guest access: failed game creation leaves no guest or quota spend")
def test_start_rollback(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("storage unavailable")

    monkeypatch.setattr(services, "create_game", fail)
    with pytest.raises(RuntimeError, match="storage unavailable"):
        guest_services.start_guest(uuid.uuid4(), "test-network")
    assert not GuestIdentity.objects.exists() and not Game.objects.exists()
    assert not GuestCreationBucket.objects.exists() and not get_user_model().objects.exists()


@case("guest-only-own-game", "Guest access: membership blocks another temporary player's game")
def test_other_game(guest):
    other = guest_services.start_guest(uuid.uuid4(), "other-network")
    with pytest.raises(PermissionDenied):
        services.membership(other.game, guest.user)


@case("guest-new-account-same-game", "Guest access: claiming credentials preserves all progress")
def test_new_claim(guest):
    services.tick(guest.game_id, 1, guest.user)
    guest.game.refresh_from_db()
    before = deepcopy(guest.game.state)
    participant_pk = Participant.objects.get(game=guest.game).pk
    claimed = guest_services.claim_guest_new(guest.user, "new-ruler", "Strong-test-pass-937!")
    guest.refresh_from_db()
    guest.game.refresh_from_db()
    assert claimed.pk == guest.user_id and claimed.check_password("Strong-test-pass-937!")
    assert guest.claimed_at and not guest_services.is_guest(claimed)
    assert guest.game.state == before and guest.game.owner_id == claimed.pk
    assert Participant.objects.get(game=guest.game).pk == participant_pk


@case("guest-new-account-collision", "Guest access: taken username cannot mutate guest progress")
def test_claim_username_collision(guest, user):
    username = guest.user.username
    with pytest.raises(RuleError):
        guest_services.claim_guest_new(guest.user, user.username, "Strong-test-pass-937!")
    guest.user.refresh_from_db()
    assert guest.user.username == username and not guest.user.has_usable_password()
    assert guest_services.is_guest(guest.user)


@case(
    "guest-new-account-password", "Guest access: password validation precedes credential mutation"
)
def test_claim_weak_password(guest):
    with pytest.raises(RuleError):
        guest_services.claim_guest_new(guest.user, "new-ruler", "123")
    assert guest_services.is_guest(guest.user)
    guest.user.refresh_from_db()
    assert not guest.user.has_usable_password()


@case("guest-new-account-signup-disabled", "Guest access: claim honors durable signup switch")
def test_claim_disabled(guest, settings):
    settings.SIGNUP_ENABLED = False
    with pytest.raises(PermissionDenied):
        guest_services.claim_guest_new(guest.user, "new-ruler", "Strong-test-pass-937!")
    assert guest_services.is_guest(guest.user)


@case(
    "guest-existing-account-transfer",
    "Guest access: authenticated attachment preserves participant",
)
def test_attach(guest, user):
    before = deepcopy(guest.game.state)
    participant = Participant.objects.get(game=guest.game)
    guest_services.attach_guest_to_user(guest.user, user)
    guest.game.refresh_from_db()
    participant.refresh_from_db()
    guest.refresh_from_db()
    assert guest.game.owner_id == user.pk and participant.user_id == user.pk
    assert guest.game.state == before and guest.claimed_at
    assert not get_user_model().objects.get(pk=guest.user_id).is_active
    assert guest_services.attach_guest_to_user(guest.user, user).pk == guest.game_id


@case("guest-existing-account-cap", "Guest access: full destination never loses or evicts a reign")
def test_attach_cap(guest, user):
    Game.objects.bulk_create(
        [Game(owner=user, title=f"Saved {index}", state={}, seed="seed") for index in range(30)]
    )
    with pytest.raises(RuleError):
        guest_services.attach_guest_to_user(guest.user, user)
    guest.game.refresh_from_db()
    assert guest.game.owner_id == guest.user_id and guest_services.is_guest(guest.user)


@case("guest-existing-account-temporary", "Guest access: a guest target is not an account claim")
def test_attach_guest_destination(guest):
    other = guest_services.start_guest(uuid.uuid4(), "other-network")
    with pytest.raises(PermissionDenied):
        guest_services.attach_guest_to_user(guest.user, other.user)
    assert guest_services.is_guest(guest.user)


@case("guest-cleanup-expired", "Guest access: only expired unclaimed private solos are deleted")
def test_cleanup_expired(guest):
    GuestIdentity.objects.filter(pk=guest.pk).update(expires_at=timezone.now() - timedelta(days=1))
    result = guest_services.cleanup_expired_guests()
    assert result["removed"] == 1
    assert not Game.objects.filter(pk=guest.game_id).exists()
    assert not get_user_model().objects.filter(pk=guest.user_id).exists()


@case("guest-cleanup-active", "Guest access: retained activity protects a guest game")
def test_cleanup_active(guest):
    assert guest_services.cleanup_expired_guests()["removed"] == 0
    assert Game.objects.filter(pk=guest.game_id).exists()


@case("guest-cleanup-promoted", "Guest access: promoted accounts never cascade away")
def test_cleanup_claimed(guest):
    guest_services.claim_guest_new(guest.user, "saved-ruler", "Strong-test-pass-937!")
    GuestIdentity.objects.filter(pk=guest.pk).update(expires_at=timezone.now() - timedelta(days=1))
    assert guest_services.cleanup_expired_guests()["removed"] == 0
    assert Game.objects.filter(pk=guest.game_id).exists()


@case(
    "guest-cleanup-shared-membership", "Guest access: unexpected shared membership blocks deletion"
)
def test_cleanup_shared(guest, user):
    shared = services.create_game(user, "Other game")
    Participant.objects.create(game=shared, user=guest.user, actor="p2")
    GuestIdentity.objects.filter(pk=guest.pk).update(expires_at=timezone.now() - timedelta(days=1))
    assert guest_services.cleanup_expired_guests()["skipped"] == 1
    assert Game.objects.filter(pk=guest.game_id).exists()


@case("guest-touch-expiry", "Guest access: an expired identity cannot silently revive itself")
def test_touch_expired(guest):
    GuestIdentity.objects.filter(pk=guest.pk).update(
        expires_at=timezone.now() - timedelta(seconds=1)
    )
    with pytest.raises(PermissionDenied):
        guest_services.touch_guest(guest.user)


@case("guest-public-entry", "Guest access: public landing reads create no game")
@pytest.mark.parametrize("language", ["fr", "en"])
def test_public_entry(language):
    client = Client()
    client.cookies["django_language"] = language
    response = client.get(reverse("home"))
    assert response.status_code == 200 and "data-guest-entry" in response.content.decode()
    assert not Game.objects.exists() and not get_user_model().objects.exists()


@case("guest-http-start", "Guest access: native form opens Council directly without setup")
def test_http_start():
    client = Client()
    client.get(reverse("home"))
    key = client.session["guest_start_key"]
    response = client.post(reverse("guest_start"), {"start_key": key})
    identity = GuestIdentity.objects.get()
    assert response.status_code == 302 and response["Location"] == reverse(
        "game", args=[identity.game_id]
    )
    council = client.get(response["Location"])
    assert council.status_code == 200 and "data-guest-access" in council.content.decode()
    assert "data-prologue-page" not in council.content.decode()


@case("guest-http-start-method", "Guest access: GET cannot start a game")
def test_http_start_get():
    assert Client().get(reverse("guest_start")).status_code == 405
    assert not Game.objects.exists()


@case("guest-http-start-intent", "Guest access: another session cannot replay a start intent")
def test_http_start_wrong_intent():
    client = Client()
    client.get(reverse("home"))
    assert client.post(reverse("guest_start"), {"start_key": str(uuid.uuid4())}).status_code == 403
    assert not Game.objects.exists()


@case(
    "guest-http-existing-authentication",
    "Guest access: wrong destination password leaves guest usable",
)
def test_http_attach_wrong_password(guest, user):
    client = Client()
    client.force_login(guest.user)
    response = client.post(
        reverse("guest_attach"), {"username": user.username, "password": "wrong"}
    )
    assert response.status_code == 200
    assert int(client.session["_auth_user_id"]) == guest.user_id
    assert guest_services.is_guest(guest.user)


@case("guest-http-claim-preserves-game", "Guest access: saving credentials signs into same game")
def test_http_claim(guest):
    client = Client()
    client.force_login(guest.user)
    response = client.post(
        reverse("guest_claim"),
        {
            "username": "new-ruler",
            "password1": "Strong-test-pass-937!",
            "password2": "Strong-test-pass-937!",
            "next": "https://outside.example/",
        },
    )
    assert response.status_code == 302 and response["Location"] == reverse(
        "game", args=[guest.game_id]
    )
    assert int(client.session["_auth_user_id"]) == guest.user_id
    assert client.get(response["Location"]).status_code == 200


@case("guest-http-start-csrf", "Guest access: CSRF rejection creates no anonymous identities")
def test_http_start_csrf():
    client = Client(enforce_csrf_checks=True)
    client.get(reverse("home"))
    response = client.post(reverse("guest_start"), {"start_key": client.session["guest_start_key"]})
    assert response.status_code == 403 and not Game.objects.exists()


@case(
    "guest-http-claim-mismatch", "Guest access: mismatched confirmation preserves temporary access"
)
def test_http_claim_mismatch(guest):
    client = Client()
    client.force_login(guest.user)
    response = client.post(
        reverse("guest_claim"),
        {
            "username": "saved-ruler",
            "password1": "Strong-test-pass-937!",
            "password2": "different",
        },
    )
    assert response.status_code == 200 and guest_services.is_guest(guest.user)


@case(
    "guest-seat-target-rejected",
    "Guest access: invitation possession cannot acquire solo credentials",
)
def test_attach_seat_rejected(guest):
    seat = get_user_model().objects.create_user("seat-only")
    SeatIdentity.objects.create(user=seat)
    with pytest.raises(PermissionDenied):
        guest_services.attach_guest_to_user(guest.user, seat)
    assert guest_services.is_guest(guest.user)


@case(
    "guest-seat-registered-gate",
    "Guest access: a seat principal is not a durable registered account",
)
def test_seat_registered_gate():
    seat = get_user_model().objects.create_user("seat-only")
    SeatIdentity.objects.create(user=seat)
    assert not guest_services.is_guest(seat)
    with pytest.raises(PermissionDenied):
        guest_services.require_registered(seat)


@case(
    "guest-cleanup-seat-exclusion",
    "Guest access: cleanup categorically excludes invitation identities",
)
def test_cleanup_seat(guest):
    SeatIdentity.objects.create(user=guest.user)
    GuestIdentity.objects.filter(pk=guest.pk).update(expires_at=timezone.now() - timedelta(days=1))
    assert guest_services.cleanup_expired_guests()["skipped"] == 1
    assert get_user_model().objects.filter(pk=guest.user_id).exists()


@case(
    "guest-restore-server-entitlement",
    "Guest access: invitation handoff resumes the original same-browser solo",
)
def test_restore_origin(guest):
    seat = get_user_model().objects.create_user("seat-only")
    SeatIdentity.objects.create(user=seat)
    client = Client()
    client.force_login(seat)
    session = client.session
    session["yaara_guest_origin"] = guest.user_id
    session.save()
    response = client.post(reverse("guest_restore"), {"user_id": seat.pk})
    assert response.status_code == 302 and response["Location"] == reverse(
        "game", args=[guest.game_id]
    )
    assert int(client.session["_auth_user_id"]) == guest.user_id


@case(
    "guest-restore-forged-origin",
    "Guest access: posted identifiers cannot recover another browser's solo",
)
def test_restore_forged_origin(guest, user):
    client = Client()
    client.force_login(user)
    response = client.post(reverse("guest_restore"), {"user_id": guest.user_id})
    assert response.status_code == 403
    assert int(client.session["_auth_user_id"]) == user.pk


@case("guest-existing-account-http", "Guest access: proven existing credentials preserve same game")
def test_attach_http(guest, user):
    client = Client()
    client.force_login(guest.user)
    response = client.post(
        reverse("guest_attach"),
        {
            "username": user.username,
            "password": "Test-only-password-832!",
        },
    )
    assert response.status_code == 302 and response["Location"] == reverse(
        "game", args=[guest.game_id]
    )
    assert int(client.session["_auth_user_id"]) == user.pk
    assert client.get(response["Location"]).status_code == 200


@case(
    "guest-creation-policy",
    "Guest access: forged custom-creation requests cannot create extra games",
)
def test_custom_creation_rejected(guest):
    with pytest.raises(PermissionDenied):
        services.create_game(guest.user, "Forbidden scheduled game", mode="scheduled")
    assert Game.objects.filter(owner=guest.user).count() == 1


@case(
    "guest-start-race",
    "Guest access: concurrent duplicate intent consumes one identity and one budget",
)
@pytest.mark.django_db(transaction=True)
def test_concurrent_start(settings):
    assert connection.vendor == "postgresql"
    settings.GUEST_STARTS_PER_HOUR = 1
    key = uuid.uuid4()
    barrier = Barrier(2)

    def start():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return guest_services.start_guest(key, "one-network").game_id
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as workers:
        first, second = list(workers.map(lambda _: start(), range(2)))
    assert first == second and GuestIdentity.objects.count() == 1
    assert set(GuestCreationBucket.objects.values_list("count", flat=True)) == {1}


@case(
    "guest-new-username-similarity",
    "Guest access: password validation uses the requested account name",
)
def test_username_password_similarity(guest):
    with pytest.raises(RuleError):
        guest_services.claim_guest_new(guest.user, "myuniquename", "myuniquename123")
    assert guest_services.is_guest(guest.user)


@case("guest-concurrent-claim", "Guest access: simultaneous account claims preserve one identity")
@pytest.mark.django_db(transaction=True)
def test_concurrent_claim(guest):
    assert connection.vendor == "postgresql"
    barrier = Barrier(2)

    def claim():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return guest_services.claim_guest_new(
                guest.user, "claimed-once", "Strong-test-pass-937!"
            ).pk
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: claim(), range(2)))
    assert results == [guest.user_id, guest.user_id]
    assert get_user_model().objects.filter(username="claimed-once").count() == 1
    assert Game.objects.filter(owner_id=guest.user_id).count() == 1


@case("guest-claim-versus-cleanup", "Guest access: cleanup rechecks claimed status after waiting")
@pytest.mark.django_db(transaction=True)
def test_claim_cleanup_race(guest, monkeypatch):
    assert connection.vendor == "postgresql"
    entered_validation = Event()
    cleanup_started = Event()
    real_validate = guest_services.validate_password

    def validation(password, user):
        entered_validation.set()
        assert cleanup_started.wait(timeout=10)
        return real_validate(password, user)

    monkeypatch.setattr(guest_services, "validate_password", validation)

    def claim():
        close_old_connections()
        try:
            return guest_services.claim_guest_new(
                guest.user, "saved-in-time", "Strong-test-pass-937!"
            ).pk
        finally:
            connections.close_all()

    def cleanup():
        close_old_connections()
        try:
            assert entered_validation.wait(timeout=10)
            cleanup_started.set()
            return guest_services.cleanup_expired_guests(guest.expires_at + timedelta(seconds=1))
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as workers:
        saved = workers.submit(claim)
        removed = workers.submit(cleanup)
        assert saved.result(timeout=20) == guest.user_id
        assert removed.result(timeout=20)["removed"] == 0
    assert Game.objects.filter(pk=guest.game_id).exists()
    assert not guest_services.is_guest(get_user_model().objects.get(pk=guest.user_id))


@case(
    "guest-transfer-versus-closure",
    "Guest access: transfer and closure cannot lose ownership or progress",
)
@pytest.mark.django_db(transaction=True)
def test_transfer_tick_race(guest, user):
    assert connection.vendor == "postgresql"
    barrier = Barrier(2)

    def transfer():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return guest_services.attach_guest_to_user(guest.user, user).pk
        finally:
            connections.close_all()

    def tick():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                services.tick(guest.game_id, 1, guest.user)
            except PermissionDenied:
                return False
            return True
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as workers:
        moved = workers.submit(transfer)
        advanced = workers.submit(tick)
        assert moved.result(timeout=20) == guest.game_id
        closed = advanced.result(timeout=20)
    guest.game.refresh_from_db()
    assert guest.game.owner_id == user.pk
    assert Participant.objects.get(game=guest.game).user_id == user.pk
    assert guest.game.state["month"] == (2 if closed else 1)
