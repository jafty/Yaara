from django import forms
from django.contrib.auth.forms import UserCreationForm


class SignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        fields = ("username",)


class GameForm(forms.Form):
    title = forms.CharField(
        label="Nom de votre règne", max_length=80, initial="Les chroniques de Yaara"
    )
    player_name = forms.CharField(label="Votre maison", max_length=60, initial="La maison d’Ambre")
    version = forms.ChoiceField(
        label="Règles",
        choices=[
            ("V1", "V1 · sièges, croissance et annulation"),
            ("V0", "V0 · règles essentielles"),
        ],
    )
    opponents = forms.ChoiceField(
        label="Vos rivaux",
        choices=[
            ("active", "Deux Prétendants contrôlés par l’ordinateur"),
            ("passive", "Rivaux passifs · explorer les règles"),
        ],
    )
    reign_months = forms.TypedChoiceField(
        label="Durée du règne",
        coerce=int,
        initial=120,
        choices=[
            (120, "10 ans · 120 mois"),
            (60, "5 ans · 60 mois"),
            (24, "2 ans · 24 mois"),
            (240, "20 ans · 240 mois"),
        ],
    )
    mode = forms.ChoiceField(
        label="Calendrier",
        choices=[
            ("manual", "Manuel · vous avancez chaque mois"),
            ("scheduled", "Automatique · le monde avance à échéance"),
        ],
    )
    interval_minutes = forms.TypedChoiceField(
        label="Cadence du calendrier automatique",
        coerce=int,
        initial=10,
        choices=[(10, "Un mois toutes les 10 minutes"), (5, "Un mois toutes les 5 minutes")],
    )
