# Quem pode usar o painel e quem é administrador do mercado.
# O usuário do /admin/ do Django não tem perfil e por isso não usa o painel.

from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse

from .models import PerfilDeAcesso


def perfil_do_mercado(
    usuario: AbstractBaseUser | AnonymousUser,
) -> PerfilDeAcesso | None:
    """Perfil do usuário, ou None se ele não tem."""
    return getattr(usuario, "perfil_mercado", None)


def tem_acesso_ao_painel(usuario: AbstractBaseUser | AnonymousUser) -> bool:
    return perfil_do_mercado(usuario) is not None


def eh_administrador(usuario: AbstractBaseUser | AnonymousUser) -> bool:
    perfil = perfil_do_mercado(usuario)
    return perfil is not None and perfil.administrador


def exigir_administrador(
    view: Callable[..., HttpResponse],
) -> Callable[..., HttpResponse]:
    """Decorator: só administrador do mercado entra na view, senão 403."""

    @wraps(view)
    def protegida(
        request: HttpRequest, *args: object, **kwargs: object
    ) -> HttpResponse:
        if not eh_administrador(request.user):
            raise PermissionDenied(
                "Apenas administradores do mercado gerenciam usuários."
            )
        return view(request, *args, **kwargs)

    return protegida
