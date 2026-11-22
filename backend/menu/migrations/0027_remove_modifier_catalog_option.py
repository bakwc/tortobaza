from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0026_techcarddraft"),
        ("catalog", "0023_option_modifiers"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="modifier",
            name="catalog_option",
        ),
    ]
