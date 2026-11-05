# Formulário de cadastro de usuário do mercado

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import PerfilDeAcesso


class FormularioNovoUsuario(UserCreationForm):
    """Usuário, senha (duas vezes) e se é administrador do mercado."""

    administrador = forms.BooleanField(
        required=False,
        label="Também é administrador do mercado",
        help_text="Administradores criam usuários e trocam a senha dos outros.",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)

    def save(self, commit: bool = True) -> User:
        usuario = super().save(commit=False)
        # Usuário do mercado não entra no /admin/ do Django
        usuario.is_staff = False
        usuario.is_superuser = False
        usuario.save()
        PerfilDeAcesso.objects.create(
            usuario=usuario, administrador=self.cleaned_data["administrador"]
        )
        return usuario
