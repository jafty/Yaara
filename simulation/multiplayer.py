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
def create_shared(operator, title, play_window="", reign_months=120, interval_minutes=10):
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
    game.paused = True
    game.deadline = None
    game.save()
    for actor in ACTORS:
        SharedInvitation.objects.create(game=game, actor=actor)
    return game


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
