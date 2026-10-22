from functools import partial

from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

from simulation import views

urlpatterns = [
    path("i18n/js/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path("i18n/", include("django.conf.urls.i18n")),
    path("health/", views.health, name="health"),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/signup/", views.signup, name="signup"),
    path("", views.home, name="home"),
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
