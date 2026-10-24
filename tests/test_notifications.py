"""Confirmed, optional recipient notifications run separately from game transactions."""

from datetime import timedelta
from io import StringIO

import pytest
from django.core import mail
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.db import transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from simulation import notifications, services
from simulation.models import EmailSubscription, NotificationDelivery, Report
from simulation.rules import RuleError
from tests.cases import case
from tests.test_application import concurrent_calls

pytestmark = [
    pytest.mark.integration,
    pytest.mark.django_db,
    pytest.mark.usefixtures("test_static_storage"),
]


@pytest.fixture(autouse=True)
def mail_settings(settings):
    settings.EMAIL_NOTIFICATIONS_ENABLED = True
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    settings.PUBLIC_BASE_URL = "https://yaara.example"


def subscribe(user, game, **overrides):
    values = dict(
        email="player@example.com", language="en", start=True, capture=True, yearly=True, raid=False
    )
    values.update(overrides)
    return notifications.configure(user, game.pk, **values)


@pytest.fixture
def subscription(user, game):
    sub = subscribe(user, game)
    notifications.confirm_address(notifications.subscription_token(sub))
    NotificationDelivery.objects.all().delete()
    sub.refresh_from_db()
    return sub


def event(game, kind="harvest", recipient="p1", scene=None):
    row = {
        "recipient": recipient,
        "kind": kind,
        "title": "A personal letter",
        "body": "Private own facts",
    }
    if scene:
        row["content"] = {"scene": scene}
    with transaction.atomic():
        services.persist(game, [row])
    return Report.objects.filter(game=game).latest("pk")


@case(
    "email-confirm-required",
    "Notifications: consent queues verification without enabling event mail",
)
def test_confirmation(user, game):
    sub = subscribe(user, game)
    assert sub.verified_at is None and not sub.raid
    assert NotificationDelivery.objects.get().kind == "verify"
    event(game)
    assert NotificationDelivery.objects.count() == 1
    notifications.confirm_address(notifications.subscription_token(sub))
    sub.refresh_from_db()
    assert sub.verified_at is not None


@case("email-invalid-address", "Notifications: invalid addresses cannot subscribe")
@pytest.mark.parametrize(
    "address",
    ["bad", "a@example.com\nBcc:attacker@example.com"],
    ids=["missing-domain", "header-injection"],
)
def test_invalid_address(user, game, address):
    with pytest.raises(RuleError):
        subscribe(user, game, email=address)
    assert not EmailSubscription.objects.exists() and not NotificationDelivery.objects.exists()


@case("email-membership", "Notifications: only an actual participant may configure a recipient")
def test_member(user, game, django_user_model):
    outsider = django_user_model.objects.create_user("outsider")
    with pytest.raises(PermissionDenied):
        subscribe(outsider, game)
    assert not EmailSubscription.objects.exists()


@case("email-confirm-readonly-get", "Notifications: scanners cannot confirm or unsubscribe by GET")
@pytest.mark.parametrize("action", ["confirm", "unsubscribe"])
def test_safe_get(subscription, action):
    token = notifications.subscription_token(subscription)
    response = Client().get(reverse("email_action", args=[action, token]))
    assert response.status_code == 200
    subscription.refresh_from_db()
    assert subscription.email == "player@example.com" and subscription.verified_at


@case("email-expired-confirmation", "Notifications: old confirmation links expire without consent")
def test_expired(user, game):
    sub = subscribe(user, game)
    EmailSubscription.objects.filter(pk=sub.pk).update(
        requested_at=timezone.now() - timedelta(days=3)
    )
    with pytest.raises(PermissionDenied):
        notifications.confirm_address(notifications.subscription_token(sub))
    sub.refresh_from_db()
    assert sub.verified_at is None


@case(
    "email-address-change",
    "Notifications: changing address invalidates old consent and queued letters",
)
def test_address_change(user, game, subscription):
    old = notifications.subscription_token(subscription)
    event(game)
    updated = subscribe(user, game, email="new@example.com")
    assert updated.verified_at is None
    assert not NotificationDelivery.objects.filter(kind="yearly", status="pending").exists()
    with pytest.raises(PermissionDenied):
        notifications.confirm_address(old)


@case("email-repeat-optin", "Notifications: repeated preference save cannot spam verification")
def test_repeat(user, game):
    first = subscribe(user, game)
    assert subscribe(user, game).pk == first.pk
    assert NotificationDelivery.objects.count() == 1


