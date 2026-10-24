"""Cohesive operator, private seat entry and waiting-room web flows."""

from django import forms
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_GET, require_http_methods

from . import multiplayer, services
from .models import Game
from .presentation import localize
from .rules import RuleError


class SharedGameForm(forms.Form):
    title = forms.CharField(
        label=gettext_lazy("Nom du règne"),
        max_length=80,
        initial=gettext_lazy("Les chroniques de Yaara"),
    )
    play_window = forms.CharField(
        label=gettext_lazy("Plages de jeu convenues"),
        max_length=240,
        help_text=gettext_lazy(
            "Indiquez les jours, heures et fuseau horaire prévus pour jouer ensemble."
        ),
    )
    reign_months = forms.TypedChoiceField(
        label=gettext_lazy("Durée du règne"),
        coerce=int,
        choices=[
            (120, gettext_lazy("10 ans · 120 mois")),
            (24, gettext_lazy("2 ans · 24 mois")),
            (60, gettext_lazy("5 ans · 60 mois")),
            (240, gettext_lazy("20 ans · 240 mois")),
        ],
        initial=120,
    )
    interval_minutes = forms.TypedChoiceField(
        label=gettext_lazy("Cadence"),
        coerce=int,
        choices=[
            (10, gettext_lazy("Une lune toutes les dix minutes")),
            (5, gettext_lazy("Une lune toutes les cinq minutes")),
        ],
        initial=10,
    )


def private_response(response):
    response["Cache-Control"] = "private, no-store"
    response["Referrer-Policy"] = "same-origin"
    response["X-Robots-Tag"] = "noindex, nofollow"
    return response


def room_context(game, include_tokens=False):
    context = {
        "room": game,
        "seats": [
            {
                "actor": invitation.actor,
                "house": localize(game.state["players"][invitation.actor]["name"]),
                "claimed": game.memberships.filter(actor=invitation.actor).exists(),
                "revoked": invitation.revoked,
                **({"token": multiplayer.invitation_token(invitation)} if include_tokens else {}),
            }
            for invitation in game.invitations.order_by("actor")
        ],
        "can_start": multiplayer.can_start(game),
        "can_read_all": game.state["status"] == "finished",
    }
    return context


@login_required
@require_http_methods(["GET", "POST"])
def manage(request):
    multiplayer.require_operator(request.user)
    form = SharedGameForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            game = multiplayer.create_shared(request.user, **form.cleaned_data)
        except RuleError as error:
            form.add_error(None, localize(error.args[0]))
        else:
            return redirect("shared_operator_room", game_id=game.pk)
    return private_response(
        render(
            request,
            "simulation/shared_manage.html",
            {
                "form": form,
                "rooms": Game.objects.filter(kind="multiplayer").order_by("-created_at"),
            },
        )
    )


@login_required
@require_http_methods(["GET", "POST"])
def operator_room(request, game_id):
    multiplayer.require_operator(request.user)
    game = get_object_or_404(Game, pk=game_id, kind="multiplayer")
    if request.method == "POST":
        try:
            action = request.POST.get("action")
            if action == "start":
                multiplayer.start_shared(request.user, game.pk)
                if game.memberships.filter(multiplayer.member_query(request.user)).exists():
                    return redirect("game", game_id=game.pk)
            elif action == "pause":
                services.toggle_pause(request.user, game.pk)
            elif action == "rotate":
                multiplayer.issue_invitation(request.user, game.pk, request.POST.get("actor"))
            elif action == "revoke":
                if request.POST.get("actor") not in multiplayer.ACTORS:
                    raise PermissionDenied
                multiplayer.revoke_invitation(request.user, game.pk, request.POST["actor"])
            elif action == "cancel":
                multiplayer.cancel_shared(request.user, game.pk)
            else:
                raise PermissionDenied
        except RuleError as error:
            messages.error(request, localize(error.args[0]))
        return redirect("shared_operator_room", game_id=game.pk)
    context = room_context(game, include_tokens=True)
    context["own_seat"] = game.memberships.filter(multiplayer.member_query(request.user)).exists()
    for seat in context["seats"]:
        seat["url"] = request.build_absolute_uri(reverse("shared_invite", args=[seat["token"]]))
    return private_response(render(request, "simulation/shared_operator.html", context))


def waiting_status(game):
    seats = {actor: game.memberships.filter(actor=actor).exists() for actor in multiplayer.ACTORS}
    return {
        "started": game.lobby_status == "running",
        "cancelled": game.lobby_status == "cancelled",
        "seats": seats,
        "can_start": multiplayer.can_start(game),
        "url": reverse("game", args=[game.pk]),
    }


@login_required
@require_GET
def operator_state(request, game_id):
    multiplayer.require_operator(request.user)
    game = get_object_or_404(Game, pk=game_id, kind="multiplayer")
    return private_response(JsonResponse(waiting_status(game)))


@require_http_methods(["GET", "POST"])
def invitation(request, token):
    invite = multiplayer.resolve_invitation(token)
    if request.method == "POST":
        from .guest_services import is_guest
        from .guest_views import guest_origin_for_handoff

        origin = guest_origin_for_handoff(request)
        account = (
            request.user
            if request.user.is_authenticated
            and not is_guest(request.user)
            and not hasattr(request.user, "shared_identity")
            else None
        )
        try:
            seat_user = multiplayer.claim_invitation(token, account=account)
        except RuleError as error:
            return private_response(
                render(
                    request,
                    "simulation/shared_invite.html",
                    {
                        "room": invite.game,
                        "error": localize(error.args[0]),
                    },
                    status=409,
                )
            )
        # A secret credential may authenticate its low-privilege seat, never the
        # registered account to which that seat is linked. Keep an already
        # authenticated registered account when it owns the same alias.
        keep_account = account is not None and seat_user.shared_identity.account_id == account.pk
        grants = request.session.get("shared_seat_access", {}).copy()
        if not keep_account:
            login(request, seat_user, backend="django.contrib.auth.backends.ModelBackend")
        grants[str(invite.game_id)] = invite.version
        request.session["shared_seat_access"] = grants
        if origin is not None:
            request.session["yaara_guest_origin"] = origin
        request.session.set_expiry(60 * 60 * 24 * 30)
        return private_response(redirect("shared_lobby", game_id=invite.game_id))
    return private_response(
        render(
            request,
            "simulation/shared_invite.html",
            {
                "room": invite.game,
                "house": localize(invite.game.state["players"][invite.actor]["name"]),
            },
        )
    )


def member_room(request, game_id):
    game = get_object_or_404(Game, pk=game_id, kind="multiplayer")
    multiplayer.check_seat_session(request, game)
    return game, services.membership(game, request.user)


@login_required
@require_GET
def lobby(request, game_id):
    game, actor = member_room(request, game_id)
    if game.lobby_status == "running":
        return private_response(redirect("game", game_id=game.pk))
    return private_response(
        render(
            request,
            "simulation/shared_lobby.html",
            {
                **room_context(game),
                "house": localize(game.state["players"][actor]["name"]),
            },
        )
    )


@login_required
@require_GET
def lobby_state(request, game_id):
    game, _actor = member_room(request, game_id)
    return private_response(JsonResponse(waiting_status(game)))
