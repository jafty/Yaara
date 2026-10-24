from functools import partial

from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

from simulation import guest_views, multiplayer_views, views

urlpatterns = [
    path("i18n/js/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path("i18n/", include("django.conf.urls.i18n")),
    path("health/", views.health, name="health"),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/signup/", views.signup, name="signup"),
    path("", views.home, name="home"),
    path("play/", guest_views.guest_start, name="guest_start"),
    path("play/resume/", guest_views.guest_restore, name="guest_restore"),
    path("save/", guest_views.guest_claim, name="guest_claim"),
    path("save/existing/", guest_views.guest_attach, name="guest_attach"),
    path("manage/", multiplayer_views.manage, name="multiplayer_manage"),
    path("manage/<uuid:game_id>/", multiplayer_views.operator_room, name="shared_operator_room"),
    path(
        "manage/<uuid:game_id>/state/",
        multiplayer_views.operator_state,
        name="shared_operator_state",
    ),
    path("join/<str:token>/", multiplayer_views.invitation, name="shared_invite"),
    path("games/<uuid:game_id>/lobby/", multiplayer_views.lobby, name="shared_lobby"),
    path(
        "games/<uuid:game_id>/lobby/state/",
        multiplayer_views.lobby_state,
        name="shared_lobby_state",
    ),
    path("games/new/", views.new_game, name="new_game"),
    path("games/<uuid:game_id>/", views.desk, name="game"),
    path("games/<uuid:game_id>/state/", views.state_view, name="state"),
    path("games/<uuid:game_id>/archive/", views.reign_archive, name="reign_archive"),
    path("games/<uuid:game_id>/orders/preview/", views.preview_order, name="preview"),
    path("games/<uuid:game_id>/orders/confirm/", views.confirm_order, name="confirm"),
    path("games/<uuid:game_id>/orders/<uuid:order_id>/cancel/", views.cancel_order, name="cancel"),
    path("games/<uuid:game_id>/advance/", views.advance, name="advance"),
    path("games/<uuid:game_id>/pause/", views.pause, name="pause"),
    path("games/<uuid:game_id>/start/", views.start, name="start"),
]
handler403 = partial(views.error_view, status=403)
handler404 = partial(views.error_view, status=404)
handler500 = partial(views.error_view, status=500)