@case("email-unsubscribe", "Notifications: unsubscribe stops queued delivery and invalidates token")
def test_unsubscribe(subscription, game):
    token = notifications.subscription_token(subscription)
    event(game)
    notifications.unsubscribe(token)
    notifications.process_due()
    subscription.refresh_from_db()
    assert subscription.email == "" and subscription.verified_at is None
    assert not mail.outbox


@case("email-category", "Notifications: opted-in reports queue only their explicit category")
@pytest.mark.parametrize(
    "kind,scene,category",
    [
        ("harvest", None, "yearly"),
        ("battle", "received-capture-success", "capture"),
        ("battle", "offensive-capture-failure", "capture"),
        ("sovereignty", None, "capture"),
        ("order", None, None),
        ("battle", "received-raid-success", None),
        ("calendar", None, None),
    ],
)
def test_category(game, subscription, kind, scene, category):
    report = event(game, kind, scene=scene)
    rows = NotificationDelivery.objects.filter(report=report)
    assert list(rows.values_list("kind", flat=True)) == ([category] if category else [])


@case("email-start-event", "Notifications: the start letter triggers the game-start preference")
def test_start_event(game, subscription):
    with transaction.atomic():
        services.persist(
            game,
            [
                {
                    "recipient": "p1",
                    "kind": "calendar",
                    "title": "Le règne commence",
                    "body": "The first Moon opens",
                }
            ],
        )
    assert NotificationDelivery.objects.get().kind == "start"


@case("email-pref-disabled", "Notifications: a disabled preference creates no delivery")
def test_disabled_preference(user, game, subscription):
    subscribe(user, game, yearly=False)
    event(game)
    assert not NotificationDelivery.objects.exists()


@case("email-recipient-isolation", "Notifications: a rival letter cannot reach this subscriber")
def test_recipient(game, subscription):
    event(game, recipient="p2")
    assert not NotificationDelivery.objects.exists()


@case("email-report-replay", "Notifications: queueing the same report twice is idempotent")
def test_replay(game, subscription):
    report = event(game)
    notifications.queue_reports(game, [report])
    assert NotificationDelivery.objects.count() == 1


@case("email-report-rollback", "Notifications: failed game transactions roll back queued email")
def test_rollback(game, subscription):
    before = game.reports.count()
    with pytest.raises(RuntimeError), transaction.atomic():
        event(game)
        raise RuntimeError("Abort the game transaction")
    assert not NotificationDelivery.objects.exists() and game.reports.count() == before


@case("email-raid-digest", "Notifications: raids wait and combine into one digest per 24 hours")
def test_raid_digest(user, game, subscription):
    subscribe(user, game, raid=True)
    event(game, "battle", scene="received-raid-success")
    event(game, "battle", scene="offensive-raid-failure")
    due = NotificationDelivery.objects.earliest("available_at").available_at
    assert due >= timezone.now() + timedelta(hours=23)
    notifications.process_due(now=due - timedelta(seconds=1))
    assert not mail.outbox
    notifications.process_due(now=due)
    assert len(mail.outbox) == 1
    assert NotificationDelivery.objects.filter(status="sent").count() == 2
    event(game, "battle", scene="received-raid-failure")
    assert NotificationDelivery.objects.filter(
        status="pending"
    ).get().available_at >= due + timedelta(hours=24)


@case(
    "email-worker-disabled",
    "Notifications: disabled mail transport never sends or consumes the queue",
)
def test_worker_disabled(game, subscription, settings):
    event(game)
    settings.EMAIL_NOTIFICATIONS_ENABLED = False
    notifications.process_due()
    assert not mail.outbox and NotificationDelivery.objects.get().status == "pending"


@case(
    "email-transient-failure", "Notifications: SMTP failure retries later without losing the letter"
)
def test_retry(game, subscription, monkeypatch):
    event(game)

    def failed(*args, **kwargs):
        raise OSError("Mail server unavailable")

    monkeypatch.setattr(notifications.EmailMessage, "send", failed)
    notifications.process_due()
    delivery = NotificationDelivery.objects.get()
    assert delivery.status == "pending" and delivery.attempts == 1
    assert delivery.available_at > timezone.now()


