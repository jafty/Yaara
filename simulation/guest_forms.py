"""Forms for preserving an already playable guest reign."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _


class GuestClaimForm(forms.Form):
    username = forms.CharField(label=_("Nom de compte"), max_length=150)
    password1 = forms.CharField(label=_("Mot de passe"), widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Confirmer le mot de passe"), widget=forms.PasswordInput)

    def clean(self):
        data = super().clean()
        if data.get("password1") != data.get("password2"):
            self.add_error("password2", _("Les deux mots de passe doivent être identiques."))
        return data


class GuestAttachForm(AuthenticationForm):
    pass
