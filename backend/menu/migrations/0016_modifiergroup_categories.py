from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0015_modifiergroup_is_global"),
    ]

    operations = [
        migrations.AddField(
            model_name="modifiergroup",
            name="categories",
            field=models.ManyToManyField(
                blank=True,
                related_name="modifier_groups",
                to="menu.techcardcategory",
                verbose_name="Categories",
            ),
        ),
    ]
