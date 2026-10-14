from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
import requests
from .models import Product, ProductBatch
from django.db.models import Sum, Value
from django.db.models.functions import Coalesce
from django.db import transaction
import json
from datetime import datetime

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

#Finalização de venda, subtração de produtos do estoque
def finish_sale(request):

    if request.method != "POST":
        return JsonResponse({
            "error": "Método não permitido."
        }, status=405)

    data = json.loads(request.body)

    for item in data["products"]:

        product = Product.objects.get(
            barcode=item["barcode"]
        )

        quantity = item["quantity"]

        if product.quantity < quantity:
            return JsonResponse({
                "error": f"Estoque insuficiente para {product.name}."
            }, status=400)

        product.quantity -= quantity
        product.save()

    return JsonResponse({
        "success": True
    })

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

        quantity = request.POST.get("quantity")
        purchase_price = request.POST.get("purchase_price")

        try:
            with transaction.atomic():
                product = Product.objects.create(
                    barcode=barcode,
                    name=name,
                    brand=brand,
                    price=price,
                )

                ProductBatch.objects.create(
                    product=product,
                    batch_number=batch_number,
                    expiration_date=expiration_date,
                    quantity=quantity,
                    purchase_price=purchase_price,
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

                    quantity = request.POST.get(
                        "new_quantity", ""
                    ).strip()

                    purchase_price = request.POST.get(
                        "new_purchase_price", ""
                    ).strip()

                    if expiration_date_text:
                        expiration_date = datetime.strptime(
                            expiration_date_text, "%d/%m/%Y"
                        ).date()
                    else:
                        expiration_date = None

                    ProductBatch.objects.create(
                        product=product,
                        batch_number=batch_number,
                        expiration_date=expiration_date,
                        quantity=quantity,
                        purchase_price=purchase_price,
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