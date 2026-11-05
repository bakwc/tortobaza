import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0078_socialmessage_profile"),
        ("menu", "0014_modifier_nested_tech_card"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="crmorderitemline",
            name="crm_crmorderitemline_one_component",
        ),
        migrations.AddField(
            model_name="crmorderitemline",
            name="tech_card",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="crm_order_item_lines",
                to="menu.techcard",
                verbose_name="Tech card",
            ),
        ),
        migrations.AddConstraint(
            model_name="crmorderitemline",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("ingredient__isnull", False),
                        ("semi_product__isnull", True),
                        ("tech_card__isnull", True),
                    ),
                    models.Q(
                        ("ingredient__isnull", True),
                        ("semi_product__isnull", False),
                        ("tech_card__isnull", True),
                    ),
                    models.Q(
                        ("ingredient__isnull", True),
                        ("semi_product__isnull", True),
                        ("tech_card__isnull", False),
                    ),
                    _connector="OR",
                ),
                name="crm_crmorderitemline_one_component",
            ),
        ),
    ]
