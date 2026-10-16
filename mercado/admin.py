from django.contrib import admin
from .models import Product, Sale, SaleItems, ProductBatch, CashMovement


admin.site.register(Product)
admin.site.register(Sale)
admin.site.register(SaleItems)
admin.site.register(ProductBatch)
admin.site.register(CashMovement)
