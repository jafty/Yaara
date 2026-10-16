from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _


class SignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = ("username",)


class GameForm(forms.Form):
    title = forms.CharField(
        label=_("Nom de votre règne"), max_length=80, initial=_("Les chroniques de Yaara")
    )
    player_name = forms.CharField(
        label=_("Votre maison"), max_length=60, initial=_("La maison d’Ambre")
    )
    version = forms.ChoiceField(
        label=_("Règles"),
        choices=[
            ("V1", _("V1 · sièges, croissance et annulation")),
            ("V0", _("V0 · règles essentielles")),
        ],
    )
    opponents = forms.ChoiceField(
        label=_("Vos rivaux"),
        choices=[
            ("active", _("Deux Prétendants contrôlés par l’ordinateur")),
            ("passive", _("Rivaux passifs · explorer les règles")),
        ],
    )
    reign_months = forms.TypedChoiceField(
        label=_("Durée du règne"),
        coerce=int,
        initial=120,
        choices=[
            (120, _("10 ans · 120 mois")),
            (60, _("5 ans · 60 mois")),
            (24, _("2 ans · 24 mois")),
            (240, _("20 ans · 240 mois")),
        ],
    )
    mode = forms.ChoiceField(
        label=_("Calendrier"),
        choices=[
            ("manual", _("Manuel · vous avancez chaque mois")),
            ("scheduled", _("Automatique · le monde avance à échéance")),
        ],
    )
    interval_minutes = forms.TypedChoiceField(
        label=_("Cadence du calendrier automatique"),
        coerce=int,
        initial=10,
        choices=[(10, _("Un mois toutes les 10 minutes")), (5, _("Un mois toutes les 5 minutes"))],
    )
