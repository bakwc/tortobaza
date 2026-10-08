import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from catalog.models import Option, Product


def _default_expires_at():
    return timezone.now() + timedelta(days=30)


class Cart(models.Model):
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name=_("Token"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))
    expires_at = models.DateTimeField(default=_default_expires_at, verbose_name=_("Expires at"))
    is_ordered = models.BooleanField(default=False, verbose_name=_("Is ordered"))

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = _("Cart")
        verbose_name_plural = _("Carts")

    def __str__(self) -> str:
        return f"Cart {self.token}"

    @property
    def subtotal(self) -> Decimal:
        total = Decimal("0")
        for item in self.items.all():
            total += item.line_total
        return total


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        related_name="items",
        on_delete=models.CASCADE,
        verbose_name=_("Cart"),
    )
    product = models.ForeignKey(
        Product,
        related_name="+",
        on_delete=models.PROTECT,
        verbose_name=_("Product"),
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("Quantity"))
    comment = models.TextField(blank=True, verbose_name=_("Comment"))
    added_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Added at"))

    class Meta:
        ordering = ["added_at", "id"]
        verbose_name = _("Cart item")
        verbose_name_plural = _("Cart items")

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
    cart_item = models.ForeignKey(
        CartItem,
        related_name="options",
        on_delete=models.CASCADE,
        verbose_name=_("Cart item"),
    )
    option = models.ForeignKey(
        Option,
        related_name="+",
        on_delete=models.PROTECT,
        verbose_name=_("Option"),
    )

    class Meta:
        verbose_name = _("Cart item option")
        verbose_name_plural = _("Cart item options")
        constraints = [
            models.UniqueConstraint(fields=["cart_item", "option"], name="uniq_cart_item_option"),
        ]

    def __str__(self) -> str:
        return f"{self.cart_item_id}: {self.option}"
