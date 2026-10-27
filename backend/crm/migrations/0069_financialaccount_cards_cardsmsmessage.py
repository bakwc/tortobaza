from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0068_link_historical_website_orders"),
    ]

    operations = [
        migrations.AddField(
            model_name="financialaccount",
            name="cards",
            field=models.CharField(blank=True, default="", max_length=255, verbose_name="Cards"),
        ),
        migrations.CreateModel(
            name="CardSmsMessage",
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
                ("message_id", models.CharField(max_length=512, unique=True, verbose_name="Message id")),
                ("received_at", models.DateTimeField(verbose_name="Received at")),
                ("raw_body", models.TextField(verbose_name="Body")),
                ("card_last4", models.CharField(blank=True, default="", max_length=4, verbose_name="Card")),
                ("currency", models.CharField(blank=True, default="", max_length=3, verbose_name="Currency")),
                (
                    "amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=12,
                        null=True,
                        verbose_name="Amount",
                    ),
                ),
                ("merchant", models.CharField(blank=True, default="", max_length=255, verbose_name="Merchant")),
                ("sms_date", models.DateField(blank=True, null=True, verbose_name="SMS date")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("unparsed", "Unparsed"),
                            ("unmatched", "Unmatched"),
                            ("ambiguous", "Ambiguous"),
                            ("inserted", "Inserted"),
                        ],
                        max_length=16,
                        verbose_name="Status",
                    ),
                ),
                (
                    "finance_db",
                    models.CharField(blank=True, default="", max_length=16, verbose_name="Finance database"),
                ),
                (
                    "transaction_id",
                    models.PositiveIntegerField(blank=True, null=True, verbose_name="Transaction id"),
                ),
            ],
            options={
                "verbose_name": "Card SMS",
                "verbose_name_plural": "Card SMS",
                "ordering": ["-received_at", "-id"],
            },
        ),
    ]
