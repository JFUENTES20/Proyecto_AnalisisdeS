from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegistroForm(UserCreationForm):
    first_name = forms.CharField(label="Nombres", max_length=150)
    last_name = forms.CharField(label="Apellidos", max_length=150)
    email = forms.EmailField(label="Correo electrónico")

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo.")
        return email


class ContactoForm(forms.Form):
    telefono = forms.CharField(
        label="Teléfono de contacto", max_length=30,
        help_text="Ejemplos: 5123 4567 o +502 5123 4567. Se guardará como +50251234567.",
        widget=forms.TextInput(attrs={"type": "tel", "inputmode": "tel", "autocomplete": "tel"}),
    )
    version = forms.CharField(widget=forms.HiddenInput)
    confirmar_cambio = forms.BooleanField(
        required=False,
        label="Confirmo que el teléfono que ingreso es correcto; el dato histórico permanecerá conservado.",
    )

    def clean_telefono(self):
        from .contacto import normalizar_telefono
        return normalizar_telefono(self.cleaned_data["telefono"])
