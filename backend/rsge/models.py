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


class InvoiceSync(models.Model):
    synced_at = models.DateTimeField(verbose_name=_("Synced at"))

    class Meta:
        verbose_name = _("Invoice sync")
        verbose_name_plural = _("Invoice syncs")

    def __str__(self) -> str:
        return self.synced_at.isoformat()


class Invoice(models.Model):
    rs_id = models.BigIntegerField(unique=True, verbose_name=_("RS id"))
    seller_un_id = models.BigIntegerField(verbose_name=_("Seller un id"))
    seq_num_b = models.BigIntegerField(null=True, verbose_name=_("Sequence number"))
    status = models.IntegerField(verbose_name=_("Status"))
    was_ref = models.IntegerField(verbose_name=_("Was ref"))
    series = models.CharField(max_length=32, verbose_name=_("Series"))
    number = models.CharField(max_length=64, verbose_name=_("Number"))
    reg_dt = models.DateTimeField(verbose_name=_("Registration date"))
    operation_dt = models.DateTimeField(verbose_name=_("Operation date"))
    s_user_id = models.BigIntegerField(verbose_name=_("Seller user id"))
    b_s_user_id = models.BigIntegerField(verbose_name=_("Buyer user id"))
    doc_mos_nom = models.CharField(max_length=128, blank=True, verbose_name=_("Document number"))
    seller_tin = models.CharField(max_length=32, verbose_name=_("Seller TIN"))
    org_name = models.TextField(verbose_name=_("Organization"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))
    amount = models.DecimalField(max_digits=14, decimal_places=4, verbose_name=_("Amount"))
    vat = models.DecimalField(max_digits=14, decimal_places=4, verbose_name=_("VAT"))
    k_id = models.BigIntegerField(verbose_name=_("K id"))
    agree_date = models.DateTimeField(null=True, verbose_name=_("Agree date"))
    agree_s_user_id = models.BigIntegerField(null=True, verbose_name=_("Agree user id"))
    ref_date = models.DateTimeField(null=True, verbose_name=_("Ref date"))
    ref_s_user_id = models.BigIntegerField(null=True, verbose_name=_("Ref user id"))
    note = models.TextField(blank=True, verbose_name=_("Note"))

    class Meta:
        ordering = ["-reg_dt", "-rs_id"]
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")

    def __str__(self) -> str:
        return f"{self.series} {self.number}"


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        related_name="lines",
        on_delete=models.CASCADE,
        verbose_name=_("Invoice"),
    )
    rs_id = models.BigIntegerField(unique=True, verbose_name=_("RS id"))
    goods = models.TextField(verbose_name=_("Goods"))
    unit = models.CharField(max_length=64, verbose_name=_("Unit"))
    quantity = models.DecimalField(max_digits=14, decimal_places=4, verbose_name=_("Quantity"))
    full_amount = models.DecimalField(max_digits=14, decimal_places=4, verbose_name=_("Full amount"))
    vat_amount = models.DecimalField(max_digits=14, decimal_places=4, verbose_name=_("VAT amount"))
    excise_amount = models.DecimalField(
        max_digits=14,
        decimal_places=4,
        null=True,
        verbose_name=_("Excise amount"),
    )
    excise_id = models.BigIntegerField(verbose_name=_("Excise id"))
    waybill_id = models.BigIntegerField(null=True, verbose_name=_("Waybill id"))
    vat_type = models.IntegerField(verbose_name=_("VAT type"))

    class Meta:
        ordering = ["rs_id"]
        verbose_name = _("Invoice line")
        verbose_name_plural = _("Invoice lines")

    def __str__(self) -> str:
        return self.goods
