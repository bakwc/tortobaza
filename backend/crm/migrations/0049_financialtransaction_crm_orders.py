from django.db import migrations, models


def copy_crm_order_links(apps, schema_editor):
    FinancialTransaction = apps.get_model("crm", "FinancialTransaction")
    Through = FinancialTransaction.crm_orders.through
    Through.objects.bulk_create(
        [
            Through(financialtransaction_id=transaction_id, crmorder_id=order_id)
            for transaction_id, order_id in FinancialTransaction.objects.exclude(
                crm_order_id=None
            ).values_list("pk", "crm_order_id")
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0048_financialtransaction_income_type_cash_transfer"),
    ]

    operations = [
        migrations.AlterField(
            model_name="financialtransaction",
            name="crm_order",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="+",
                to="crm.crmorder",
            ),
        ),
        migrations.AddField(
            model_name="financialtransaction",
            name="crm_orders",
            field=models.ManyToManyField(
                blank=True,
                related_name="financial_transactions",
                to="crm.crmorder",
            ),
        ),
        migrations.RunPython(copy_crm_order_links, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="financialtransaction",
            name="crm_order",
        ),
    ]
