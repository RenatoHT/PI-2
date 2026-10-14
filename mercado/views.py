from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
import requests
from .models import Product, ProductBatch
from django.db.models import Sum
from django.db import transaction
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

#Página de estoque
def stock(request):
    products = Product.objects.annotate(
        total_quantity=Sum("batches__quantity")
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
        expiration_date = request.POST.get("expiration_date")
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


"""depreciado
def stock(request):
    if request.method == "POST":
        action = request.POST.get("action")

        if action == "delete":
            barcode = request.POST.get("barcode")

            product = get_object_or_404(
                Product,
                barcode=barcode
            )

            product.delete()

        elif action == "add":
            barcode = request.POST.get("barcode")
            name = request.POST.get("name")
            quantity = int(request.POST.get("quantity") or 0)
            price = request.POST.get("price")

            product = Product.objects.filter(
                barcode=barcode
            ).first()

            if product:
                product.quantity += quantity
                product.price = price
                product.save()
            else:
                Product.objects.create(
                    barcode=barcode,
                    name=name,
                    quantity=quantity,
                    price=price,
                )

    products = Product.objects.all().order_by("name")

    return render(
        request,
        "stock.html",
        {"products": products}
    )
"""


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