"""Authorized commands and transaction boundaries; one lock for every game mutation."""

import secrets
import uuid
from datetime import timedelta
from datetime import timezone as datetime_timezone

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from . import engine
from .calendar import closing_moon
from .messages import describe, message
from .models import CommandReceipt, Game, Participant, Report, TargetEngagement, TickExecution
from .narration import number
from .rules import ACTION_LABELS, RuleError


def membership(game, user):
    participant = Participant.objects.filter(game=game, user=user).first()
    if participant is None:
        raise PermissionDenied(message("Vous ne participez pas à cette partie."))
    return participant.actor


def check_window(game, expected_month=None):
    if game.paused:
        raise RuleError(
            message("La partie est en pause. Reprenez le calendrier pour donner un ordre.")
        )
    if game.state["status"] != "active":
        raise RuleError(message("Ce règne est terminé."))
    if game.deadline and timezone.now() >= game.deadline:
        raise RuleError(
            message("Le mois est clos. Vérifiez le départ et le devis du mois suivant.")
        )
    if expected_month is not None and expected_month != game.state["month"]:
        raise RuleError(message("Le calendrier a changé. Préparez à nouveau votre décret."))


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
    events = [
        {
            **event,
            "content": event.get(
                "content",
                {
                    "title": describe(event["title"]),
                    "body": describe(event["body"]),
                },
            ),
        }
        for event in events
    ]
    Report.objects.bulk_create(
        [
            Report(
                game=game,
                month=event.get("month", game.state["month"]),
                **{key: value for key, value in event.items() if key != "month"},
            )
            for event in events
        ]
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
    player_name=message("La maison d’Ambre"),
    calendar_version=2,
    forge_version=2,
    map_version=3,
    economy_version=2,
):
    # Serialize account-level creation limits as well as each game's commands.
    get_user_model().objects.select_for_update().get(pk=user.pk)
    if Game.objects.filter(owner=user).count() >= 30:
        raise RuleError(
            message("Vous avez déjà trente parties. Conservez vos règnes existants pour le moment.")
        )
    if mode not in ("manual", "scheduled") or interval_minutes not in (5, 10):
        raise RuleError(message("Ce calendrier n’est pas disponible."))
    state = engine.new_state(
        version,
        reign_months,
        opponents,
        player_name,
        calendar_version=calendar_version,
        forge_version=forge_version,
        map_version=map_version,
        economy_version=economy_version,
    )
    awaiting_start = mode == "scheduled" and economy_version >= 2
    if awaiting_start:
        state["awaiting_start"] = True
    game = Game.objects.create(
        owner=user,
        title=title,
        state=state,
        seed=secrets.token_hex(32),
        mode=mode,
        interval_minutes=interval_minutes,
        remaining_seconds=interval_minutes * 60,
        deadline=timezone.now() + timedelta(minutes=interval_minutes)
        if mode == "scheduled" and not awaiting_start
        else None,
        paused=awaiting_start,
    )
    Participant.objects.create(game=game, user=user, actor="p1")
    welcome = []
    engine.report(
        welcome,
        recipient="p1",
        kind="welcome",
        title=message("Le sceau vous appartient"),
        body=message(
            "J’ai fait ouvrir les registres de vos trois cités. Leurs habitants reconnaissent votre autorité, mais il nous appartient encore de préparer les années qui viennent. Chaque cité gardera ses réserves ; pour vos dépenses, je demanderai à tous les greniers de contribuer selon leurs moyens. La première récolte nous sera versée au mois 12. D’ici là, je tiendrai compte des hommes partis et des ouvrages que vous aurez ordonnés."
        ),
    )
    if economy_version >= 2:
        welcome[0]["body"] = str(
            message(
                "Le règne avance de lune en lune. Les ordres scellés prennent effet à la clôture. Chaque cité finance ses travaux ; les origines financent leurs expéditions. Le prélèvement est automatique et entre aux greniers toutes les douze lunes, sans ordre de collecte."
            )
        )
        welcome[0]["content"]["body"] = describe(message(welcome[0]["body"]))
    Report.objects.create(game=game, month=state["month"], **welcome[0])
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
        raise RuleError(
            message("La situation a changé depuis ce devis. Vérifiez à nouveau vos moyens.")
        )
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
                "title": message("Décret scellé"),
                "body": message(
                    "J’ai placé sous votre sceau cet ordre : {p0}. Les greniers promettent {p1} Mesures, qui ne seront dépensées qu’au départ, au mois {p2}. Les hommes et les emplacements nécessaires vous sont désormais réservés.",
                    p0=ACTION_LABELS[order["kind"]].lower(),
                    p1=number(order["cost"]),
                    p2=order["execute_month"],
                ),
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
                "title": message("Décret retiré"),
                "body": message(
                    "Selon votre volonté, j’ai retiré ce décret : {p0}. Les moyens qu’il engageait sont de nouveau libres.",
                    p0=ACTION_LABELS[order["kind"]].lower(),
                )
                + (
                    message(" Une autre expédition pourra désormais engager la cible.")
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
                message("Le calendrier de cette partie ne peut pas être avancé manuellement.")
            )
    # The explicit target month makes HTTP and scheduler retries safe.
    existing = TickExecution.objects.filter(game=game, month=expected_month).first()
    if existing:
        return existing, False
    if game.paused or game.state["status"] != "active":
        raise RuleError(message("Le calendrier de cette partie est arrêté."))
    if expected_month != closing_moon(game.state):
        raise RuleError(message("Ce mois ne peut pas être résolu. Actualisez la page."))
    now = timezone.now()
    if game.mode == "scheduled":
        if not game.deadline or now < game.deadline:
            raise RuleError(message("La prochaine clôture n’est pas encore atteinte."))
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
                        "title": message("Le calendrier est suspendu"),
                        "body": message(
                            "Le traitement a pris du retard. Reprenez la partie pour ouvrir une nouvelle fenêtre de décision complète."
                        ),
                    }
                    for member in game.memberships.all()
                ],
            )
            return None, False
    bot_commands = engine.bot_orders(game.state, game.seed)
    events, audit = engine.advance_month(game.state, game.seed)
    events = [{**event, "month": expected_month} for event in events]
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
        raise PermissionDenied(message("Cette partie ne peut pas être suspendue."))
    if game.state.get("awaiting_start"):
        raise RuleError(message("Commencez le règne pour ouvrir la première lune."))
    if game.paused:
        game.deadline = timezone.now() + timedelta(seconds=max(1, game.remaining_seconds))
        if game.state.get("clock_aligned"):
            game.deadline = aligned_deadline(game.deadline, game.interval_minutes, inclusive=True)
        game.paused = False
    else:
        if game.deadline <= timezone.now():
            raise RuleError(
                message(
                    "La clôture est déjà atteinte ; attendez son traitement avant de suspendre la partie."
                )
            )
        game.remaining_seconds = max(1, int((game.deadline - timezone.now()).total_seconds()))
        game.deadline = None
        game.paused = True
    persist(game)


@transaction.atomic
def start_calendar(user, game_id):
    game = Game.objects.select_for_update().get(pk=game_id)
    membership(game, user)
    if game.owner_id != user.pk or game.mode != "scheduled":
        raise PermissionDenied(message("Cette partie ne peut pas être commencée ainsi."))
    if game.state.get("awaiting_start"):
        game.state["awaiting_start"] = False
        game.paused = False
        game.state["clock_aligned"] = True
        game.deadline = aligned_deadline(timezone.now(), game.interval_minutes)
        persist(game)


def aligned_deadline(instant, interval_minutes, *, inclusive=False):
    instant = instant.astimezone(datetime_timezone.utc)
    boundary = instant.replace(second=0, microsecond=0)
    boundary -= timedelta(minutes=boundary.minute % interval_minutes)
    if boundary < instant or not inclusive:
        boundary += timedelta(minutes=interval_minutes)
    return boundary


def quote(user, game_id, spec):
    game = Game.objects.get(pk=game_id)
    actor = membership(game, user)
    check_window(game)
    request_id = uuid.uuid4()
    order = engine.prepare_order(game.state, actor, spec, str(request_id))
    return game, actor, order, request_id
