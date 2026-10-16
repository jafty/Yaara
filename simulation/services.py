"""Authorized commands and transaction boundaries; one lock for every game mutation."""

import secrets
import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from . import engine
from .models import CommandReceipt, Game, Participant, Report, TargetEngagement, TickExecution
from .narration import number
from .rules import ACTION_LABELS, RuleError


def membership(game, user):
    participant = Participant.objects.filter(game=game, user=user).first()
    if participant is None:
        raise PermissionDenied("Vous ne participez pas à cette partie.")
    return participant.actor


def check_window(game, expected_month=None):
    if game.paused:
        raise RuleError("La partie est en pause. Reprenez le calendrier pour donner un ordre.")
    if game.state["status"] != "active":
        raise RuleError("Ce règne est terminé.")
    if game.deadline and timezone.now() >= game.deadline:
        raise RuleError("Le mois est clos. Vérifiez le départ et le devis du mois suivant.")
    if expected_month is not None and expected_month != game.state["month"]:
        raise RuleError("Le calendrier a changé. Préparez à nouveau votre décret.")


def sync_engagements(game):
    targets = engine.active_targets(game.state)
    TargetEngagement.objects.filter(game=game).exclude(city_id__in=targets).delete()
    for city_id, order_id in targets.items():
        TargetEngagement.objects.update_or_create(
            game=game, city_id=city_id, defaults={"order_id": order_id}
        )


def persist(game, events=()):
    engine.assert_invariants(game.state)
    game.revision += 1
    game.save()
    sync_engagements(game)
    Report.objects.bulk_create(
        [Report(game=game, month=game.state["month"], **event) for event in events]
    )


@transaction.atomic
def create_game(
    user,
    title,
    version="V1",
    reign_months=120,
    opponents="active",
    mode="manual",
    interval_minutes=10,
    player_name="La maison d’Ambre",
):
    # Serialize account-level creation limits as well as each game's commands.
    get_user_model().objects.select_for_update().get(pk=user.pk)
    if Game.objects.filter(owner=user).count() >= 30:
        raise RuleError(
            "Vous avez déjà trente parties. Conservez vos règnes existants pour le moment."
        )
    if mode not in ("manual", "scheduled") or interval_minutes not in (5, 10):
        raise RuleError("Ce calendrier n’est pas disponible.")
    state = engine.new_state(version, reign_months, opponents, player_name)
    game = Game.objects.create(
        owner=user,
        title=title,
        state=state,
        seed=secrets.token_hex(32),
        mode=mode,
        interval_minutes=interval_minutes,
        remaining_seconds=interval_minutes * 60,
        deadline=timezone.now() + timedelta(minutes=interval_minutes)
        if mode == "scheduled"
        else None,
    )
    Participant.objects.create(game=game, user=user, actor="p1")
    Report.objects.create(
        game=game,
        recipient="p1",
        month=0,
        kind="welcome",
        title="Le sceau vous appartient",
        body="J’ai fait ouvrir les registres de vos trois cités. Leurs habitants reconnaissent votre autorité, mais il nous appartient encore de préparer les années qui viennent. Chaque cité gardera ses réserves ; pour vos dépenses, je demanderai à tous les greniers de contribuer selon leurs moyens. La première récolte nous sera versée au mois 12. D’ici là, je tiendrai compte des hommes partis et des ouvrages que vous aurez ordonnés.",
    )
    return game


@transaction.atomic
def confirm(user, game_id, spec, request_id, expected_month, expected_revision=None):
    game = Game.objects.select_for_update().get(pk=game_id)
    actor = membership(game, user)
    receipt = CommandReceipt.objects.filter(game=game, actor=actor, request_id=request_id).first()
    if receipt:
        return next(order for order in game.state["orders"] if order["id"] == receipt.order_id)
    check_window(game, expected_month)
    if expected_revision is not None and game.revision != expected_revision:
        raise RuleError("La situation a changé depuis ce devis. Vérifiez à nouveau vos moyens.")
    order = engine.confirm_order(game.state, actor, spec, str(request_id))
    CommandReceipt.objects.create(
        game=game, actor=actor, request_id=request_id, order_id=order["id"]
    )
    persist(
        game,
        [
            {
                "recipient": actor,
                "kind": "order",
                "title": "Décret scellé",
                "body": f"J’ai placé sous votre sceau cet ordre : {ACTION_LABELS[order['kind']].lower()}. Les greniers promettent {number(order['cost'])} Mesures, qui ne seront dépensées qu’au départ, au mois {order['execute_month']}. Les hommes et les emplacements nécessaires vous sont désormais réservés.",
            }
        ],
    )
    return order


