from django.db import migrations, models

from crm.telegram import _weight_kg_text


def _line_name(line):
    if line.ingredient_id is not None:
        return line.ingredient.name
    if line.semi_product_id is not None:
        return line.semi_product.name
    return line.tech_card.name


def backfill_telegram_posted_items(apps, schema_editor):
    CrmOrder = apps.get_model("crm", "CrmOrder")
    orders = CrmOrder.objects.filter(telegram_message_id__isnull=False).prefetch_related(
        "items__tech_card",
        "items__modifiers__modifier",
        "items__lines__ingredient",
        "items__lines__semi_product",
        "items__lines__tech_card",
    )
    for order in orders:
        rows = []
        for item in order.items.all().order_by("position", "id"):
            name = item.name.strip()
            if not name and item.tech_card_id is not None:
                name = item.tech_card.name
            rows.append(
                {
                    "name": name,
                    "quantity": item.quantity,
                    "weight_kg": _weight_kg_text(item.weight_kg),
                    "modifiers": [
                        [row.modifier.name, row.quantity]
                        for row in item.modifiers.all().order_by("id")
                    ],
                    "lines": [_line_name(line) for line in item.lines.all().order_by("id")],
                    "comment": item.comment,
                }
            )
        order.telegram_posted_items = rows
        order.save(update_fields=["telegram_posted_items"])


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0084_crmorder_weight_blank"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="telegram_posted_items",
            field=models.JSONField(default=list, verbose_name="Telegram posted items"),
        ),
        migrations.RunPython(backfill_telegram_posted_items, migrations.RunPython.noop),
    ]
