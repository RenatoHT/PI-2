from django.urls import path
from . import views

urlpatterns = [
    path("scan/", views.scan, name="scan"),
    path("lookup/<str:barcode>/", views.lookup_product),
    path("stock/", views.stock, name="estoque"),
    path("product/<str:barcode>/", views.product_lookup, name="product_lookup"),
    path("finish-sale/", views.finish_sale, name="finish_sale"),
]