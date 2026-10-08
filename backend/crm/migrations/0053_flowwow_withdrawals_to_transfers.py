from django.db import migrations


def mark_flowwow_withdrawals_as_transfers(apps, schema_editor):
    FinancialTransaction = apps.get_model("crm", "FinancialTransaction")
    FinancialTransaction.objects.filter(
        account__name="Flowwow",
        kind="withdrawal",
    ).update(kind="transfer")


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0052_financialtransaction_matched_transaction"),
    ]

    operations = [
        migrations.RunPython(
            mark_flowwow_withdrawals_as_transfers,
            migrations.RunPython.noop,
        ),
    ]