@transaction.atomic
def cancel(user, game_id, order_id):
    game = Game.objects.select_for_update().get(pk=game_id)
    actor = membership(game, user)
    check_window(game)
    order = engine.cancel_order(game.state, actor, order_id)
    persist(
        game,
        [
            {
                "recipient": actor,
                "kind": "order",
                "title": "Décret retiré",
                "body": f"Selon votre volonté, j’ai retiré ce décret : {ACTION_LABELS[order['kind']].lower()}. Les moyens qu’il engageait sont de nouveau libres."
                + (
                    " Une autre expédition pourra désormais engager la cible."
                    if order["kind"] in ("raid", "capture")
                    else ""
                ),
            }
        ],
    )


@transaction.atomic
def tick(game_id, expected_month, user=None):
    game = Game.objects.select_for_update().get(pk=game_id)
    if user is not None:
        membership(game, user)
        if game.owner_id != user.pk or game.mode != "manual":
            raise PermissionDenied(
                "Le calendrier de cette partie ne peut pas être avancé manuellement."
            )
    # The explicit target month makes HTTP and scheduler retries safe.
    existing = TickExecution.objects.filter(game=game, month=expected_month).first()
    if existing:
        return existing, False
    if game.paused or game.state["status"] != "active":
        raise RuleError("Le calendrier de cette partie est arrêté.")
    if expected_month != game.state["month"] + 1:
        raise RuleError("Ce mois ne peut pas être résolu. Actualisez la page.")
    now = timezone.now()
    if game.mode == "scheduled":
        if not game.deadline or now < game.deadline:
            raise RuleError("La prochaine clôture n’est pas encore atteinte.")
        if now - game.deadline > timedelta(minutes=game.interval_minutes):
            game.paused = True
            game.remaining_seconds = game.interval_minutes * 60
            game.deadline = None
            persist(
                game,
                [
                    {
                        "recipient": member.actor,
                        "kind": "calendar",
                        "title": "Le calendrier est suspendu",
                        "body": "Le traitement a pris du retard. Reprenez la partie pour ouvrir une nouvelle fenêtre de décision complète.",
                    }
                    for member in game.memberships.all()
                ],
            )
            return None, False
    bot_commands = engine.bot_orders(game.state, game.seed)
    events, audit = engine.advance_month(game.state, game.seed)
    audit["bot_orders"] = [order["id"] for order in bot_commands]
    audit["accepted_orders"] = [
        order["id"] for order in game.state["orders"] if order["execute_month"] == expected_month
    ]
    execution = TickExecution.objects.create(
        game=game, month=expected_month, rules=game.state["rules"], trace=audit
    )
    if game.mode == "scheduled":
        game.deadline += timedelta(minutes=game.interval_minutes)
    if game.state["status"] == "finished":
        game.deadline = None
    persist(game, events)
    return execution, True


@transaction.atomic
def toggle_pause(user, game_id):
    game = Game.objects.select_for_update().get(pk=game_id)
    membership(game, user)
    if game.owner_id != user.pk or game.mode != "scheduled" or game.state["status"] != "active":
        raise PermissionDenied("Cette partie ne peut pas être suspendue.")
    if game.paused:
        game.deadline = timezone.now() + timedelta(seconds=max(1, game.remaining_seconds))
        game.paused = False
    else:
        if game.deadline <= timezone.now():
            raise RuleError(
                "La clôture est déjà atteinte ; attendez son traitement avant de suspendre la partie."
            )
        game.remaining_seconds = max(1, int((game.deadline - timezone.now()).total_seconds()))
        game.deadline = None
        game.paused = True
    persist(game)


def quote(user, game_id, spec):
    game = Game.objects.get(pk=game_id)
    actor = membership(game, user)
    check_window(game)
    request_id = uuid.uuid4()
    order = engine.prepare_order(game.state, actor, spec, str(request_id))
    return game, actor, order, request_id
