import uuid
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from . import engine, services
from .calendar import closing_moon
from .forms import GameForm, SignupForm
from .models import Game, Report
from .narration import work_effect, work_phrase
from .presentation import localize, report_view
from .projections import player_view
from .rules import ACTION_LABELS, EXPEDITION_PRICES, RuleError, allocate


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
        raise PermissionDenied(_("La création de comptes est actuellement fermée."))
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
            "month": game.state["month"]
            if game.state["status"] == "finished"
            else closing_moon(game.state),
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
            form.add_error(None, localize(error.args[0]))
        else:
            return redirect(reverse("game", args=[game.id]) + "?tab=prologue")
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
        "awaiting_start": game.state.get("awaiting_start", False),
        "clock_aligned": game.state.get("clock_aligned", False),
    }


@login_required
@require_GET
def desk(request, game_id):
    game, actor = authorized_game(request, game_id)
    view = localize(player_view(game.state, actor))
    for city in view["owned_cities"]:
        try:
            city["contribution"] = max(0, int(request.GET.get(f"men_{city['id']}", "0")))
        except ValueError:
            city["contribution"] = 0
    mission_kind = "capture" if request.GET.get("mission") == "capture" else "raid"
    price = EXPEDITION_PRICES[mission_kind]
    contributions = {city["id"]: city["contribution"] for city in view["owned_cities"]}
    fees = allocate(price["base"], contributions)
    for city in view["owned_cities"]:
        city["expedition_charge"] = fees[city["id"]] + city["contribution"] * price["per_person"]
        city["expedition_shortfall"] = max(0, city["expedition_charge"] - city["available_stock"])
    tab = request.GET.get("tab", "domain")
    if tab not in (
        "domain",
        "decrees",
        "constructions",
        "wars",
        "letters",
        "city",
        "help",
        "prologue",
    ):
        raise Http404
    prologue_page = 1
    if tab == "prologue":
        try:
            prologue_page = int(request.GET.get("page", "1"))
        except ValueError as error:
            raise Http404 from error
        if not 1 <= prologue_page <= 4:
            raise Http404
    city_id = request.GET.get("city")
    selected = next((city for city in view["cities"] if city["id"] == city_id), None)
    if selected is None and (city_id is not None or tab == "city"):
        raise Http404
    if selected is None:
        selected = next(iter(view["owned_cities"]), view["cities"][0])
    # Reports are immutable per-recipient records; never infer access from current ownership.
    reports = Report.objects.filter(game=game, recipient=actor)
    news_month = view["closed_moon"] or game.state["month"]
    if tab != "letters":
        reports = reports.filter(month=news_month)
    constructions = [
        {**work, "city": city["name"], "city_id": city["id"]}
        for city in view["owned_cities"]
        for work in city["works"]
    ]
    milestones = []
    if not view["finished"]:
        milestones.extend(
            {
                "moon": order["execute_month"],
                "label": order["label"],
                "detail": order["destination"],
                "tab": "decrees",
            }
            for order in view["orders"]
            if order["status"] == "confirmed"
        )
        milestones.extend(
            {
                "moon": work["finish_month"],
                "label": work["label"],
                "detail": work["city"],
                "tab": "constructions",
            }
            for work in constructions
        )
        milestones.extend(
            {
                "moon": work["finish_month"],
                "label": _("Armement achevé"),
                "detail": view["realm"],
                "tab": "constructions",
            }
            for work in view["equipment_work"]
        )
        for mission in view["missions"]:
            if not mission["returning"]:
                milestones.append(
                    {
                        "moon": mission["combat_month"],
                        "label": _("Combat prévu"),
                        "detail": mission["target"],
                        "tab": "wars",
                    }
                )
            milestones.append(
                {
                    "moon": mission["return_month"],
                    "label": _("Retour prévu"),
                    "detail": mission["target"],
                    "tab": "wars",
                }
            )
        milestones.append(
            {
                "moon": view["harvest_moon"],
                "label": _("Versement de la récolte"),
                "detail": "",
                "tab": "domain",
            }
        )
        milestones.sort(key=lambda item: item["moon"])
    action_kind = request.GET.get("action")
    action = next((item for item in view["work_actions"] if item["kind"] == action_kind), None)
    if action_kind == "expedition":
        action = {"kind": action_kind, "label": _("Dicter l’ordre d’une expédition")}
    elif action_kind == "equipment" and view["equipment_available"]:
        action = {"kind": action_kind, "label": _("Organiser l’armement")}
    elif action_kind and action is None:
        raise Http404
    return render(
        request,
        "simulation/chronicle.html",
        {
            "game": metadata(game),
            "view": view,
            "tab": tab,
            "prologue_page": prologue_page,
            "prologue_previous": prologue_page - 1,
            "prologue_next": prologue_page + 1,
            "nav_section": "wars"
            if action_kind == "expedition" or tab == "wars"
            else "constructions"
            if tab == "constructions" or action_kind
            else "domain",
            "selected": selected,
            "reports": [report_view(report) for report in reports],
            "news_moon": max(1, news_month),
            "action": action,
            "section_orders": [
                order
                for order in view["orders"]
                if (tab != "wars" or order["kind"] in ("raid", "capture"))
                and (tab != "constructions" or order["kind"] not in ("raid", "capture"))
            ],
            "city_requested": city_id is not None,
            "selected_target": next(
                (target for target in view["attack_targets"] if target["id"] == city_id), None
            ),
            "mission_kind": mission_kind,
            "expedition_total": sum(contributions.values()),
            "expedition_cost": price["base"] + sum(contributions.values()) * price["per_person"],
            "selected_cities": request.GET.getlist("cities"),
            "constructions": constructions,
            "construction_count": len(constructions) + len(view["equipment_work"]),
            "milestones": milestones,
            "neighbors": [
                link["second"] if link["first"]["id"] == selected["id"] else link["first"]
                for link in view["links"]
                if selected["id"] in (link["first"]["id"], link["second"]["id"])
            ],
            "attack_origins": {
                target["id"]: target["origins"] for target in view["attack_targets"]
            },
        },
    )


