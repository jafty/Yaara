"""Guest lifecycle services; ordinary gameplay still uses Participant authorization."""

import logging
import uuid
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.translation import gettext as _

from . import services
from .guest_models import GuestCreationBucket, GuestIdentity
from .models import Game, Participant
from .rules import RuleError

logger = logging.getLogger(__name__)


def _event(name, identity):
    identity_id, game_id = identity.pk, identity.game_id
    transaction.on_commit(lambda: logger.info("%s identity=%s game=%s", name, identity_id, game_id))


def guest_identity(user):
    if not user or not user.is_authenticated:
        return None
    return GuestIdentity.objects.filter(user_id=user.pk, claimed_at__isnull=True).first()


def is_guest(user):
    return guest_identity(user) is not None


def require_registered(user):
    if not user or not user.is_authenticated or is_guest(user) or _is_seat_identity(user):
        raise PermissionDenied(_("Conservez votre règne dans un compte pour continuer."))


def _retention():
    return timedelta(days=settings.GUEST_RETENTION_DAYS)


def _private_solo(identity):
    game = identity.game
    return (
        getattr(game, "kind", "solo") == "solo"
        and game.mode == "manual"
        and game.owner_id == identity.user_id
        and game.memberships.count() == 1
        and game.memberships.filter(user_id=identity.user_id, actor="p1").exists()
        and not Game.objects.filter(owner_id=identity.user_id).exclude(pk=game.pk).exists()
        and not Participant.objects.filter(user_id=identity.user_id).exclude(game=game).exists()
    )


def _creation_budget(network_key, now, start_key):
    window = now.replace(minute=0, second=0, microsecond=0)
    limits = {
        "all": settings.GUEST_GLOBAL_STARTS_PER_HOUR,
        "network:" + str(network_key): settings.GUEST_STARTS_PER_HOUR,
    }
    buckets = []
    for scope in sorted(limits):
        key = salted_hmac("yaara-guest-budget", scope + window.isoformat()).hexdigest()
        GuestCreationBucket.objects.get_or_create(key=key, defaults={"window": window})
        bucket = GuestCreationBucket.objects.select_for_update().get(pk=key)
        buckets.append((bucket, limits[scope]))
    existing = (
        GuestIdentity.objects.select_related("user", "game").filter(start_key=start_key).first()
    )
    if existing:
        if existing.claimed_at or existing.expires_at <= now or not existing.user.is_active:
            raise PermissionDenied(_("Votre accès invité a expiré."))
        return existing
    for bucket, limit in buckets:
        if bucket.count >= limit:
            raise RuleError(_("Trop de nouveaux règnes invités. Réessayez dans une heure."))
        bucket.count += 1
        bucket.save(update_fields=["count"])
    return None


@transaction.atomic
def start_guest(start_key, network_key):
    """A repeated session-bound intent resumes the same identity, including during a pause."""
    start_key = uuid.UUID(str(start_key))
    existing = (
        GuestIdentity.objects.select_related("user", "game").filter(start_key=start_key).first()
    )
    if existing:
        if (
            existing.claimed_at
            or existing.expires_at <= timezone.now()
            or not existing.user.is_active
        ):
            raise PermissionDenied(_("Votre accès invité a expiré."))
        return existing
    if not settings.GUEST_PLAY_ENABLED:
        raise PermissionDenied(_("Les nouveaux règnes invités sont momentanément fermés."))
    now = timezone.now()
    existing = _creation_budget(network_key, now, start_key)
    if existing:
        return existing
    user = get_user_model().objects.create_user(username="guest_" + uuid.uuid4().hex)
    game = services.create_game(user, _("Les chroniques de Yaara"))
    identity = GuestIdentity.objects.create(
        user=user,
        game=game,
        start_key=start_key,
        created_at=now,
        last_seen_at=now,
        expires_at=now + _retention(),
    )
    _event("guest_started", identity)
    return identity


@transaction.atomic
def touch_guest(user):
    if not user or not user.is_authenticated:
        return None
    identity = (
        GuestIdentity.objects.select_for_update()
        .filter(user_id=user.pk, claimed_at__isnull=True)
        .first()
    )
    if identity is None:
        return None
    now = timezone.now()
    if identity.expires_at <= now:
        raise PermissionDenied(_("Votre accès invité a expiré."))
    # Bounded writes still keep session/cookie expiry in step with the documented idle policy.
    if now - identity.last_seen_at >= timedelta(hours=1):
        identity.last_seen_at = now
        identity.expires_at = now + _retention()
        identity.save(update_fields=["last_seen_at", "expires_at"])
        identity.renew_session = True
    return identity


