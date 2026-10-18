from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import Product, ProductBatch, Sale, SaleItems, CashMovement
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce
from django.db import transaction
from datetime import datetime
from decimal import Decimal
import requests
import json

#página de venda
def scan(request):
    return render(request, "scan.html")

#conulta de estoque
def product_lookup(request, barcode):
    try:
        product = Product.objects.get(barcode=barcode)

        return JsonResponse({
            "found": True,
            "barcode": product.barcode,
            "name": product.name,
            "price": float(product.price),
            "quantity": product.quantity,
        })

    except Product.DoesNotExist:
        return JsonResponse({
            "found": False,
            "barcode": barcode,
        })

# Exclui um produto do estoque.
def product_delete(request, barcode):

    if request.method != "POST":
        return redirect("estoque")

    product = get_object_or_404(Product, barcode=barcode)

    if product.quantity > 0:
        return render(
            request,
            "stock.html",
            {
                "products": Product.objects.annotate(
                    total_quantity=Coalesce(
                        Sum("batches__quantity"),
                        Value(0),
                    )
                ).order_by("name"),
                "error": (
                    f'Não é possível excluir "{product.name}", '
                    "pois ainda existem unidades em estoque."
                ),
            },
        )

    product.delete()

    return redirect("estoque")

class SaleError(Exception):
    def __init__(self, message, status=400):
        self.message = message
        self.status = status
        super().__init__(message)


# Finalização da venda, com baixa de estoque por lote e registro de venda
def finish_sale(request):

    if request.method != "POST":
        return JsonResponse({
            "error": "Método não permitido."
        }, status=405)

    try:
        data = json.loads(request.body)
        products = data.get("products", [])

        if not products:
            return JsonResponse({
                "error": "Nenhum produto informado para a venda."
            }, status=400)

        with transaction.atomic():

            # Cria o registro da venda.
            sale = Sale.objects.create()
            total = Decimal("0.00")

            for item in products:

                barcode = item.get("barcode")
                quantity = item.get("quantity")

                if not barcode or not isinstance(quantity, int) or isinstance(quantity, bool) or quantity <= 0:
                    raise SaleError("Produto ou quantidade inválida.")

                product = Product.objects.filter(
                    barcode=barcode
                ).first()

                if product is None:
                    raise SaleError(
                        f"Produto com código {barcode} não encontrado.",
                        status=404
                    )

                # Bloqueia os lotes deste produto durante a operação.
                batches = list(
                    ProductBatch.objects.select_for_update()
                    .filter(product=product, quantity__gt=0)
                    .order_by("id")
                )

                # Primeiro: lotes sem identificação e sem validade.
                # Depois: lotes com validade, do vencimento mais próximo para o mais distante.
                batches.sort(
                    key=lambda batch: (
                        0 if not batch.batch_number and not batch.expiration_date else
                        1 if batch.expiration_date is not None else
                        2,
                        batch.expiration_date or datetime.max.date(),
                        batch.id,
                    )
                )

                # Não permite utilizar lotes vencidos.
                today = datetime.now().date()

                available_quantity = sum(
                    batch.quantity
                    for batch in batches
                    if (
                        batch.expiration_date is None
                        or batch.expiration_date >= today
                    )
                )

                if available_quantity < quantity:
                    raise SaleError(
                        f"Estoque disponível insuficiente para "
                        f"{product.name}."
                    )


                # Registra o item vendido.
                SaleItems.objects.create(
                    sale=sale,
                    product=product,
                    quantity_sold=quantity,
                    unit_price=product.price
                )
                
                total += product.price * quantity
                
                remaining = quantity

                # Baixa o estoque dos lotes na ordem definida.
                for batch in batches:

                    if batch.expiration_date is not None and batch.expiration_date < today:
                        continue

                    if remaining <= 0:
                        break

                    # Retira do lote a menor quantidade entre necessário e o disponível.
                    deducted = min(batch.quantity, remaining)

                    batch.quantity -= deducted
                    batch.save(update_fields=["quantity"])

                    remaining -= deducted

            # Salva o total da venda.
            sale.total_amount = total
            sale.save(update_fields=["total_amount"])

            # Registra a entrada no caixa.
            CashMovement.objects.create(
                type=CashMovement.IN,
                amount=total,
                description=f"Venda {sale.id}",
                sale=sale
            )

        return JsonResponse({
            "success": True,
            "sale_id": sale.id,
            "total_amount": str(total)
        }, status=201)

    except SaleError as exc:
        # A exceção foi lançada dentro do atomic.
        # Ao sair dele, o Django executa o rollback.
        return JsonResponse({
            "error": exc.message
        }, status=exc.status)


# Página de estoque
def stock(request):
    products = Product.objects.annotate(
        total_quantity=Coalesce(
            Sum("batches__quantity"),
            Value(0)
        )
    ).order_by("name")

    return render(
        request,
        "stock.html",
        {"products": products}
    )