@login_required
@require_GET
def state_view(request, game_id):
    game, actor = authorized_game(request, game_id)
    return JsonResponse({"game": metadata(game), "view": localize(player_view(game.state, actor))})


def order_form_url(game, spec):
    """Return only to a local, known action; the query is an unsealed selection."""
    kind = spec.get("kind")
    query = {"tab": "decrees"}
    if kind in ("raid", "capture"):
        query = {"tab": "wars", "action": "expedition", "mission": kind}
        if spec.get("target") in game.state["cities"]:
            query["city"] = spec["target"]
        query.update(
            (f"men_{city}", count)
            for city, count in spec.get("contributions", {}).items()
            if city in game.state["cities"]
        )
    elif kind in ACTION_LABELS:
        query = {"tab": "constructions", "action": kind, "cities": spec.get("cities", [])}
    return reverse("game", args=[game.id]) + "?" + urlencode(query, doseq=True)


@login_required
@require_http_methods(["GET", "POST"])
def preview_order(request, game_id):
    game, actor = authorized_game(request, game_id)
    spec = {}
    if request.method == "GET":
        payload = request.GET.get("payload", "")
        try:
            data = signing.loads(payload, salt="yaara-order", max_age=3600)
            if (
                data["game_id"] != str(game_id)
                or data["user_id"] != request.user.pk
                or data["actor"] != actor
            ):
                raise signing.BadSignature
            spec = data["spec"]
            if data["revision"] != game.revision or data["month"] != game.state["month"]:
                raise signing.BadSignature
            services.check_window(game, data["month"])
            order = engine.prepare_order(game.state, actor, spec, data["request_id"])
        except (signing.BadSignature, KeyError, ValueError) as error:
            messages.error(
                request,
                localize(error.args[0])
                if isinstance(error, RuleError)
                else _("Ce devis n’est plus valable. Préparez à nouveau votre décret."),
            )
            return redirect(order_form_url(game, spec))
    else:
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
                messages.error(request, _("Les effectifs doivent être des nombres entiers."))
                spec.update(target=request.POST.get("target"))
                return redirect(order_form_url(game, spec))
            spec.update({"target": request.POST.get("target"), "contributions": contributions})
        elif kind != "equipment":
            spec["cities"] = request.POST.getlist("cities")
        try:
            game, actor, order, request_id = services.quote(request.user, game_id, spec)
        except RuleError as error:
            messages.error(request, localize(error.args[0]))
            return redirect(order_form_url(game, spec))
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
    kind = spec["kind"]
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
            "effect": work_effect(
                task["kind"], task["level"], game.state.get("economy_version", 1)
            ),
            "finish_month": order["execute_month"] + task["duration"],
        }
        for task in order["tasks"]
    ]
    return render(
        request,
        "simulation/decree_letter.html",
        {
            "game": metadata(game),
            "label": localize(ACTION_LABELS[kind]),
            "view": localize(player_view(game.state, actor)),
            "tab": "decrees",
            "nav_section": "wars" if kind in ("raid", "capture") else "constructions",
            "order": order,
            "target": city_names.get(order.get("target")),
            "funding": funding,
            "contributions": contributions,
            "tasks": localize(tasks),
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
    game, actor = authorized_game(request, game_id)
    destination = order_form_url(game, {})
    try:
        data = signing.loads(request.POST.get("payload", ""), salt="yaara-order", max_age=3600)
        if data["game_id"] != str(game_id) or data["user_id"] != request.user.pk:
            raise signing.BadSignature
        destination = order_form_url(game, data["spec"])
        order = services.confirm(
            request.user,
            game_id,
            data["spec"],
            uuid.UUID(data["request_id"]),
            data["month"],
            data["revision"],
        )
        destination = (
            reverse("game", args=[game_id])
            + "?tab="
            + ("wars" if order["kind"] in ("raid", "capture") else "constructions")
        )
        messages.success(
            request,
            _(
                "J’ai reçu votre sceau. Les moyens promis attendent l’entrée en vigueur de votre décret."
            ),
        )
    except (signing.BadSignature, KeyError, ValueError) as error:
        messages.error(
            request,
            localize(error.args[0])
            if isinstance(error, RuleError)
            else _("Ce devis n’est plus valable. Préparez à nouveau votre décret."),
        )
    return redirect(destination)


@login_required
@require_POST
def cancel_order(request, game_id, order_id):
    authorized_game(request, game_id)
    destination = request.POST.get("return_tab", "decrees")
    if destination not in ("domain", "decrees", "constructions", "wars"):
        destination = "decrees"
    try:
        services.cancel(request.user, game_id, str(order_id))
        messages.success(
            request,
            _(
                "J’ai retiré ce décret de nos engagements. Les moyens qu’il promettait sont de nouveau libres."
            ),
        )
    except RuleError as error:
        messages.error(request, localize(error.args[0]))
    return redirect(f"/games/{game_id}/?tab={destination}")


@login_required
@require_POST
def advance(request, game_id):
    authorized_game(request, game_id)
    try:
        target = int(request.POST.get("month", "0"))
        execution, executed = services.tick(game_id, target, request.user)
        if executed:
            messages.success(
                request,
                _(
                    "La lune {moon} est désormais consignée dans ces chroniques. Voici les nouvelles qui nous sont parvenues."
                ).format(moon=target),
            )
        else:
            messages.info(
                request,
                _("Ce mois figure déjà dans nos chroniques. Je n’en ai pas répété les événements."),
            )
    except (ValueError, RuleError) as error:
        messages.error(
            request,
            localize(error.args[0])
            if isinstance(error, RuleError)
            else _("Le mois demandé est invalide."),
        )
    return redirect("game", game_id=game_id)


@login_required
@require_POST
def pause(request, game_id):
    authorized_game(request, game_id)
    try:
        services.toggle_pause(request.user, game_id)
    except RuleError as error:
        messages.error(request, localize(error.args[0]))
    return redirect("game", game_id=game_id)


@login_required
@require_POST
def start(request, game_id):
    authorized_game(request, game_id)
    services.start_calendar(request.user, game_id)
    return redirect("game", game_id=game_id)


def error_view(request, exception=None, status=404):
    return render(request, "simulation/error.html", {"status": status}, status=status)


def csrf_failure(request, reason=""):
    return error_view(request, status=403)