def _locked_guest(user):
    identity = GuestIdentity.objects.select_for_update().filter(user_id=user.pk).first()
    if identity is None:
        raise PermissionDenied(_("Ce règne ne dépend pas de votre accès invité."))
    return identity


@transaction.atomic
def claim_guest_new(user, username, password):
    identity = _locked_guest(user)
    current = get_user_model().objects.select_for_update().get(pk=user.pk)
    game = Game.objects.select_for_update().get(pk=identity.game_id)
    identity.game = game
    if identity.claimed_at:
        if current.is_active and current.username == username:
            return current
        raise PermissionDenied(_("Cet accès invité a déjà été conservé."))
    if not settings.SIGNUP_ENABLED:
        raise PermissionDenied(_("La création de comptes est actuellement fermée."))
    if identity.expires_at <= timezone.now() or not _private_solo(identity):
        raise PermissionDenied(_("Ce règne ne peut pas être rattaché à cet accès invité."))
    username = username.strip()
    current.username = username
    try:
        current._meta.get_field("username").clean(username, current)
        if (
            get_user_model()
            .objects.filter(username__iexact=username)
            .exclude(pk=current.pk)
            .exists()
        ):
            raise ValidationError(_("Ce nom de compte est déjà utilisé."))
        validate_password(password, current)
    except ValidationError as error:
        raise RuleError(" ".join(error.messages)) from error
    current.set_password(password)
    try:
        with transaction.atomic():
            current.save(update_fields=["username", "password"])
    except IntegrityError as error:
        raise RuleError(_("Ce nom de compte est déjà utilisé.")) from error
    identity.claimed_at = timezone.now()
    identity.save(update_fields=["claimed_at"])
    _event("guest_claimed", identity)
    return current


@transaction.atomic
def attach_guest_to_user(guest_user, target_user):
    """Caller must authenticate the ordinary destination account before invoking."""
    identity = _locked_guest(guest_user)
    users = {
        row.pk: row
        for row in get_user_model()
        .objects.select_for_update()
        .filter(pk__in=[guest_user.pk, target_user.pk])
        .order_by("pk")
    }
    destination = users.get(target_user.pk)
    game = Game.objects.select_for_update().get(pk=identity.game_id)
    identity.game = game
    if identity.claimed_at:
        if game.owner_id == target_user.pk:
            return game
        raise PermissionDenied(_("Cet accès invité a déjà été conservé."))
    if (
        destination is None
        or not destination.is_active
        or destination.pk == guest_user.pk
        or is_guest(destination)
        or _is_seat_identity(destination)
        or identity.expires_at <= timezone.now()
        or not _private_solo(identity)
    ):
        raise PermissionDenied(_("Ce règne ne peut pas être rattaché à ce compte."))
    if Game.objects.filter(owner=destination).count() >= 30:
        raise RuleError(_("Ce compte possède déjà trente règnes. Votre règne invité est conservé."))
    participant = Participant.objects.get(game=game, user_id=guest_user.pk)
    participant.user = destination
    participant.save(update_fields=["user"])
    game.owner = destination
    game.save(update_fields=["owner"])
    identity.claimed_at = timezone.now()
    identity.save(update_fields=["claimed_at"])
    previous = users[guest_user.pk]
    previous.is_active = False
    previous.save(update_fields=["is_active"])
    _event("guest_attached", identity)
    return game


def _is_seat_identity(user):
    try:
        model = apps.get_model("simulation", "SeatIdentity")
    except LookupError:
        return False
    return model.objects.filter(user_id=user.pk).exists()


def cleanup_expired_guests(now=None):
    now = now or timezone.now()
    result = {"removed": 0, "skipped": 0}
    ids = list(
        GuestIdentity.objects.filter(claimed_at__isnull=True, expires_at__lte=now).values_list(
            "pk", flat=True
        )
    )
    for identity_id in ids:
        with transaction.atomic():
            identity = GuestIdentity.objects.select_for_update().filter(pk=identity_id).first()
            if identity is None or identity.claimed_at or identity.expires_at > now:
                continue
            user = get_user_model().objects.select_for_update().get(pk=identity.user_id)
            identity.game = Game.objects.select_for_update().get(pk=identity.game_id)
            if not _private_solo(identity) or _is_seat_identity(user):
                result["skipped"] += 1
                logger.warning("guest_cleanup_skipped identity=%s", identity.pk)
                continue
            user.delete()
            result["removed"] += 1
    GuestCreationBucket.objects.filter(window__lt=now - timedelta(days=2)).delete()
    return result
