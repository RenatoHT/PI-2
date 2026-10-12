from django.urls import path
from . import views
from . import api

urlpatterns = [
    path("scan/", views.scan, name="scan"),
    path("lookup/<str:barcode>/", views.lookup_product),
    path("stock/", views.stock, name="estoque"),
    path("product/<str:barcode>/", views.product_lookup, name="product_lookup"),
    path("finish-sale/", views.finish_sale, name="finish_sale"),
    
    #api 
    path("api/produtos/", api.products, name="api_products"),
    path("api/produtos/<str:barcode>/", api.product_detail, name="api_product_detail"),
    path("api/estoque/", api.stock_list, name="api_stock_list"),
    path("api/estoque/<str:barcode>/", api.stock_adjust, name="api_stock_adjust"),
    path("api/vendas/", api.sales, name="api_sales"),
    path("api/vendas/<int:sale_id>/", api.sale_detail, name="api_sale_detail"),
    path("api/caixa/movimentacoes/", api.cash_movements, name="api_cash_movements"),
    path("api/caixa/saldo/", api.cash_balance, name="api_cash_balance"),
    
]