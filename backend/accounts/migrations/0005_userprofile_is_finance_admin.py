from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_alter_userprofile_options_alter_userprofile_gender_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="is_finance_admin",
            field=models.BooleanField(default=False, verbose_name="Finance admin"),
        ),
    ]
