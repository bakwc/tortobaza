import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.utils import timezone

from catalog.models import Option, Product


def _default_expires_at():
    return timezone.now() + timedelta(days=30)


class Cart(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(default=_default_expires_at)
    is_ordered = models.BooleanField(default=False)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Cart {self.token}"

    @property
    def subtotal(self) -> Decimal:
        total = Decimal("0")
        for item in self.items.all():
            total += item.line_total
        return total


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="+", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    comment = models.TextField(blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["added_at", "id"]

    def __str__(self) -> str:
        return f"{self.product.name} x{self.quantity}"

    @property
    def unit_price(self) -> Decimal:
        delta = sum((co.option.price_delta for co in self.options.all()), Decimal("0"))
        return self.product.base_price + delta

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity


class CartItemOption(models.Model):
    cart_item = models.ForeignKey(CartItem, related_name="options", on_delete=models.CASCADE)
    option = models.ForeignKey(Option, related_name="+", on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart_item", "option"], name="uniq_cart_item_option"),
        ]

    def __str__(self) -> str:
        return f"{self.cart_item_id}: {self.option}"
