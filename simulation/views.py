import uuid
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from . import engine, multiplayer, services
from .archives import condense_archive
from .archives import reign_archive as build_reign_archive
from .calendar import closing_moon
from .cartography import schedule, workspace_context
from .forms import GameForm, SignupForm
from .models import Game, Report
from .narration import work_effect, work_phrase
from .presentation import localize, report_view
from .projections import player_view
from .rules import ACTION_LABELS, RuleError, allocate, expedition_prices


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


def home(request):
    if not request.user.is_authenticated:
        from .guest_views import landing

        return landing(request)
    from .guest_services import guest_identity

    identity = guest_identity(request.user)
    if identity is not None:
        return redirect("game", game_id=identity.game_id)
    games = (
        Game.objects.filter(
            Q(memberships__user=request.user)
            | Q(memberships__user__shared_identity__account=request.user)
        )
        .distinct()
        .order_by("-created_at")
    )
    for game in games:
        multiplayer.check_seat_session(request, game)
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
            "cities": sum(
                city["owner"] == services.membership(game, request.user)
                for city in game.state["cities"].values()
            ),
            "shared": game.kind == "multiplayer",
            "waiting": game.kind == "multiplayer" and game.lobby_status == "waiting",
        }
        for game in games
    ]
    return render(request, "simulation/home.html", {"games": cards})


@login_required
def new_game(request):
    from .guest_services import require_registered

    require_registered(request.user)
    form = GameForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            game = services.create_game(request.user, **form.cleaned_data)
        except RuleError as error:
            form.add_error(None, localize(error.args[0]))
        else:
            return redirect(reverse("game", args=[game.id]) + "?tab=prologue")
    initial = engine.new_state()
    cities = list(initial["cities"].values())[:3]
    capture_prices = expedition_prices(initial["economy_version"])["capture"]
    capture_price = (
        initial["config"]["capture_minimum"] * capture_prices["per_person"] + capture_prices["base"]
    )
    return render(
        request,
        "simulation/new_game.html",
        {
            "form": form,
            "initial_population": sum(city["population"] for city in cities),
            "initial_fideles": sum(city["fideles"] for city in cities),
            "initial_stock_per_city": cities[0]["stock"],
            "initial_total_stock": sum(city["stock"] for city in cities),
            "initial_capture_minimum_cost": capture_price,
        },
    )


def authorized_game(request, game_id):
    queryset = (
        Game.objects.select_for_update()
        if request.method == "POST" and connection.in_atomic_block
        else Game.objects.all()
    )
    game = get_object_or_404(queryset, id=game_id)
    multiplayer.check_seat_session(request, game)
    actor = services.membership(game, request.user)
    return game, actor


def metadata(game, actor=None, user=None):
    shared = game.kind == "multiplayer"
    can_manage = (
        multiplayer.is_operator(user)
        if shared and user is not None
        else user is not None and game.owner_id == user.pk
    )
    return {
        "id": str(game.id),
        "title": game.title,
        "mode": game.mode,
        "paused": game.paused,
        "deadline": game.deadline,
        "interval_minutes": game.interval_minutes,
        "revision": multiplayer.visible_revision(game, actor) if actor is not None else 0,
        "shared": shared,
        "can_manage": can_manage,
        "can_advance": not shared and can_manage and game.mode == "manual",
        "awaiting_start": game.state.get("awaiting_start", False),
        "clock_aligned": game.state.get("clock_aligned", False),
    }


