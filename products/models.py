from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=200)
    barcode = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

