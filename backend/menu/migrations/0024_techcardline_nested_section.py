import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("menu", "0023_techcard_optional_quantity_and_storage_text"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="techcardline",
            name="menu_techcardline_one_component",
        ),
        migrations.AddField(
            model_name="techcardline",
            name="nested_section",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="nested_in_lines",
                to="menu.techcardsection",
                verbose_name="Section",
            ),
        ),
        migrations.AddConstraint(
            model_name="techcardline",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("ingredient__isnull", False),
                        ("nested_section__isnull", True),
                        ("nested_tech_card__isnull", True),
                        ("semi_product__isnull", True),
                    ),
                    models.Q(
                        ("ingredient__isnull", True),
                        ("nested_section__isnull", True),
                        ("nested_tech_card__isnull", True),
                        ("semi_product__isnull", False),
                    ),
                    models.Q(
                        ("ingredient__isnull", True),
                        ("nested_section__isnull", True),
                        ("nested_tech_card__isnull", False),
                        ("semi_product__isnull", True),
                    ),
                    models.Q(
                        ("ingredient__isnull", True),
                        ("nested_section__isnull", False),
                        ("nested_tech_card__isnull", True),
                        ("semi_product__isnull", True),
                    ),
                    _connector="OR",
                ),
                name="menu_techcardline_one_component",
            ),
        ),
    ]
