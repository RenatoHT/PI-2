# Telas do painel inicial, da lista de vencimentos e da lista de estoque baixo

from datetime import timedelta

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone

from . import estoque_baixo, vencimentos


def painel(request: HttpRequest) -> HttpResponse:
    """Tela inicial com os números do dia e os atalhos."""
    contexto = {
        "resumo": vencimentos.resumir_vencimentos(hoje=timezone.localdate()),
        "dias_padrao": vencimentos.FILTRO_DIAS_PADRAO,
        "estoque_baixo": estoque_baixo.contar_produtos_abaixo_do_minimo(),
    }
    return render(request, "painel.html", contexto)


def listar_vencimentos(request: HttpRequest) -> HttpResponse:
    """Lista os lotes que vencem dentro do filtro ?dias= (3, 7, 15 ou 30)."""
    try:
        dias = vencimentos.interpretar_filtro_dias(request.GET.get("dias"))
    except ValueError as erro:
        return _responder_filtro_invalido(request, erro)
    hoje = timezone.localdate()
    contexto = {
        "dias": dias,
        "filtros": vencimentos.FILTROS_DIAS_VENCIMENTO,
        "limite": hoje + timedelta(days=dias),
        "lotes": vencimentos.lotes_a_vencer(hoje=hoje, dias=dias),
    }
    return render(request, "vencimentos.html", contexto)


def listar_estoque_baixo(request: HttpRequest) -> HttpResponse:
    """Lista os produtos com quantidade igual ou menor que o estoque mínimo."""
    contexto = {"produtos": estoque_baixo.produtos_abaixo_do_minimo()}
    return render(request, "estoque_baixo.html", contexto)


def _responder_filtro_invalido(request: HttpRequest, erro: ValueError) -> HttpResponse:
    # Filtro inválido na URL: mostra a tela com a mensagem de erro
    contexto = {
        "dias": None,
        "filtros": vencimentos.FILTROS_DIAS_VENCIMENTO,
        "lotes": [],
        "erro": str(erro),
    }
    return render(request, "vencimentos.html", contexto, status=400)
