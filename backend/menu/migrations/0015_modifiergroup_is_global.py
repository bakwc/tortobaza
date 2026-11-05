from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0014_modifier_nested_tech_card"),
    ]

    operations = [
        migrations.AddField(
            model_name="modifiergroup",
            name="is_global",
            field=models.BooleanField(default=False, verbose_name="Is global"),
        ),
    ]
