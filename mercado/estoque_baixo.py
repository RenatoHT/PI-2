# Regra de estoque baixo, usada pelo painel e pela tela de estoque baixo.
# Mesma regra da API (/mercado/api/estoque/): quantidade total <= estoque mínimo.

from __future__ import annotations

from django.db.models import F, QuerySet, Sum, Value
from django.db.models.functions import Coalesce

from .models import Product


def produtos_abaixo_do_minimo() -> QuerySet[Product]:
    """Produtos com quantidade total (soma dos lotes) igual ou menor que o mínimo.

    Os sem estoque aparecem primeiro; depois, os de menor quantidade.
    """
    return (
        Product.objects.annotate(
            total_quantity=Coalesce(Sum("batches__quantity"), Value(0)),
        )
        .filter(total_quantity__lte=F("min_quantity"))
        .order_by("total_quantity", "name")
    )


def contar_produtos_abaixo_do_minimo() -> int:
    return produtos_abaixo_do_minimo().count()
