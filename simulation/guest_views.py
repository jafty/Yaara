"""Public recruitment entry and explicit guest-account handoff."""

import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .guest_forms import GuestAttachForm, GuestClaimForm
from .guest_models import GuestIdentity
from .guest_services import (
    _private_solo,
    attach_guest_to_user,
    claim_guest_new,
    guest_identity,
    start_guest,
    touch_guest,
)
from .rules import RuleError


def _safe_next(request, default):
    target = request.POST.get("next", request.GET.get("next", ""))
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return default


@require_GET
def landing(request):
    if request.user.is_authenticated:
        identity = guest_identity(request.user)
        return redirect("game", game_id=identity.game_id) if identity else redirect("home")
    if "guest_start_key" not in request.session:
        request.session["guest_start_key"] = str(uuid.uuid4())
    return render(
        request,
        "simulation/guest_entry.html",
        {
            "start_key": request.session["guest_start_key"],
            "guest_enabled": settings.GUEST_PLAY_ENABLED,
            "retention_days": settings.GUEST_RETENTION_DAYS,
        },
    )


@require_POST
def guest_start(request):
    if request.user.is_authenticated:
        identity = guest_identity(request.user)
        return redirect("game", game_id=identity.game_id) if identity else redirect("home")
    key = request.POST.get("start_key", "")
    expected = request.session.get("guest_start_key", "")
    if not key or not expected or not constant_time_compare(key, expected):
        raise PermissionDenied(
            _("Autorisez les cookies de ce site, puis revenez à l’accueil pour commencer.")
        )
    try:
        uuid.UUID(key)
    except ValueError as error:
        raise PermissionDenied from error
    try:
        identity = start_guest(key, request.META.get("REMOTE_ADDR", "unknown"))
    except RuleError as error:
        return HttpResponse(str(error), status=429, headers={"Retry-After": "3600"})
    login(request, identity.user, backend="django.contrib.auth.backends.ModelBackend")
    request.session.set_expiry(settings.GUEST_RETENTION_DAYS * 86400)
    return redirect("game", game_id=identity.game_id)


@login_required
@require_http_methods(["GET", "POST"])
def guest_claim(request):
    identity = guest_identity(request.user)
    if identity is None:
        return redirect("home")
    if not settings.SIGNUP_ENABLED:
        raise PermissionDenied(_("La création de comptes est actuellement fermée."))
    form = GuestClaimForm(request.POST or None)
    target = _safe_next(request, reverse("game", args=[identity.game_id]))
    if request.method == "POST" and form.is_valid():
        try:
            user = claim_guest_new(
                request.user, form.cleaned_data["username"], form.cleaned_data["password1"]
            )
        except RuleError as error:
            form.add_error(None, str(error))
        else:
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            request.session.pop("guest_start_key", None)
            request.session.set_expiry(None)
            return redirect(target)
    return render(
        request,
        "simulation/guest_claim.html",
        {
            "form": form,
            "next": target,
            "guest_game_id": identity.game_id,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def guest_attach(request):
    identity = guest_identity(request.user)
    if identity is None:
        return redirect("home")
    form = GuestAttachForm(request, data=request.POST or None)
    target = _safe_next(request, reverse("game", args=[identity.game_id]))
    if request.method == "POST" and form.is_valid():
        destination = form.get_user()
        try:
            attach_guest_to_user(request.user, destination)
        except RuleError as error:
            form.add_error(None, str(error))
        except PermissionDenied:
            form.add_error(None, _("Ce règne ne peut pas être rattaché à ce compte."))
        else:
            login(request, destination, backend="django.contrib.auth.backends.ModelBackend")
            request.session.pop("guest_start_key", None)
            request.session.set_expiry(None)
            return redirect(target)
    return render(
        request,
        "simulation/guest_attach.html",
        {
            "form": form,
            "next": target,
            "guest_game_id": identity.game_id,
        },
    )


def guest_origin_for_handoff(request):
    """Capture only a server-proven guest origin before a passwordless seat logs in."""
    identity = guest_identity(request.user)
    if identity:
        return identity.user_id
    if request.user.is_authenticated:
        return request.session.get("yaara_guest_origin")
    return None


@login_required
@require_POST
def guest_restore(request):
    origin = request.session.get("yaara_guest_origin")
    identity = (
        GuestIdentity.objects.select_related("user")
        .filter(user_id=origin, claimed_at__isnull=True, user__is_active=True)
        .first()
    )
    if not origin or identity is None:
        raise PermissionDenied(_("Cet essai solo n’est pas accessible depuis cette session."))
    touch_guest(identity.user)
    if not _private_solo(identity):
        raise PermissionDenied(_("Cet essai solo n’est pas accessible depuis cette session."))
    login(request, identity.user, backend="django.contrib.auth.backends.ModelBackend")
    request.session.set_expiry(settings.GUEST_RETENTION_DAYS * 86400)
    return redirect("game", game_id=identity.game_id)


def guest_access(request):
    identity = guest_identity(request.user)
    origin = request.session.get("yaara_guest_origin") if request.user.is_authenticated else None
    return {
        "guest_access": {
            "is_guest": identity is not None,
            "game_id": identity.game_id if identity else None,
            "retention_days": settings.GUEST_RETENTION_DAYS,
            "can_restore": bool(
                origin
                and GuestIdentity.objects.filter(
                    user_id=origin,
                    claimed_at__isnull=True,
                    user__is_active=True,
                    expires_at__gt=timezone.now(),
                ).exists()
            ),
        }
    }


class GuestActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)
        try:
            identity = touch_guest(request.user)
        except PermissionDenied:
            logout(request)
            messages.info(
                request, _("Votre accès invité a expiré. Vous pouvez commencer un nouveau règne.")
            )
            return redirect("home")
        if identity and getattr(identity, "renew_session", False):
            request.session.set_expiry(settings.GUEST_RETENTION_DAYS * 86400)
        return self.get_response(request)
