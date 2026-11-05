# Regras de vencimento dos lotes, usadas pelo painel e pela tela de vencimentos.
# Recebem a data de hoje por parâmetro para facilitar os testes.

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import QuerySet

from .models import Product, ProductBatch

# Opções do filtro de dias na tela de vencimentos
FILTROS_DIAS_VENCIMENTO: tuple[int, ...] = (3, 7, 15, 30)
FILTRO_DIAS_PADRAO: int = 7


def interpretar_filtro_dias(valor_bruto: str | None) -> int:
    """Lê o ?dias= da URL. Vazio vira 7; valor fora da lista dá erro."""
    if not valor_bruto:
        return FILTRO_DIAS_PADRAO
    if not valor_bruto.isdigit():
        raise _erro_filtro_invalido(valor_bruto)
    dias = int(valor_bruto)
    if dias not in FILTROS_DIAS_VENCIMENTO:
        raise _erro_filtro_invalido(valor_bruto)
    return dias


def _erro_filtro_invalido(valor_bruto: str) -> ValueError:
    return ValueError(
        f"Filtro de dias inválido: {valor_bruto!r}. "
        f"Esperado um número inteiro entre {FILTROS_DIAS_VENCIMENTO}."
    )


def dias_restantes(hoje: date, validade: date) -> int:
    """Dias até a validade (negativo se já venceu)."""
    return (validade - hoje).days


def descrever_situacao(dias: int) -> str:
    """Texto que aparece na tela: Vencido, Vence hoje, Vence amanhã..."""
    if dias < 0:
        return "Vencido"
    if dias == 0:
        return "Vence hoje"
    if dias == 1:
        return "Vence amanhã"
    return f"Vence em {dias} dias"


@dataclass(frozen=True)
class LoteVencendo:
    """Uma linha da tela de vencimentos."""

    produto: str
    marca: str
    codigo_barras: str
    numero_lote: str
    validade: date
    quantidade: int
    dias_restantes: int
    situacao: str
    vencido: bool


def lotes_a_vencer(hoje: date, dias: int) -> list[LoteVencendo]:
    """Lotes com estoque que vencem até hoje + dias (inclui os já vencidos)."""
    limite = hoje + timedelta(days=dias)
    lotes = _lotes_com_estoque_e_validade().filter(expiration_date__lte=limite)
    return [_montar_linha(hoje, lote) for lote in lotes]


def _lotes_com_estoque_e_validade() -> QuerySet[ProductBatch]:
    return (
        ProductBatch.objects.select_related("product")
        .filter(quantity__gt=0, expiration_date__isnull=False)
        .order_by("expiration_date", "product__name", "id")
    )


def _montar_linha(hoje: date, lote: ProductBatch) -> LoteVencendo:
    assert lote.expiration_date is not None
    dias = dias_restantes(hoje, lote.expiration_date)
    return LoteVencendo(
        produto=lote.product.name,
        marca=lote.product.brand,
        codigo_barras=lote.product.barcode,
        numero_lote=lote.batch_number,
        validade=lote.expiration_date,
        quantidade=lote.quantity,
        dias_restantes=dias,
        situacao=descrever_situacao(dias),
        vencido=dias < 0,
    )


@dataclass(frozen=True)
class ResumoVencimentos:
    """Números do painel inicial."""

    total_produtos: int
    lotes_vencidos: int
    lotes_proximos: int


def resumir_vencimentos(hoje: date) -> ResumoVencimentos:
    """Conta produtos, lotes vencidos e lotes que vencem nos próximos 7 dias."""
    lotes = _lotes_com_estoque_e_validade()
    limite = hoje + timedelta(days=FILTRO_DIAS_PADRAO)
    return ResumoVencimentos(
        total_produtos=Product.objects.count(),
        lotes_vencidos=lotes.filter(expiration_date__lt=hoje).count(),
        lotes_proximos=lotes.filter(expiration_date__range=(hoje, limite)).count(),
    )
