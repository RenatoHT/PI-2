from django.db import models

#Informações sobre o produto
class Product(models.Model):
    name = models.CharField(max_length=200)
    barcode = models.CharField(max_length=50, unique=True)
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.name