#Cadastro de produto e primeiro lote
def product_create(request):
    if request.method == "POST":
        barcode = request.POST.get("barcode", "").strip()
        name = request.POST.get("name", "").strip()
        brand = request.POST.get("brand", "").strip()
        price = request.POST.get("price")

        batch_number = request.POST.get("batch_number", "").strip()
        
        expiration_date_text = request.POST.get("expiration_date", "").strip()
        if expiration_date_text:
            try:
                expiration_date = datetime.strptime(
                    expiration_date_text, "%d/%m/%Y"
                ).date()
            except ValueError:
                return render(
                    request,
                    "product_form.html",
                    {
                        "error": "Data de validade inválida. "
                                "Digite uma data válida no formato DD/MM/AAAA."
                    }
                )
        else:
            expiration_date = None

        quantity = int(request.POST.get("quantity"))
        purchase_price_text = request.POST.get(
            "purchase_price", ""
        ).strip().replace(",", ".")

        purchase_price = Decimal(purchase_price_text)

        try:
            with transaction.atomic():
                product = Product.objects.create(
                    barcode=barcode,
                    name=name,
                    brand=brand,
                    price=price,
                )


                lote = ProductBatch.objects.create(
                    product=product,
                    batch_number=batch_number,
                    expiration_date=expiration_date,
                    quantity=quantity,
                    purchase_price=purchase_price,
                )

                
                total = Decimal(lote.quantity) * lote.purchase_price

                CashMovement.objects.create(
                    type=CashMovement.OUT,
                    amount=total,
                    description=f"Compra de lote {lote.batch_number} - {product.name}",
                )

            return render(
                request,
                "product_form.html",
                {"success": "Produto cadastrado com sucesso."}
            )

        except Exception as e:
            return render(
                request,
                "product_form.html",
                {
                    "error": "Não foi possível cadastrar o produto. "
                             "Verifique os dados informados."
                }
            )

    return render(request, "product_form.html")

#Altera produto já cadastrado
def product_edit(request, barcode):
    product = get_object_or_404(Product, barcode=barcode)

    if request.method == "POST":
        action = request.POST.get("action", "save")

        try:
            with transaction.atomic():
                if action == "add_batch":
                    batch_number = request.POST.get(
                        "new_batch_number", ""
                    ).strip()

                    expiration_date_text = request.POST.get(
                        "new_expiration_date", ""
                    ).strip()

                    quantity = int(request.POST.get(
                        "new_quantity", ""
                    ).strip())

                    purchase_price_text = request.POST.get(
                        "new_purchase_price", ""
                    ).strip().replace(",", ".")

                    purchase_price = Decimal(purchase_price_text)

                    if expiration_date_text:
                        expiration_date = datetime.strptime(
                            expiration_date_text, "%d/%m/%Y"
                        ).date()
                    else:
                        expiration_date = None

                    lote = ProductBatch.objects.create(
                        product=product,
                        batch_number=batch_number,
                        expiration_date=expiration_date,
                        quantity=quantity,
                        purchase_price=purchase_price,
                    )

                    
                    total = Decimal(lote.quantity) * lote.purchase_price

                    CashMovement.objects.create(
                        type=CashMovement.OUT,
                        amount=total,
                        description=(
                            f"Compra de lote {lote.batch_number} - {product.name}"
                        ),
                    )
                elif action == "save":
                    product.name = request.POST.get(
                        "name", ""
                    ).strip()

                    product.brand = request.POST.get(
                        "brand", ""
                    ).strip()

                    product.price = request.POST.get("price", "").strip()
                    product.save()

                    batches = product.batches.all()

                    for batch in batches:
                        batch_number = request.POST.get(
                            f"batch_number_{batch.id}", ""
                        ).strip()

                        expiration_date_text = request.POST.get(
                            f"expiration_date_{batch.id}", ""
                        ).strip()

                        quantity = request.POST.get(
                            f"quantity_{batch.id}", ""
                        ).strip()

                        purchase_price = request.POST.get(
                            f"purchase_price_{batch.id}", ""
                        ).strip()

                        if expiration_date_text:
                            expiration_date = datetime.strptime(
                                expiration_date_text, "%d/%m/%Y"
                            ).date()
                        else:
                            expiration_date = None

                        batch.batch_number = batch_number
                        batch.expiration_date = expiration_date
                        batch.quantity = quantity
                        batch.purchase_price = purchase_price
                        batch.save()

                else:
                    return render(
                        request,
                        "product_edit.html",
                        {
                            "product": product,
                            "batches": product.batches.all(),
                            "error": "Operação inválida.",
                        },
                    )

            return redirect(
                "product_edit",
                barcode=product.barcode,
            )

        except (ValueError, TypeError):
            return render(
                request,
                "product_edit.html",
                {
                    "product": product,
                    "batches": product.batches.all(),
                    "error": (
                        "Não foi possível salvar. Confira os campos "
                        "e utilize DD/MM/AAAA nas datas de validade."
                    ),
                },
            )

    return render(
        request,
        "product_edit.html",
        {
            "product": product,
            "batches": product.batches.all().order_by("id"),
        },
    )

#Consulta API Open Food Facts
def lookup_product(request, barcode):
    url = f"https://world.openfoodfacts.org/api/v3/product/{barcode}"

    headers = {
        "User-Agent": "MeuScanner/1.0"
    }

    response = requests.get(url, headers=headers)
    data = response.json()

    product = data.get("product", {})

    return JsonResponse({
        "barcode": barcode,
        "name": product.get("product_name", ""),
        "brand": product.get("brands", ""),
        "category": product.get("categories", ""),
    })