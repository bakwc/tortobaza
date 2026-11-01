from decimal import Decimal

from django.db import migrations


def sale_price_per_piece(apps, schema_editor):
    TechCard = apps.get_model("menu", "TechCard")
    for card in TechCard.objects.filter(kind="piece", sale_price__isnull=False):
        card.sale_price = (card.sale_price / Decimal(card.basis_quantity)).quantize(Decimal("0.01"))
        card.save(update_fields=["sale_price"])


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0011_sale_price"),
    ]

    operations = [
        migrations.RunPython(sale_price_per_piece, migrations.RunPython.noop),
    ]
