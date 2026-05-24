from django.db import migrations


def forwards(apps, schema_editor):
    PickupLocation = apps.get_model("orders", "PickupLocation")

    def fill_en(Model, pairs):
        for row in Model.objects.all().iterator():
            updates = {}
            for en_field, base_field in pairs:
                en_val = getattr(row, en_field)
                base_val = getattr(row, base_field)
                if base_val is None or base_val == "":
                    continue
                if en_val is None or en_val == "":
                    updates[en_field] = base_val
            if updates:
                Model.objects.filter(pk=row.pk).update(**updates)

    fill_en(
        PickupLocation,
        [("name_en", "name"), ("address_en", "address")],
    )


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0005_order_locale_pickuplocation_address_en_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
