from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as message


class SignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = ("username",)


class GameForm(forms.Form):
    title = forms.CharField(
        label=message("Nom de votre règne"),
        max_length=80,
        initial=message("Les chroniques de Yaara"),
    )
    player_name = forms.CharField(
        label=message("Votre maison"), max_length=60, initial=message("La maison d’Ambre")
    )
    version = forms.ChoiceField(
        label=message("Règles"),
        choices=[
            ("V1", message("V1 · sièges, croissance et annulation")),
            ("V0", message("V0 · règles essentielles")),
        ],
    )
    opponents = forms.ChoiceField(
        label=message("Vos rivaux"),
        choices=[
            ("active", message("Deux Prétendants contrôlés par l’ordinateur")),
            ("passive", message("Rivaux passifs · explorer les règles")),
        ],
    )
    reign_months = forms.TypedChoiceField(
        label=message("Durée du règne"),
        coerce=int,
        initial=120,
        choices=[
            (120, message("10 ans · 120 mois")),
            (60, message("5 ans · 60 mois")),
            (24, message("2 ans · 24 mois")),
            (240, message("20 ans · 240 mois")),
        ],
    )
    mode = forms.ChoiceField(
        label=message("Calendrier"),
        choices=[
            ("manual", message("Manuel · vous avancez chaque mois")),
            ("scheduled", message("Automatique · le monde avance à échéance")),
        ],
    )
    interval_minutes = forms.TypedChoiceField(
        label=message("Cadence du calendrier automatique"),
        coerce=int,
        initial=10,
        choices=[
            (10, message("Un mois toutes les 10 minutes")),
            (5, message("Un mois toutes les 5 minutes")),
        ],
    )
