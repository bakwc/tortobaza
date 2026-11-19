from django.db import models
from django.utils.translation import gettext_lazy as _


class WishlistItem(models.Model):
    title = models.CharField(max_length=200, verbose_name=_("Title"))
    purpose = models.TextField(blank=True, default="", verbose_name=_("Purpose"))
    priority = models.PositiveIntegerField(verbose_name=_("Priority"))
    cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Cost"),
    )

    class Meta:
        ordering = ["priority", "id"]
        verbose_name = _("Wishlist item")
        verbose_name_plural = _("Wishlist items")

    def __str__(self) -> str:
        return self.title
