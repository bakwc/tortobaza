from django.db import migrations, models

BATCH_SIZE = 500


def fill_text_folded(apps, schema_editor):
    SocialMessage = apps.get_model("crm", "SocialMessage")
    ids = list(SocialMessage.objects.order_by("id").values_list("id", flat=True))
    for offset in range(0, len(ids), BATCH_SIZE):
        chunk_ids = ids[offset : offset + BATCH_SIZE]
        rows = list(SocialMessage.objects.filter(id__in=chunk_ids))
        for row in rows:
            row.text_folded = row.text.casefold()
        SocialMessage.objects.bulk_update(rows, ["text_folded"])


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0086_remove_crmorder_courier_alerted_departure_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="socialmessage",
            name="text_folded",
            field=models.TextField(blank=True, default="", editable=False, verbose_name="Folded text"),
        ),
        migrations.RunPython(fill_text_folded, migrations.RunPython.noop),
    ]
