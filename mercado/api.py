import json
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Sum, Q
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse

from .models import Product, Sale, SaleItems, CashMovement


def product_to_dict(p):
    """Serializa um Product para JSON. Centralizado para resposta ser sempre igual em qualquer endpoint"""
    return {
        "name": p.name,
        "barcode": p.barcode,
        "quantity": p.quantity,
        "price": str(p.price),
        "min_quantity": p.min_quantity,
        "low_stock": p.quantity <= p.min_quantity,
    }


def json_body(request):
    """Lê o body JSON com erro amigável em vez de estourar 500"""
    try:
        return json.loads(request.body or b"{}"), None
    except json.JSONDecodeError:
        return None, JsonResponse({"error": "JSON inválido"}, status=400)


def parse_decimal(value):
    """Converte string/float para Decimal seguro para campo monetário"""
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


# ---------------- produtos ------------------------------

@require_http_methods(["GET", "POST"])
def products(request):
    if request.method == "GET":
        items = [product_to_dict(p) for p in Product.objects.all().order_by("name")]
        return JsonResponse({"products": items})

    data, error_response = json_body(request)
    if error_response:
        return error_response

    barcode = (data.get("barcode") or "").strip()
    name = (data.get("name") or "").strip()
    price = parse_decimal(data.get("price", 0))

    if not barcode or not name:
        return JsonResponse({"error": "Campos obrigatórios: barcode, name"}, status=400)
    if price is None or price < 0:
        return JsonResponse({"error": "Preço inválido"}, status=400)

    product, created = Product.objects.update_or_create(
        barcode=barcode,
        defaults={
            "name": name,
            "price": price,
            "quantity": data.get("quantity", 0),
            "min_quantity": data.get("min_quantity", 0),
        },
    )

    return JsonResponse(
        {"created": created, "product": product_to_dict(product)},
        status=201 if created else 200,
    )


@require_http_methods(["GET"])
def product_detail(request, barcode):
    try:
        product = Product.objects.get(barcode=barcode)
    except Product.DoesNotExist:
        return JsonResponse({"found": False, "barcode": barcode}, status=404)
    return JsonResponse({"found": True, "product": product_to_dict(product)})


# ---------------- estoque ----------------------------------

@require_http_methods(["GET"])
def stock_list(request):
    items = [product_to_dict(p) for p in Product.objects.all().order_by("name")]
    low = [i for i in items if i["low_stock"]]
    return JsonResponse({"products": items, "low_stock": low})


@require_http_methods(["POST"])
def stock_adjust(request, barcode):
    """Ajuste manual de estoque: {"delta": 5} repoe ou {"delta": -3} tira
    Delta evita a condição de corrida de ler-modificar-gravar, que poderia causar inconsistência em estoque
    """
    data, error_response = json_body(request)
    if error_response:
        return error_response

    try:
        delta = int(data.get("delta"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Delta inválido"}, status=400)

    try:
        product = Product.objects.get(barcode=barcode)
    except Product.DoesNotExist:
        return JsonResponse({"error": "Produto não encontrado"}, status=404)

    if product.quantity + delta < 0:
        return JsonResponse({"error": "Estoque não pode ficar negativo"}, status=400)

    product.quantity += delta
    product.save(update_fields=["quantity"])
    return JsonResponse({"product": product_to_dict(product)})


# ---------------- vendas ----------------------------------

@require_http_methods(["GET", "POST"])
def sales(request):
    if request.method == "GET":
        result = [
            {
                "id": sale.id,
                "sale_date": sale.sale_date.isoformat(),
                "total_amount": float(sale.total_amount),
                "items_count": sale.items.count(),
            }
            for sale in Sale.objects.all().order_by("-sale_date")[:100]
        ]
        return JsonResponse({"sales": result})

    data, error_response = json_body(request)
    if error_response:
        return error_response

    items = data.get("products")
    if not isinstance(items, list) or not items:
        return JsonResponse({"error": "Lista de produtos inválida ou vazia"}, status=400)

    try:
        with transaction.atomic():
            sale = Sale.objects.create()
            total = Decimal("0")

            for item in items:
                product = Product.objects.select_for_update().get(barcode=item["barcode"])
                quantity = int(item["quantity"])
                if quantity <= 0:
                    raise ValueError(f"Quantidade inválida para o produto {product.name}")
                if product.quantity < quantity:
                    raise ValueError(f"Estoque insuficiente para o produto {product.name}")

                product.quantity -= quantity
                product.save(update_fields=["quantity"])

                SaleItems.objects.create(
                    sale=sale,
                    product=product,
                    quantity_sold=quantity,
                    unit_price=product.price,
                )
                total += product.price * quantity

            sale.total_amount = total
            sale.save(update_fields=["total_amount"])

            CashMovement.objects.create(
                type=CashMovement.IN,
                amount=total,
                description=f"Venda {sale.id}",
                sale=sale,
            )

    except Product.DoesNotExist:
        return JsonResponse({"error": "Produto não encontrado"}, status=404)
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse(
        {
            "sale_id": sale.id,
            "total_amount": float(total),
        },
        status=201,
    )


@require_http_methods(["GET"])
def sale_detail(request, sale_id):
    try:
        sale = Sale.objects.get(id=sale_id)
    except Sale.DoesNotExist:
        return JsonResponse({"error": "Venda não encontrada"}, status=404)

    return JsonResponse(
        {
            "id": sale.id,
            "sale_date": sale.sale_date.isoformat(),
            "total_amount": float(sale.total_amount),
            "items": [
                {
                    "barcode": item.product.barcode,
                    "name": item.product.name,
                    "quantity_sold": item.quantity_sold,
                    "unit_price": float(item.unit_price),
                }
                for item in sale.items.all()
            ],
        }
    )


# ---------------- caixa ----------------------------------

@require_http_methods(["GET", "POST"])
def cash_movements(request):
    if request.method == "GET":
        result = [
            {
                "id": cm.id,
                "type": cm.type,
                "amount": float(cm.amount),
                "description": cm.description,
                "created_at": cm.created_at.isoformat(),
                "sale_id": cm.sale.id if cm.sale else None,
            }
            for cm in CashMovement.objects.all().order_by("-created_at")[:200]
        ]
        return JsonResponse({"cash_movements": result})

    data, error_response = json_body(request)
    if error_response:
        return error_response

    amount = parse_decimal(data.get("amount"))
    if amount is None or amount <= 0:
        return JsonResponse({"error": "Valor inválido"}, status=400)
    if data.get("type") not in [CashMovement.IN, CashMovement.OUT]:
        return JsonResponse({"error": "Tipo inválido, deve ser IN ou OUT"}, status=400)

    movement = CashMovement.objects.create(
        type=data["type"],
        amount=amount,
        description=(data.get("description") or "").strip(),
    )
    return JsonResponse(
        {
            "id": movement.id,
        },
        status=201,
    )


@require_http_methods(["GET"])
def cash_balance(request):
    """Saldo atual = entradas - saídas, numa query só"""
    totals = CashMovement.objects.aggregate(
        entrada=Sum("amount", filter=Q(type=CashMovement.IN)),
        saida=Sum("amount", filter=Q(type=CashMovement.OUT)),
    )
    balance = (totals["entrada"] or 0) - (totals["saida"] or 0)
    return JsonResponse(
        {
            "balance": float(balance),
        }
    )