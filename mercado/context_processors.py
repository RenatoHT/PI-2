# Deixa disponível nos templates se o usuário é administrador do mercado

from django.http import HttpRequest

from .autorizacao import eh_administrador


def papel_do_mercado(request: HttpRequest) -> dict[str, bool]:
    return {"administrador_do_mercado": eh_administrador(request.user)}
