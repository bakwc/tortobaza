from django.db import migrations


def clear_instagram_resolved_addresses(apps, schema_editor):
    ResolvedYandexAddress = apps.get_model("crm", "ResolvedYandexAddress")
    ResolvedGoogleAddress = apps.get_model("crm", "ResolvedGoogleAddress")
    instagram_rows = ResolvedYandexAddress.objects.filter(
        yandex_url__contains="l.instagram.com/"
    )
    instagram_addresses = list(instagram_rows.values_list("address", flat=True))
    ResolvedGoogleAddress.objects.filter(address__in=instagram_addresses).delete()
    instagram_rows.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0026_clear_instagram_resolved_google_addresses"),
    ]

    operations = [
        migrations.RunPython(
            clear_instagram_resolved_addresses,
            migrations.RunPython.noop,
        ),
    ]
