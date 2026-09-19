from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0034_flowwowwebhookevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="crmorder",
            name="flowwow_order_id",
            field=models.IntegerField(blank=True, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="crmorderimage",
            name="source_url",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddConstraint(
            model_name="crmorderimage",
            constraint=models.UniqueConstraint(
                fields=("order", "source_url"),
                name="uniq_crmorderimage_order_source_url",
            ),
        ),
    ]
