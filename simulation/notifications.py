"""Opt-in recipient mail with a transactional outbox and standard Django transport."""

import uuid
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.db import transaction
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from . import multiplayer, services
from .messages import message
from .models import EmailSubscription, Game, NotificationDelivery
from .rules import RuleError

TOKEN_SALT = "yaara-email-consent"
PREFERENCES = ("start", "capture", "yearly", "raid")


def subscription_token(subscription):
    return signing.dumps({"id": subscription.pk, "v": str(subscription.token)}, salt=TOKEN_SALT)


def resolve_token(token, lock=False):
    try:
        data = signing.loads(token, salt=TOKEN_SALT)
        rows = EmailSubscription.objects.select_for_update() if lock else EmailSubscription.objects
        return rows.get(pk=data["id"], token=data["v"], email__gt="")
    except (
        signing.BadSignature,
        KeyError,
        ValueError,
        ValidationError,
        EmailSubscription.DoesNotExist,
    ) as error:
        raise PermissionDenied from error


@transaction.atomic
def configure(
    user, game_id, *, email, language="fr", start=True, capture=True, yearly=True, raid=False
):
    game = Game.objects.select_for_update().get(pk=game_id)
    actor = services.membership(game, user)
    email = email.strip()
    try:
        if email:
            validate_email(email)
            if len(email) > 254 or not email.isprintable():
                raise ValidationError("Invalid address")
    except ValidationError as error:
        raise RuleError(message("Indiquez une adresse e-mail valide.")) from error
    if email and not settings.EMAIL_NOTIFICATIONS_ENABLED:
        raise RuleError(message("Les notifications par e-mail ne sont pas encore activées."))
    member = game.memberships.get(actor=actor)
    sub, created = EmailSubscription.objects.select_for_update().get_or_create(
        participant=member, defaults={"requested_at": timezone.now()}
    )
    changed = created or sub.email != email
    if (
        changed
        and email
        and not created
        and sub.email
        and sub.verified_at is None
        and timezone.now() - sub.requested_at < timedelta(minutes=5)
    ):
        raise RuleError(
            message("Attendez cinq minutes avant de demander un nouvel e-mail de confirmation.")
        )
    if (
        email
        and sub.verified_at is None
        and timezone.now() - sub.requested_at >= timedelta(hours=1)
    ):
        changed = True
    if changed:
        sub.token = uuid.uuid4()
        sub.verified_at = None
        sub.requested_at = timezone.now()
        sub.deliveries.filter(status__in=["pending", "sending"]).update(status="cancelled")
    sub.email = email
    sub.language = language if language in ("fr", "en") else "fr"
    for key, value in {"start": start, "capture": capture, "yearly": yearly, "raid": raid}.items():
        setattr(sub, key, bool(value))
        if not value:
            sub.deliveries.filter(kind=key, status="pending").update(status="cancelled")
    sub.save()
    if email and changed:
        NotificationDelivery.objects.get_or_create(
            subscription=sub,
            event_key=f"verify:{sub.token}",
            defaults={"kind": "verify", "available_at": timezone.now()},
        )
    return sub


@transaction.atomic
def confirm_address(token):
    sub = resolve_token(token, lock=True)
    if timezone.now() - sub.requested_at > timedelta(days=2):
        raise PermissionDenied
    if sub.verified_at is None:
        sub.verified_at = timezone.now()
        sub.save(update_fields=["verified_at"])
    sub.deliveries.filter(kind="verify", status="pending").update(status="cancelled")
    return sub


@transaction.atomic
def unsubscribe(token):
    sub = resolve_token(token, lock=True)
    sub.email = ""
    sub.verified_at = None
    sub.token = uuid.uuid4()
    sub.save(update_fields=["email", "verified_at", "token"])
    sub.deliveries.filter(status__in=["pending", "sending"]).update(status="cancelled")


def category(report):
    if report.kind == "harvest":
        return "yearly"
    if report.kind == "sovereignty" or "-capture-" in report.content.get("scene", ""):
        return "capture"
    if "-raid-" in report.content.get("scene", ""):
        return "raid"
    if report.kind == "calendar" and report.title == "Le règne commence":
        return "start"
    return None


def queue_reports(game, reports):
    """Called only inside the caller's game transaction; no network side effects."""
    if not settings.EMAIL_NOTIFICATIONS_ENABLED:
        return
    subscriptions = {
        sub.participant.actor: sub
        for sub in EmailSubscription.objects.select_related("participant")
        .filter(participant__game=game, verified_at__isnull=False)
        .exclude(email="")
    }
    now = timezone.now()
    for report in reports:
        kind = category(report)
        sub = subscriptions.get(report.recipient)
        if sub is None or kind is None or not getattr(sub, kind):
            continue
        due = now
        if kind == "raid":
            pending = (
                sub.deliveries.filter(kind="raid", status="pending")
                .order_by("available_at")
                .first()
            )
            due = pending.available_at if pending else now + timedelta(hours=24)
            if sub.last_raid_sent_at:
                due = max(due, sub.last_raid_sent_at + timedelta(hours=24))
        NotificationDelivery.objects.get_or_create(
            subscription=sub,
            event_key=f"report:{report.pk}",
            defaults={"report": report, "kind": kind, "available_at": due},
        )


