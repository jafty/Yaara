"""Native consent/preferences pages for ordinary accounts and passwordless players."""

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import get_language, gettext_lazy
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from . import multiplayer, notifications, services
from .models import EmailSubscription, Game
from .multiplayer_views import private_response
from .presentation import localize
from .rules import RuleError


class EmailPreferencesForm(forms.Form):
    email = forms.EmailField(
        label=gettext_lazy("Votre adresse e-mail (facultatif)"),
        required=False,
        max_length=254,
        help_text=gettext_lazy(
            "Sans inscription. Votre adresse reste privée ; un lien permet de se désabonner."
        ),
    )
    start = forms.BooleanField(label=gettext_lazy("Départ du règne"), required=False, initial=True)
    capture = forms.BooleanField(
        label=gettext_lazy("Conquêtes et résultats de capture"), required=False, initial=True
    )
    yearly = forms.BooleanField(
        label=gettext_lazy("Bilan annuel et récoltes"), required=False, initial=True
    )
    raid = forms.BooleanField(
        label=gettext_lazy("Résumé des raids : au plus un e-mail par 24 heures"), required=False
    )


@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def preferences(request, game_id):
    rows = Game.objects.select_for_update() if request.method == "POST" else Game.objects.all()
    game = get_object_or_404(rows, pk=game_id)
    multiplayer.check_seat_session(request, game)
    actor = services.membership(game, request.user)
    member = game.memberships.get(actor=actor)
    sub = EmailSubscription.objects.filter(participant=member).first()
    form = EmailPreferencesForm(
        request.POST or None,
        initial={key: getattr(sub, key) for key in ("email", *notifications.PREFERENCES)}
        if sub
        else None,
    )
    if request.method == "POST" and form.is_valid():
        try:
            notifications.configure(
                request.user, game.pk, language=get_language(), **form.cleaned_data
            )
        except RuleError as error:
            form.add_error(None, localize(error.args[0]))
        else:
            messages.success(
                request,
                _(
                    "Préférences enregistrées. Si nécessaire, confirmez votre adresse depuis l’e-mail reçu."
                ),
            )
            return redirect("email_settings", game_id=game.pk)
    return_url = None
    if game.kind == "multiplayer":
        invite = game.invitations.get(actor=actor)
        if not invite.revoked:
            return_url = request.build_absolute_uri(
                reverse("shared_invite", args=[multiplayer.invitation_token(invite)])
            )
    return private_response(
        render(
            request,
            "simulation/email_preferences.html",
            {
                "room": game,
                "form": form,
                "subscription": sub,
                "mail_enabled": settings.EMAIL_NOTIFICATIONS_ENABLED,
                "return_url": return_url,
            },
        )
    )


@require_http_methods(["GET", "POST"])
def email_action(request, action, token):
    if action not in ("confirm", "unsubscribe"):
        raise Http404
    notifications.resolve_token(token)
    done = False
    if request.method == "POST":
        if action == "confirm":
            notifications.confirm_address(token)
        else:
            notifications.unsubscribe(token)
        done = True
    return private_response(
        render(request, "simulation/email_action.html", {"action": action, "done": done})
    )
