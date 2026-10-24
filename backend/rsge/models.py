from django.db import models
from django.utils.translation import gettext_lazy as _


class WaybillSync(models.Model):
    synced_at = models.DateTimeField(verbose_name=_("Synced at"))

    class Meta:
        verbose_name = _("Waybill sync")
        verbose_name_plural = _("Waybill syncs")

    def __str__(self) -> str:
        return self.synced_at.isoformat()


class Waybill(models.Model):
    rs_id = models.BigIntegerField(unique=True, verbose_name=_("RS id"))
    waybill_number = models.CharField(max_length=64, verbose_name=_("Waybill number"))
    type = models.IntegerField(verbose_name=_("Type"))
    status = models.IntegerField(verbose_name=_("Status"))
    create_date = models.DateTimeField(verbose_name=_("Create date"))
    activate_date = models.DateTimeField(verbose_name=_("Activate date"))
    begin_date = models.DateTimeField(verbose_name=_("Begin date"))
    delivery_date = models.DateTimeField(null=True, verbose_name=_("Delivery date"))
    close_date = models.DateTimeField(null=True, verbose_name=_("Close date"))
    buyer_tin = models.CharField(max_length=32, verbose_name=_("Buyer TIN"))
    buyer_name = models.TextField(verbose_name=_("Buyer name"))
    seller_tin = models.CharField(max_length=32, verbose_name=_("Seller TIN"))
    seller_name = models.TextField(verbose_name=_("Seller name"))
    start_address = models.TextField(blank=True, verbose_name=_("Start address"))
    end_address = models.TextField(blank=True, verbose_name=_("End address"))
    driver_tin = models.CharField(max_length=32, blank=True, verbose_name=_("Driver TIN"))
    driver_name = models.TextField(blank=True, verbose_name=_("Driver name"))
    car_number = models.CharField(max_length=32, blank=True, verbose_name=_("Car number"))
    reception_info = models.TextField(blank=True, verbose_name=_("Reception info"))
    waybill_comment = models.TextField(blank=True, verbose_name=_("Comment"))
    transport_coast = models.DecimalField(max_digits=14, decimal_places=4, verbose_name=_("Transport cost"))
    full_amount = models.DecimalField(max_digits=14, decimal_places=4, verbose_name=_("Full amount"))
    s_user_id = models.BigIntegerField(verbose_name=_("Seller user id"))
    par_id = models.BigIntegerField(null=True, verbose_name=_("Parent id"))
    invoice_id = models.BigIntegerField(null=True, verbose_name=_("Invoice id"))
    is_confirmed = models.IntegerField(verbose_name=_("Is confirmed"))
    is_corrected = models.IntegerField(verbose_name=_("Is corrected"))
    seller_st = models.IntegerField(verbose_name=_("Seller ST"))
    is_med = models.IntegerField(verbose_name=_("Is med"))

    class Meta:
        ordering = ["-create_date", "-rs_id"]
        verbose_name = _("Waybill")
        verbose_name_plural = _("Waybills")

    def __str__(self) -> str:
        return self.waybill_number


class WaybillGood(models.Model):
    waybill = models.ForeignKey(
        Waybill,
        related_name="goods",
        on_delete=models.CASCADE,
        verbose_name=_("Waybill"),
    )
    rs_id = models.BigIntegerField(unique=True, verbose_name=_("RS id"))
    name = models.TextField(verbose_name=_("Name"))
    unit_id = models.IntegerField(verbose_name=_("Unit id"))
    unit_txt = models.CharField(max_length=64, blank=True, verbose_name=_("Unit"))
    quantity = models.DecimalField(max_digits=14, decimal_places=4, verbose_name=_("Quantity"))
    price = models.DecimalField(max_digits=14, decimal_places=4, verbose_name=_("Price"))
    amount = models.DecimalField(max_digits=14, decimal_places=4, verbose_name=_("Amount"))
    bar_code = models.CharField(max_length=128, blank=True, verbose_name=_("Barcode"))
    a_id = models.BigIntegerField(verbose_name=_("A id"))
    vat_type = models.IntegerField(verbose_name=_("VAT type"))
    quantity_ext = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        verbose_name=_("Quantity ext"),
    )
    status = models.IntegerField(verbose_name=_("Status"))
    quantity_f = models.DecimalField(max_digits=14, decimal_places=4, verbose_name=_("Quantity F"))

    class Meta:
        ordering = ["rs_id"]
        verbose_name = _("Waybill good")
        verbose_name_plural = _("Waybill goods")

    def __str__(self) -> str:
        return self.name
