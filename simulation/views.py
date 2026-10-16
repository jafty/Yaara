import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from . import services
from .forms import GameForm, SignupForm
from .models import Game, Report
from .narration import work_phrase
from .projections import player_view
from .rules import ACTION_LABELS, RuleError


@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    if not settings.SIGNUP_ENABLED:
        raise PermissionDenied("La création de comptes est actuellement fermée.")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("home")
    return render(request, "registration/signup.html", {"form": form})


@login_required
def home(request):
    games = Game.objects.filter(memberships__user=request.user).order_by("-created_at")
    cards = [
        {
            "id": game.id,
            "title": game.title,
            "month": game.state["month"],
            "rules": game.state["rules"],
            "finished": game.state["status"] == "finished",
            "reign_months": game.state["config"]["reign_months"],
            "mode": game.mode,
            "cities": sum(city["owner"] == "p1" for city in game.state["cities"].values()),
        }
        for game in games
    ]
    return render(request, "simulation/home.html", {"games": cards})


@login_required
def new_game(request):
    form = GameForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            game = services.create_game(request.user, **form.cleaned_data)
        except RuleError as error:
            form.add_error(None, str(error))
        else:
            return redirect("game", game_id=game.id)
    return render(request, "simulation/new_game.html", {"form": form})


def authorized_game(request, game_id):
    game = get_object_or_404(Game, id=game_id)
    actor = services.membership(game, request.user)
    return game, actor


def metadata(game):
    return {
        "id": str(game.id),
        "title": game.title,
        "mode": game.mode,
        "paused": game.paused,
        "deadline": game.deadline,
        "interval_minutes": game.interval_minutes,
        "revision": game.revision,
    }


@login_required
@require_GET
def desk(request, game_id):
    game, actor = authorized_game(request, game_id)
    view = player_view(game.state, actor)
    tab = request.GET.get("tab", "domain")
    if tab not in ("domain", "decrees", "letters"):
        raise Http404
    city_id = request.GET.get("city")
    selected = next((city for city in view["cities"] if city["id"] == city_id), None)
    if selected is None:
        selected = next(iter(view["owned_cities"]), view["cities"][0])
    # Reports are immutable per-recipient records; never infer access from current ownership.
    reports = Report.objects.filter(game=game, recipient=actor)[: 100 if tab == "letters" else 4]
    return render(
        request,
        "simulation/chronicle.html",
        {
            "game": metadata(game),
            "view": view,
            "tab": tab,
            "selected": selected,
            "reports": reports,
            "attack_origins": {
                target["id"]: target["origins"] for target in view["attack_targets"]
            },
        },
    )


@login_required
@require_GET
def state_view(request, game_id):
    game, actor = authorized_game(request, game_id)
    return JsonResponse({"game": metadata(game), "view": player_view(game.state, actor)})


@login_required
@require_POST
def preview_order(request, game_id):
    authorized_game(request, game_id)
    kind = request.POST.get("kind", "")
    spec = {"kind": kind}
    if kind in ("raid", "capture"):
        try:
            contributions = {
                key.removeprefix("men_"): int(value or 0)
                for key, value in request.POST.items()
                if key.startswith("men_")
            }
        except ValueError:
            messages.error(request, "Les effectifs doivent être des nombres entiers.")
            return redirect(f"/games/{game_id}/?tab=decrees")
        spec.update({"target": request.POST.get("target"), "contributions": contributions})
    elif kind != "equipment":
        spec["cities"] = request.POST.getlist("cities")
    try:
        game, actor, order, request_id = services.quote(request.user, game_id, spec)
    except RuleError as error:
        messages.error(request, str(error))
        return redirect(f"/games/{game_id}/?tab=decrees")
    payload = signing.dumps(
        {
            "game_id": str(game.id),
            "actor": actor,
            "user_id": request.user.pk,
            "request_id": str(request_id),
            "month": game.state["month"],
            "revision": game.revision,
            "spec": spec,
        },
        salt="yaara-order",
    )
    city_names = {city_id: city["name"] for city_id, city in game.state["cities"].items()}
    funding = [
        {"name": city_names[city_id], "amount": amount}
        for city_id, amount in order["funding"].items()
        if amount
    ]
    contributions = [
        {"name": city_names[city_id], "count": count}
        for city_id, count in order.get("contributions", {}).items()
    ]
    tasks = [
        {
            "name": city_names[task["city"]],
            "level": task["level"],
            "description": work_phrase(task["kind"], task["level"]),
            "finish_month": order["execute_month"] + task["duration"],
        }
        for task in order["tasks"]
    ]
    return render(
        request,
        "simulation/decree_letter.html",
        {
            "game": metadata(game),
            "label": ACTION_LABELS[kind],
            "order": order,
            "target": city_names.get(order.get("target")),
            "funding": funding,
            "contributions": contributions,
            "tasks": tasks,
            "payload": payload,
            "combat_month": order["execute_month"] + 1,
            "return_month": order["execute_month"] + 2,
            "finish_month": order["execute_month"] + order.get("duration", 0),
            "cancellable": game.state["rules"] == "V1",
        },
    )


@login_required
@require_POST
def confirm_order(request, game_id):
    authorized_game(request, game_id)
    try:
        data = signing.loads(request.POST.get("payload", ""), salt="yaara-order", max_age=3600)
        if data["game_id"] != str(game_id) or data["user_id"] != request.user.pk:
            raise signing.BadSignature
        services.confirm(
            request.user,
            game_id,
            data["spec"],
            uuid.UUID(data["request_id"]),
            data["month"],
            data["revision"],
        )
        messages.success(
            request,
            "J’ai reçu votre sceau. Les moyens promis attendent l’entrée en vigueur de votre décret.",
        )
    except (signing.BadSignature, KeyError, ValueError) as error:
        messages.error(
            request,
            str(error)
            if isinstance(error, RuleError)
            else "Ce devis n’est plus valable. Préparez à nouveau votre décret.",
        )
    return redirect(f"/games/{game_id}/?tab=decrees")


@login_required
@require_POST
def cancel_order(request, game_id, order_id):
    authorized_game(request, game_id)
    try:
        services.cancel(request.user, game_id, str(order_id))
        messages.success(
            request,
            "J’ai retiré ce décret de nos engagements. Les moyens qu’il promettait sont de nouveau libres.",
        )
    except RuleError as error:
        messages.error(request, str(error))
    return redirect(f"/games/{game_id}/?tab=decrees")


@login_required
@require_POST
def advance(request, game_id):
    authorized_game(request, game_id)
    try:
        target = int(request.POST.get("month", "0"))
        _, executed = services.tick(game_id, target, request.user)
        if executed:
            messages.success(
                request,
                f"Le mois {target} est désormais consigné dans ces chroniques. Voici les nouvelles qui nous sont parvenues.",
            )
        else:
            messages.info(
                request,
                "Ce mois figure déjà dans nos chroniques. Je n’en ai pas répété les événements.",
            )
    except (ValueError, RuleError) as error:
        messages.error(
            request, str(error) if isinstance(error, RuleError) else "Le mois demandé est invalide."
        )
    return redirect("game", game_id=game_id)


@login_required
@require_POST
def pause(request, game_id):
    authorized_game(request, game_id)
    try:
        services.toggle_pause(request.user, game_id)
    except RuleError as error:
        messages.error(request, str(error))
    return redirect("game", game_id=game_id)


def error_view(request, exception=None, status=404):
    return render(request, "simulation/error.html", {"status": status}, status=status)


def csrf_failure(request, reason=""):
    return error_view(request, status=403)