@case(
    "email-send-localized",
    "Notifications: worker sends localized recipient mail and unsubscribe link",
)
@pytest.mark.parametrize("language", ["fr", "en"])
def test_send(game, subscription, language):
    subscription.language = language
    subscription.save()
    event(game)
    call_command("send_notifications", stdout=StringIO())
    call_command("send_notifications", stdout=StringIO())
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["player@example.com"]
    assert ("Unsubscribe" if language == "en" else "Se désabonner") in mail.outbox[0].body
    assert "https://yaara.example" in mail.outbox[0].body
    assert "Private own facts" not in mail.outbox[0].body


@case("email-worker-concurrency", "Notifications: concurrent workers send a pending batch once")
@pytest.mark.django_db(transaction=True)
def test_worker_concurrency(game, subscription):
    event(game)
    concurrent_calls([notifications.process_due, notifications.process_due])
    assert len(mail.outbox) == 1
    assert NotificationDelivery.objects.get().status == "sent"


@case(
    "email-native-settings",
    "Notifications: participant preferences remain native and CSRF protected",
)
def test_form(user, game):
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    url = reverse("email_settings", args=[game.pk])
    assert client.get(url).status_code == 200
    assert client.post(url, {"email": "player@example.com"}).status_code == 403
    response = client.post(
        url,
        {
            "email": "player@example.com",
            "yearly": "on",
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        },
    )
    assert response.status_code == 302
    assert EmailSubscription.objects.get().verified_at is None


@case(
    "email-send-outside-transaction",
    "Notifications: transport holds no database transaction or game lock",
)
@pytest.mark.django_db(transaction=True)
def test_transport_boundary(game, subscription, monkeypatch):
    from django.db import connection

    event(game)

    def accepted(*args, **kwargs):
        assert not connection.in_atomic_block
        return 1

    monkeypatch.setattr(notifications.EmailMessage, "send", accepted)
    notifications.process_due()
    assert NotificationDelivery.objects.get().status == "sent"


@case("email-guest-consent", "Notifications: guest solo players can opt in without registration")
def test_guest_consent():
    client = Client()
    client.get(reverse("home"))
    solo = client.post(reverse("guest_start"), {"start_key": client.session["guest_start_key"]}).url
    response = client.post(solo + "email/", {"email": "guest@example.com", "yearly": "on"})
    assert response.status_code == 302
    sub = EmailSubscription.objects.get()
    assert not sub.participant.user.has_usable_password()
    notifications.process_due()
    assert len(mail.outbox) == 1 and "/email/confirm/" in mail.outbox[0].body


@case("email-worker-lease-recovery", "Notifications: an expired worker lease is retried")
def test_lease_recovery(game, subscription):
    event(game)
    NotificationDelivery.objects.update(
        status="sending", available_at=timezone.now() - timedelta(seconds=1)
    )
    notifications.process_due()
    assert len(mail.outbox) == 1 and NotificationDelivery.objects.get().status == "sent"


@case(
    "email-clear-unconfirmed",
    "Notifications: clearing an unconfirmed address always permits opting out",
)
def test_clear_unconfirmed(user, game):
    sub = subscribe(user, game)
    subscribe(user, game, email="")
    sub.refresh_from_db()
    assert not sub.email and not sub.deliveries.filter(status="pending").exists()


@case(
    "email-automatic-room-start",
    "Notifications: final guest admission queues the waiting house's start letter",
)
def test_automatic_start_mail(user, django_user_model):
    import uuid

    from django.contrib.auth.models import Permission

    from simulation import multiplayer

    user.user_permissions.add(Permission.objects.get(codename="manage_multiplayer_games"))
    operator = django_user_model.objects.get(pk=user.pk)
    room = multiplayer.create_shared(operator, "Shared mail")
    token = multiplayer.recruitment_token(room)
    first = multiplayer.choose_seat(token, "p1", "Cedar", uuid.uuid4())
    sub = subscribe(first, room)
    notifications.confirm_address(notifications.subscription_token(sub))
    multiplayer.choose_seat(token, "p2", "Oak", uuid.uuid4())
    multiplayer.choose_seat(token, "p3", "Palm", uuid.uuid4())
    queued = NotificationDelivery.objects.get(kind="start")
    assert queued.subscription_id == sub.pk and queued.report.recipient == "p1"
    notifications.process_due()
    assert len(mail.outbox) == 1 and "/join/" in mail.outbox[0].body
    assert token not in mail.outbox[0].body