def absolute_url(path):
    return settings.PUBLIC_BASE_URL.rstrip("/") + path


def return_path(sub):
    member = sub.participant
    game = member.game
    if game.kind == "multiplayer":
        invite = game.invitations.get(actor=member.actor)
        if invite.revoked or game.lobby_status == "cancelled":
            return reverse("home")
        return reverse("shared_invite", args=[multiplayer.invitation_token(invite)])
    return reverse("game", args=[game.pk])


def mail_message(sub, deliveries):
    token = subscription_token(sub)
    stop_url = absolute_url(reverse("email_action", args=["unsubscribe", token]))
    with translation.override(sub.language):
        if deliveries[0].kind == "verify":
            subject = _("Confirmez les notifications de Yaara")
            body = _("Confirmez votre adresse sous 48 heures pour recevoir les nouvelles choisies.")
            body += "\n\n" + absolute_url(reverse("email_action", args=["confirm", token]))
        else:
            subject = _("Des nouvelles de votre maison dans Yaara")
            # Titles come exclusively from this recipient's stored letters. Bodies,
            # live state and rival numerical accounts never enter email.
            from .messages import render

            body = sub.participant.game.title + "\n\n"
            for delivery in deliveries[:50]:
                report = delivery.report
                title = (
                    render(report.content["title"], sub.language)
                    if "title" in report.content
                    else report.title
                )
                body += (
                    _("Lune %(moon)s : %(title)s") % {"moon": report.month, "title": title} + "\n"
                )
            body += "\n" + _("Retrouver votre maison") + ": " + absolute_url(return_path(sub))
        body += "\n\n" + _("Se désabonner") + ": " + stop_url
        return EmailMessage(
            "Yaara · " + subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [sub.email],
            headers={"List-Unsubscribe": f"<{stop_url}>"},
        )


@transaction.atomic
def claim_batch(sub_id, now):
    # A short lease prevents two workers sending the same batch. No game or
    # subscription lock is held while the transport opens a network connection.
    sub = EmailSubscription.objects.select_for_update(skip_locked=True).filter(pk=sub_id).first()
    if sub is None or sub.deliveries.filter(status="sending", available_at__gt=now).exists():
        return None
    deliveries = list(
        sub.deliveries.select_related("report")
        .filter(status__in=["pending", "sending"], available_at__lte=now)
        .order_by("pk")
    )
    eligible = []
    for item in deliveries:
        allowed = bool(sub.email) and (
            (
                item.kind == "verify"
                and sub.verified_at is None
                and now - sub.requested_at <= timedelta(days=2)
            )
            or (item.kind in PREFERENCES and sub.verified_at and getattr(sub, item.kind))
        )
        if item.report is not None:
            allowed = (
                allowed
                and item.report.game_id == sub.participant.game_id
                and item.report.recipient == sub.participant.actor
            )
        if not allowed:
            item.status = "cancelled"
            item.save(update_fields=["status"])
        elif (
            item.kind == "raid"
            and sub.last_raid_sent_at
            and now < sub.last_raid_sent_at + timedelta(hours=24)
        ):
            item.status = "pending"
            item.available_at = sub.last_raid_sent_at + timedelta(hours=24)
            item.save(update_fields=["status", "available_at"])
        else:
            item.status = "sending"
            item.attempts += 1
            item.available_at = now + timedelta(minutes=5)
            item.save(update_fields=["status", "attempts", "available_at"])
            eligible.append(item)
    if not eligible:
        return None
    return sub, eligible, mail_message(sub, eligible)


def process_due(now=None, limit=100):
    if not settings.EMAIL_NOTIFICATIONS_ENABLED:
        return 0
    now = now or timezone.now()
    candidate_ids = list(
        NotificationDelivery.objects.filter(
            status__in=["pending", "sending"], available_at__lte=now
        )
        .values_list("subscription_id", flat=True)
        .distinct()[:limit]
    )
    sent = 0
    for sub_id in candidate_ids:
        batch = claim_batch(sub_id, now)
        if batch is None:
            continue
        sub, deliveries, outgoing = batch
        try:
            if outgoing.send() != 1:
                raise OSError("Transport did not accept the message")
        except Exception:
            # Retain the queue without logging addresses, bodies or tokens.
            for item in deliveries:
                retry = now + timedelta(minutes=min(1440, 5 * 2 ** min(item.attempts - 1, 9)))
                NotificationDelivery.objects.filter(pk=item.pk, status="sending").update(
                    status="pending", available_at=retry
                )
        else:
            with transaction.atomic():
                current = EmailSubscription.objects.select_for_update().filter(pk=sub_id).first()
                if current is None:
                    continue
                current.deliveries.filter(
                    pk__in=[item.pk for item in deliveries], status="sending"
                ).update(status="sent")
                if current.token == sub.token and any(item.kind == "raid" for item in deliveries):
                    current.last_raid_sent_at = now
                    current.save(update_fields=["last_raid_sent_at"])
            sent += 1
    return sent
