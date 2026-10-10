from django.db import models
from django.utils import timezone

#Informações sobre o produto
class Product(models.Model):
    name = models.CharField(max_length=200)
    barcode = models.CharField(max_length=50, unique=True)
    quantity = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.name


class Sale(models.Model):
    # A data_venda preenche-se automaticamente com o momento exato em que a venda for criada
    sale_date = models.DateTimeField(default=timezone.now)
    # Podemos começar com o total a 0 e calcular depois, dependendo dos itens
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Sale {self.id} - {self.sale_date.strftime('%Y-%m-%d %H:%M')}"


class SaleItems(models.Model):
    # ForeignKey
    # Se a venda for apagada, apagamos os itens (cascade)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')

    # Relacionamento com o produto, qual produto foi levado?
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity_sold = models.PositiveIntegerField(default=1)

    # Registramos o preço unitario, caso o preço do produto original mude no futuro
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Sale Item"
        verbose_name_plural = "Sale Items"

    def __str__(self):
        return f"{self.quantity_sold} x {self.product.name} (Sale {self.sale.id})"
