from django.db import migrations

# Website order number, CRM order id. Reviewed once against the production copy.
_PAIRS = (
    ("73020", 1000016),
    ("73037", 1000065),
    ("73046", 1000082),
    ("73104", 1000099),
    ("73056", 1000108),
    ("73073", 1000110),
    ("73024", 1000139),
    ("73192", 1000156),
    ("73225", 1000300),
    ("73243", 26),
    ("73175", 1000126),
)


def link_historical_website_orders(apps, schema_editor):
    CrmOrder = apps.get_model("crm", "CrmOrder")
    Order = apps.get_model("orders", "Order")
    for number, crm_id in _PAIRS:
        website = Order.objects.filter(number=number).first()
        if website is None:
            continue
        if CrmOrder.objects.filter(website_order_id=website.pk).exists():
            continue
        CrmOrder.objects.filter(pk=crm_id, deleted=False, website_order__isnull=True).update(
            website_order_id=website.pk
        )


def unlink_historical_website_orders(apps, schema_editor):
    CrmOrder = apps.get_model("crm", "CrmOrder")
    Order = apps.get_model("orders", "Order")
    for number, crm_id in _PAIRS:
        website = Order.objects.filter(number=number).first()
        if website is None:
            continue
        CrmOrder.objects.filter(pk=crm_id, website_order_id=website.pk).update(website_order_id=None)


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0067_crmorder_paypal_payment_link"),
        ("orders", "0015_alter_order_payment_method_paypalpayment"),
    ]

    operations = [
        migrations.RunPython(link_historical_website_orders, unlink_historical_website_orders),
    ]
