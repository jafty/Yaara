"""Shared-room application services; seat links authenticate only low-privilege identities."""

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import F, Q

from . import services
from .messages import message
from .models import Game, Participant, SeatIdentity, SharedInvitation
from .rules import RuleError

ACTORS = ("p1", "p2", "p3")
INVITE_SALT = "yaara-shared-seat"
RECRUITMENT_SALT = "yaara-shared-recruitment"


def is_operator(user):
    return user.is_authenticated and user.has_perm("simulation.manage_multiplayer_games")


def require_operator(user):
    if not is_operator(user):
        raise PermissionDenied


def member_query(user):
    return Q(user=user) | Q(user__shared_identity__account=user)


def visible_revision(game, actor):
    if game.kind == "multiplayer":
        return game.memberships.get(actor=actor).view_revision
    return game.revision


def bump_visible(game, actor=None):
    if game.kind == "multiplayer":
        members = game.memberships.all()
        if actor is not None:
            members = members.filter(actor=actor)
        members.update(view_revision=F("view_revision") + 1)


def invitation_token(invitation):
    return signing.dumps({"id": str(invitation.pk), "v": invitation.version}, salt=INVITE_SALT)


def resolve_invitation(token):
    try:
        data = signing.loads(token, salt=INVITE_SALT)
        invitation = SharedInvitation.objects.select_related("game").get(
            pk=data["id"], version=data["v"], revoked=False
        )
    except (signing.BadSignature, KeyError, ValueError, SharedInvitation.DoesNotExist) as error:
        raise PermissionDenied from error
    if invitation.game.lobby_status == "cancelled":
        raise PermissionDenied
    return invitation


@transaction.atomic
def create_shared(
    operator, title, play_window="", reign_months=120, interval_minutes=10, auto_start=True
):
    require_operator(operator)
    game = services.create_game(
        operator,
        title,
        opponents="passive",
        mode="scheduled",
        reign_months=reign_months,
        interval_minutes=interval_minutes,
    )
    game.memberships.all().delete()
    game.reports.all().delete()
    game.kind = "multiplayer"
    game.lobby_status = "waiting"
    game.play_window = play_window
    game.auto_start = auto_start
    game.paused = True
    game.deadline = None
    game.save()
    for actor in ACTORS:
        SharedInvitation.objects.create(game=game, actor=actor)
    return game


def recruitment_token(game):
    return signing.dumps({"id": str(game.pk), "v": game.recruitment_version}, salt=RECRUITMENT_SALT)


def resolve_recruitment(token):
    try:
        data = signing.loads(token, salt=RECRUITMENT_SALT)
        return Game.objects.get(pk=data["id"], recruitment_version=data["v"], kind="multiplayer")
    except (signing.BadSignature, KeyError, ValueError, Game.DoesNotExist) as error:
        raise PermissionDenied from error


@transaction.atomic
def rotate_recruitment(operator, game_id):
    require_operator(operator)
    game = Game.objects.select_for_update().get(pk=game_id, kind="multiplayer")
    game.recruitment_version += 1
    game.save(update_fields=["recruitment_version"])


def validate_house_name(game, actor, name):
    name = name.strip()
    if not name or len(name) > 80 or not name.isprintable():
        raise RuleError(message("Choisissez un nom de maison de 1 à 80 caractères, sur une ligne."))
    if any(
        row["name"].strip().casefold() == name.casefold()
        for key, row in game.state["players"].items()
        if key != actor
    ):
        raise RuleError(message("Une autre maison porte déjà ce nom."))
    return name


@transaction.atomic
def choose_seat(token, actor, house_name, claim_key, user=None):
    preliminary = resolve_recruitment(token)
    game = Game.objects.select_for_update().get(pk=preliminary.pk)
    resolve_recruitment(token)  # Recheck rotation after obtaining the game lock.
    try:
        claim_key = uuid.UUID(str(claim_key))
    except (ValueError, TypeError) as error:
        raise PermissionDenied from error
    existing = game.memberships.filter(claim_key=claim_key).first()
    if existing is not None:
        invitation = game.invitations.get(actor=existing.actor)
        if (
            invitation.revoked
            or invitation.version != existing.claim_version
            or game.lobby_status == "cancelled"
        ):
            raise PermissionDenied
        return existing.user
    if (
        user is not None
        and user.is_authenticated
        and game.memberships.filter(member_query(user)).exists()
    ):
        raise RuleError(message("Vous disposez déjà d’une maison dans ce règne."))
    if game.lobby_status != "waiting":
        raise RuleError(message("Ce règne a déjà commencé ; aucune place ne peut être ajoutée."))
    invitation = game.invitations.filter(actor=actor, revoked=False).first()
    if invitation is None or game.memberships.filter(actor=actor).exists():
        raise RuleError(message("Cette place n’est plus disponible. Choisissez une autre maison."))
    name = validate_house_name(game, actor, house_name)
    from .guest_services import is_guest

    account = (
        user
        if user is not None
        and user.is_authenticated
        and not is_guest(user)
        and not hasattr(user, "shared_identity")
        else None
    )
    seat = get_user_model().objects.create_user("seat_" + uuid.uuid4().hex)
    SeatIdentity.objects.create(user=seat, account=account)
    Participant.objects.create(
        game=game, user=seat, actor=actor, claim_key=claim_key, claim_version=invitation.version
    )
    game.state["players"][actor]["name"] = name
    game.save(update_fields=["state"])
    if game.auto_start and can_start(game):
        start_locked(game)
    return seat


