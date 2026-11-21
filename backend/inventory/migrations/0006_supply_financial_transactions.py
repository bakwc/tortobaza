import django.db.models.deletion
from django.db import migrations, models


def copy_supply_transactions(apps, schema_editor):
    Supply = apps.get_model("inventory", "Supply")
    SupplyTransaction = apps.get_model("inventory", "SupplyTransaction")
    SupplyTransaction.objects.bulk_create(
        [
            SupplyTransaction(supply_id=supply.pk, financial_transaction_id=supply.financial_transaction_id)
            for supply in Supply.objects.exclude(financial_transaction_id=None)
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0069_financialaccount_cards_cardsmsmessage"),
        ("inventory", "0005_remove_inventorycountline_unit_cost"),
    ]

    operations = [
        migrations.CreateModel(
            name="SupplyTransaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "financial_transaction",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="supply_transaction",
                        to="crm.financialtransaction",
                        verbose_name="Bank transaction",
                    ),
                ),
                (
                    "supply",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="supply_transactions",
                        to="inventory.supply",
                        verbose_name="Supply",
                    ),
                ),
            ],
            options={
                "verbose_name": "Supply transaction",
                "verbose_name_plural": "Supply transactions",
            },
        ),
        migrations.AddField(
            model_name="supply",
            name="financial_transactions",
            field=models.ManyToManyField(
                blank=True,
                related_name="supplies",
                through="inventory.SupplyTransaction",
                to="crm.financialtransaction",
                verbose_name="Bank transactions",
            ),
        ),
        migrations.RunPython(copy_supply_transactions, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="supply",
            name="financial_transaction",
        ),
    ]