@login_required
@require_GET
def desk(request, game_id):
    game, actor = authorized_game(request, game_id)
    if game.kind == "multiplayer" and game.lobby_status in ("waiting", "cancelled"):
        return redirect("shared_lobby", game_id=game_id)
    view = localize(player_view(game.state, actor))
    for city in view["owned_cities"]:
        city["crew_assignments"] = [
            {
                "name": localize(
                    work_phrase(work["kind"], work["level"], game.state.get("economy_version", 1))
                ),
                "phase": "active",
                "start_moon": work["start_month"],
                "finish_moon": work["finish_month"],
                "anchor": f"work-{city['id']}-{index}",
            }
            for index, work in enumerate(
                w
                for w in game.state["works"]
                if w.get("city") == city["id"] and w["status"] == "active"
            )
        ]
        city["crew_assignments"].extend(
            {
                "name": localize(
                    work_phrase(task["kind"], task["level"], game.state.get("economy_version", 1))
                ),
                "phase": "reserved",
                "start_moon": order["execute_month"],
                "finish_moon": order["execute_month"] + task["duration"],
                "anchor": "order-" + order["id"],
            }
            for order in game.state["orders"]
            if order["actor"] == actor and order["status"] == "confirmed"
            for task in order["tasks"]
            if task["city"] == city["id"]
        )
        try:
            city["contribution"] = max(0, int(request.GET.get(f"men_{city['id']}", "0")))
        except ValueError:
            city["contribution"] = 0
    owned_by_id = {city["id"]: city for city in view["owned_cities"]}
    for city in view["cities"]:
        if city["id"] in owned_by_id:
            city["crew_assignments"] = owned_by_id[city["id"]]["crew_assignments"]
    for action in view["work_actions"]:
        for option in action.get("cities", []):
            option["crew_assignments"] = owned_by_id[option["id"]]["crew_assignments"]
    mission_kind = "capture" if request.GET.get("mission") == "capture" else "raid"
    price = view["expedition_prices"][mission_kind]
    contributions = {city["id"]: city["contribution"] for city in view["owned_cities"]}
    fees = allocate(price["base"], contributions)
    for city in view["owned_cities"]:
        city["expedition_charge"] = fees[city["id"]] + city["contribution"] * price["per_person"]
        city["expedition_shortfall"] = max(0, city["expedition_charge"] - city["available_stock"])
        city["expedition_remaining"] = city["available_stock"] - city["expedition_charge"]
        city["expedition_food"] = max(0, city["present_population"] - city["contribution"]) * 500
        city["expedition_siege_shortfall"] = max(
            0, city["expedition_food"] - city["expedition_remaining"]
        )
    tab = request.GET.get("tab", "map")
    if tab not in (
        "map",
        "mail",
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
    mail_section = request.GET.get("mail", "news")
    if mail_section not in ("news", "attention", "schedule", "chronicle"):
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
    target_observations = []
    if tab in ("wars", "map") and city_id:
        known = Report.objects.filter(
            game=game, recipient=actor, content__city_id=city_id
        ).order_by("-month", "-id")
        target_observations = [
            report_view(letter, state=game.state)
            for letter in known
            if letter.content.get("observation")
        ][:3]
    # Reports are immutable per-recipient records; never infer access from current ownership.
    reports = Report.objects.filter(game=game, recipient=actor)
    news_month = view["closed_moon"] or game.state["month"]
    if tab != "letters" and not (tab == "mail" and mail_section == "chronicle"):
        # The order register already shows reservations; keep receipts in the archive.
        reports = reports.filter(month=news_month).exclude(kind="order", title="Décret scellé")
    constructions = [
        {**work, "city": city["name"], "city_id": city["id"], "city_index": index}
        for city in view["owned_cities"]
        for index, work in enumerate(city["works"])
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
    recent_by_city = {}
    for letter in Report.objects.filter(
        game=game, recipient=actor, month__gte=max(1, view["closed_moon"] - 2)
    ).order_by("-month", "-id"):
        entry = report_view(letter, state=game.state)
        if entry["city_id"] and entry["city_id"] not in recent_by_city:
            recent_by_city[entry["city_id"]] = entry
    for city in view["owned_cities"]:
        city["recent_report"] = recent_by_city.get(city["id"])
    action_kind = request.GET.get("action")
    if (
        (tab == "wars" or (tab == "map" and not selected["owned"]))
        and city_id
        and selected["reachable"]
        and not selected["engaged"]
    ):
        action_kind = "expedition"
    action = next((item for item in view["work_actions"] if item["kind"] == action_kind), None)
    if action_kind == "expedition":
        action = {"kind": action_kind, "label": _("Dicter l’ordre d’une expédition")}
    elif action_kind == "convoy" and view["strategic_rules"]:
        action = {"kind": "convoy", "label": _("Acheminer des ressources")}
    elif action_kind == "equipment" and view["equipment_available"]:
        action = {"kind": action_kind, "label": _("Organiser l’armement")}
    elif (
        action_kind
        and action is None
        and not (tab == "map" and action_kind in ("works", "accounts"))
    ):
        raise Http404
    local_work = None
    if tab == "map" and action and action.get("cities") and selected["owned"]:
        local_work = next((c for c in action["cities"] if c["id"] == selected["id"]), None)
    return render(
        request,
        "simulation/chronicle.html",
        {
            "game": metadata(game, actor, request.user),
            "view": view,
            "tab": tab,
            "prologue_page": prologue_page,
            "workspace": tab in ("map", "mail", "domain", "prologue"),
            "activity": action_kind,
            "local_work": local_work,
            "mail_section": mail_section,
            "schedule": schedule(view),
            **workspace_context(view, selected, action_kind),
            "prologue_previous": prologue_page - 1,
            "prologue_next": prologue_page + 1,
            "selected": selected,
            "reports": [report_view(report, state=game.state) for report in reports],
            "news_moon": max(1, news_month),
            "action": action,
            "section_orders": [
                order
                for order in view["orders"]
                if order["status"] == "confirmed"
                and (tab != "wars" or order["kind"] in ("raid", "capture", "convoy"))
                and (tab != "constructions" or order["kind"] not in ("raid", "capture", "convoy"))
            ],
            "city_requested": city_id is not None,
            "selected_target": next(
                (target for target in view["attack_targets"] if target["id"] == city_id), None
            ),
            "mission_kind": mission_kind,
            "target_observations": target_observations,
            "combat_moon": view["open_moon"] + 1,
            "return_moon": view["open_moon"] + 2,
            "convoy_origin": request.GET.get("origin", ""),
            "convoy_target": request.GET.get("target", ""),
            "convoy_cargo": request.GET.get("cargo", ""),
            "expedition_total": sum(contributions.values()),
            "expedition_cost": price["base"] + sum(contributions.values()) * price["per_person"],
            "expedition_capacity": sum(
                city["contribution"] * city.get("carry_per_survivor", 5000)
                for city in view["owned_cities"]
            ),
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
def reign_archive(request, game_id):
    scope = request.GET.get("scope", "player")
    game = get_object_or_404(Game, id=game_id)
    if game.kind == "multiplayer" and scope == "all" and multiplayer.is_operator(request.user):
        actor = None
    else:
        game, actor = authorized_game(request, game_id)
    output = request.GET.get("format", "html")
    if scope not in {"player", "all"} or output not in {"html", "json", "compact"}:
        raise Http404
    archive = build_reign_archive(game, request.user, actor, scope)
    if output == "compact":
        response = JsonResponse(
            condense_archive(archive),
            json_dumps_params={"ensure_ascii": False, "separators": (",", ":")},
        )
        response["Content-Disposition"] = (
            f'attachment; filename="yaara-{game.pk}-{scope}-compact.json"'
        )
    elif output == "json":
        response = JsonResponse(archive, json_dumps_params={"ensure_ascii": False, "indent": 2})
        response["Content-Disposition"] = f'attachment; filename="yaara-{game.pk}-{scope}.json"'
    else:
        response = render(
            request,
            "simulation/reign_archive.html",
            {
                "game": metadata(game, actor, request.user),
                "view": localize(player_view(game.state, actor)) if actor else {"finished": True},
                "archive": archive,
                "has_personal_book": actor is not None,
                "archive_base": "simulation/base.html"
                if actor is None
                else "simulation/manuscript.html",
                "can_read_all": multiplayer.is_operator(request.user)
                if game.kind == "multiplayer"
                else game.owner_id == request.user.pk,
                "tab": "domain",
            },
        )
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@require_GET
def state_view(request, game_id):
    game, actor = authorized_game(request, game_id)
    response = JsonResponse(
        {
            "game": metadata(game, actor, request.user),
            "view": localize(player_view(game.state, actor)),
        }
    )
    response["Cache-Control"] = "private, no-store"
    return response


def order_form_url(game, spec):
    """Return only to a local, known action; the query is an unsealed selection."""
    kind = spec.get("kind")
    query = {"tab": "decrees"}
    if kind in ("raid", "capture"):
        query = {"tab": "map", "action": "expedition", "mission": kind}
        if spec.get("target") in game.state["cities"]:
            query["city"] = spec["target"]
        query.update(
            (f"men_{city}", count)
            for city, count in spec.get("contributions", {}).items()
            if city in game.state["cities"]
        )
    elif kind == "convoy":
        query = {
            "tab": "map",
            "action": "convoy",
            "origin": spec.get("origin", ""),
            "target": spec.get("target", ""),
            "cargo": spec.get("cargo", ""),
        }
    elif kind in ACTION_LABELS:
        query = {"tab": "constructions", "action": kind, "cities": spec.get("cities", [])}
        if len(spec.get("cities", [])) == 1:
            query = {"tab": "map", "action": kind, "city": spec["cities"][0]}
    return reverse("game", args=[game.id]) + "?" + urlencode(query, doseq=True)


@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
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
            if (
                data["revision"] != multiplayer.visible_revision(game, actor)
                or data["month"] != game.state["month"]
            ):
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
        elif kind == "convoy":
            try:
                cargo = int(request.POST.get("cargo", "0"))
            except ValueError:
                cargo = 0
            spec.update(
                origin=request.POST.get("origin"), target=request.POST.get("target"), cargo=cargo
            )
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
                "revision": multiplayer.visible_revision(game, actor),
                "spec": spec,
            },
            salt="yaara-order",
        )
    kind = spec["kind"]
    city_names = {city_id: city["name"] for city_id, city in game.state["cities"].items()}
    own_view = player_view(game.state, actor)
    own_by_id = {city["id"]: city for city in own_view["owned_cities"]}
    funding = [
        {
            "name": city_names[city_id],
            "amount": amount,
            "remaining": own_by_id[city_id]["available_stock"] - amount,
            "siege_food": max(
                0,
                own_by_id[city_id]["present_population"]
                - order.get("contributions", {}).get(city_id, 0),
            )
            * (500 if game.state["rules"] == "V1" else 0),
            "siege_shortfall": max(
                0,
                max(
                    0,
                    own_by_id[city_id]["present_population"]
                    - order.get("contributions", {}).get(city_id, 0),
                )
                * (500 if game.state["rules"] == "V1" else 0)
                - (own_by_id[city_id]["available_stock"] - amount),
            ),
        }
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
            "description": work_phrase(
                task["kind"], task["level"], game.state.get("economy_version", 1)
            ),
            "effect": work_effect(
                task["kind"], task["level"], game.state.get("economy_version", 1)
            ),
            "finish_month": order["execute_month"] + task["duration"],
        }
        for task in order["tasks"]
    ]
    preview_view = localize(own_view)
    selected_id = (
        spec.get("target") or spec.get("origin") or next(iter(spec.get("cities", [])), None)
    )
    selected = next((c for c in preview_view["cities"] if c["id"] == selected_id), None)
    return render(
        request,
        "simulation/decree_letter.html",
        {
            "game": metadata(game, actor, request.user),
            "label": localize(ACTION_LABELS[kind]),
            "workspace": True,
            "selected": selected,
            "city_requested": selected is not None,
            "edit_url": order_form_url(game, spec),
            **workspace_context(preview_view, selected),
            "view": preview_view,
            "tab": "decrees",
            "order": order,
            "target": city_names.get(order.get("target")),
            "origin": city_names.get(order.get("origin")),
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
@transaction.atomic
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
            reverse("game", args=[game_id]) + "?tab=mail&mail=schedule#order-" + order["id"]
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
@transaction.atomic
def cancel_order(request, game_id, order_id):
    authorized_game(request, game_id)
    destination = request.POST.get("return_tab", "decrees")
    if destination not in ("domain", "decrees", "constructions", "wars", "mail", "map"):
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
    return redirect(
        f"/games/{game_id}/?tab={destination}" + ("&mail=schedule" if destination == "mail" else "")
    )


@login_required
@require_POST
@transaction.atomic
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
@transaction.atomic
def pause(request, game_id):
    authorized_game(request, game_id)
    try:
        services.toggle_pause(request.user, game_id)
    except RuleError as error:
        messages.error(request, localize(error.args[0]))
    return redirect("game", game_id=game_id)


@login_required
@require_POST
@transaction.atomic
def start(request, game_id):
    authorized_game(request, game_id)
    services.start_calendar(request.user, game_id)
    return redirect("game", game_id=game_id)


def error_view(request, exception=None, status=404):
    return render(request, "simulation/error.html", {"status": status}, status=status)


def csrf_failure(request, reason=""):
    return error_view(request, status=403)
