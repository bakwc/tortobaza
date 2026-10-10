from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0056_crmorder_payment_type_paypal"),
    ]

    operations = [
        migrations.AlterField(
            model_name="financialtransaction",
            name="expense_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("salary", "Salary"),
                    ("rent", "Rent"),
                    ("products", "Products"),
                    ("consumables", "Consumables"),
                    ("equipment", "Equipment"),
                    ("fees", "Fees"),
                    ("taxi", "Taxi"),
                    ("gasoline", "Gasoline"),
                    ("marketing", "Marketing"),
                ],
                max_length=20,
                verbose_name="Expense type",
            ),
        ),
        migrations.AlterField(
            model_name="financialtransactionrule",
            name="expense_type",
            field=models.CharField(
                choices=[
                    ("salary", "Salary"),
                    ("rent", "Rent"),
                    ("products", "Products"),
                    ("consumables", "Consumables"),
                    ("equipment", "Equipment"),
                    ("fees", "Fees"),
                    ("taxi", "Taxi"),
                    ("gasoline", "Gasoline"),
                    ("marketing", "Marketing"),
                ],
                max_length=20,
                verbose_name="Expense type",
            ),
        ),
    ]
