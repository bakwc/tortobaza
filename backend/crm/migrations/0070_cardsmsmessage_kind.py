from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0069_financialaccount_cards_cardsmsmessage"),
    ]

    operations = [
        migrations.AddField(
            model_name="cardsmsmessage",
            name="kind",
            field=models.CharField(
                choices=[("expense", "Expense"), ("income", "Income")],
                default="expense",
                max_length=20,
                verbose_name="Kind",
            ),
        ),
    ]
