from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
import requests
from .models import Product
import json

def scan(request):
    return render(request, "scan.html")

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