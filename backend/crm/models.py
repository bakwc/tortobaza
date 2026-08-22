from django.db import models


class CrmOrder(models.Model):
    FULFILLMENT_DELIVERY = "delivery"
    FULFILLMENT_PICKUP = "pickup"
    FULFILLMENT_CHOICES = [
        (FULFILLMENT_DELIVERY, "Delivery"),
        (FULFILLMENT_PICKUP, "Pickup"),
    ]

    PAYMENT_CASH = "cash"
    PAYMENT_TERMINAL = "terminal"
    PAYMENT_TBC = "tbc"
    PAYMENT_BOG = "bog"
    PAYMENT_TYPE_CHOICES = [
        (PAYMENT_CASH, "Cash"),
        (PAYMENT_TERMINAL, "Terminal"),
        (PAYMENT_TBC, "TBC Transfer"),
        (PAYMENT_BOG, "BOG Transfer"),
    ]

    date = models.DateField()
    time_start = models.TimeField()
    time_end = models.TimeField(null=True, blank=True)
    contact = models.TextField()
    fulfillment_type = models.CharField(
        max_length=10,
        choices=FULFILLMENT_CHOICES,
        default=FULFILLMENT_DELIVERY,
    )
    weight = models.CharField(max_length=50)
    filling = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    cake_price = models.DecimalField(max_digits=10, decimal_places=2)
    prepayment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default=PAYMENT_CASH,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "time_start"]

    def __str__(self) -> str:
        time_display = (
            f"{self.time_start.strftime('%H:%M')}-{self.time_end.strftime('%H:%M')}"
            if self.time_end
            else self.time_start.strftime("%H:%M")
        )
        return f"{self.date} {time_display} - {self.contact[:30]}"


class CrmOrderImage(models.Model):
    order = models.ForeignKey(CrmOrder, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="crm_orders/")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return f"Image #{self.pk} for CrmOrder #{self.order_id}"