@transaction.atomic
def rename_house(user, game_id, house_name):
    game = Game.objects.select_for_update().get(pk=game_id, kind="multiplayer")
    actor = services.membership(game, user)
    if game.lobby_status != "waiting":
        raise RuleError(message("Le nom de la maison est fixé au départ du règne."))
    game.state["players"][actor]["name"] = validate_house_name(game, actor, house_name)
    game.save(update_fields=["state"])


@transaction.atomic
def issue_invitation(operator, game_id, actor):
    require_operator(operator)
    game = Game.objects.select_for_update().get(pk=game_id, kind="multiplayer")
    if actor not in ACTORS or game.lobby_status == "cancelled":
        raise RuleError(message("Cette invitation ne peut pas être créée."))
    invitation, created = SharedInvitation.objects.get_or_create(game=game, actor=actor)
    if not created:
        invitation.version += 1
    invitation.revoked = False
    invitation.save()
    if game.auto_start and can_start(game):
        start_locked(game)
    return invitation


@transaction.atomic
def revoke_invitation(operator, game_id, actor):
    require_operator(operator)
    Game.objects.select_for_update().get(pk=game_id, kind="multiplayer")
    invitation = SharedInvitation.objects.get(game_id=game_id, actor=actor)
    invitation.revoked = True
    invitation.version += 1
    invitation.save()


@transaction.atomic
def claim_invitation(token, account=None):
    preliminary = resolve_invitation(token)
    game = Game.objects.select_for_update().get(pk=preliminary.game_id)
    invitation = resolve_invitation(token)
    participant = game.memberships.filter(actor=invitation.actor).first()
    if (
        account is not None
        and game.memberships.filter(member_query(account)).exclude(actor=invitation.actor).exists()
    ):
        raise RuleError(message("Vous disposez déjà d’une maison dans ce règne."))
    if participant is not None:
        if account is not None:
            identity = participant.user.shared_identity
            if identity.account_id is None:
                identity.account = account
                identity.save(update_fields=["account"])
        return participant.user
    if game.lobby_status != "waiting":
        raise RuleError(message("Ce règne a déjà commencé ; aucune place ne peut être ajoutée."))
    if account is not None and game.memberships.filter(member_query(account)).exists():
        raise RuleError(message("Vous disposez déjà d’une maison dans ce règne."))
    seat = get_user_model().objects.create_user("seat_" + uuid.uuid4().hex)
    SeatIdentity.objects.create(user=seat, account=account)
    Participant.objects.create(game=game, user=seat, actor=invitation.actor)
    if game.auto_start and can_start(game):
        start_locked(game)
    return seat


def check_seat_session(request, game):
    if game.kind != "multiplayer" or not hasattr(request.user, "shared_identity"):
        return
    participant = game.memberships.filter(user=request.user).first()
    if participant is None:
        raise PermissionDenied
    invitation = game.invitations.get(actor=participant.actor)
    grants = request.session.get("shared_seat_access", {})
    if invitation.revoked or grants.get(str(game.pk)) != invitation.version:
        raise PermissionDenied


def calendar_events(game, title, body):
    return [
        {"recipient": member.actor, "kind": "calendar", "title": title, "body": body}
        for member in game.memberships.all()
    ]


def can_start(game):
    return (
        game.lobby_status == "waiting"
        and set(game.memberships.values_list("actor", flat=True)) == set(ACTORS)
        and game.invitations.filter(revoked=False).count() == 3
    )


@transaction.atomic
def start_shared(operator, game_id):
    require_operator(operator)
    game = Game.objects.select_for_update().get(pk=game_id, kind="multiplayer")
    if game.lobby_status == "running":
        return
    if not can_start(game):
        raise RuleError(message("Les trois maisons doivent rejoindre le règne avant son départ."))
    start_locked(game)


def start_locked(game):
    """Start once under the admission/operator caller's game lock and transaction."""
    game.lobby_status = "running"
    game.paused = False
    game.state["awaiting_start"] = False
    game.state["clock_aligned"] = False
    game.remaining_seconds = game.interval_minutes * 60
    game.deadline = services.timezone.now() + timedelta(minutes=game.interval_minutes)
    services.persist(
        game,
        calendar_events(
            game,
            message("Le règne commence"),
            message(
                "Les trois maisons sont réunies. La première lune dispose d’un intervalle complet ; le calendrier affiché fixe les prochaines clôtures."
            ),
        ),
    )
    bump_visible(game)


@transaction.atomic
def cancel_shared(operator, game_id):
    require_operator(operator)
    game = Game.objects.select_for_update().get(pk=game_id, kind="multiplayer")
    if game.lobby_status == "cancelled":
        return
    game.lobby_status = "cancelled"
    game.paused = True
    game.deadline = None
    services.persist(
        game,
        calendar_events(
            game,
            message("Le règne est arrêté"),
            message(
                "L’organisateur a arrêté ce règne. Les lettres conservées restent dans les archives de chaque maison."
            ),
        ),
    )
    bump_visible(game)
