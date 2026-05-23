from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0001_initial"),
        ("catalog", "0005_product_delivery_schedule_tier"),
    ]

    operations = [
        migrations.RemoveField(model_name="order", name="timeslot"),
        migrations.DeleteModel(name="DeliveryTimeslot"),
    ]
