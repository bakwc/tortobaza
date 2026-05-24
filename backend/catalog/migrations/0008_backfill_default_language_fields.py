from django.db import migrations


def forwards(apps, schema_editor):
    def fill_en(Model, pairs):
        for row in Model.objects.all().iterator():
            updates = {}
            for en_field, base_field in pairs:
                en_val = getattr(row, en_field)
                base_val = getattr(row, base_field)
                if base_val is None or base_val == "":
                    continue
                if en_val is None or en_val == "":
                    updates[en_field] = base_val
            if updates:
                Model.objects.filter(pk=row.pk).update(**updates)

    Category = apps.get_model("catalog", "Category")
    Product = apps.get_model("catalog", "Product")
    OptionGroup = apps.get_model("catalog", "OptionGroup")
    Option = apps.get_model("catalog", "Option")
    ProductImage = apps.get_model("catalog", "ProductImage")

    fill_en(Category, [("name_en", "name")])
    fill_en(Product, [("name_en", "name"), ("description_en", "description")])
    fill_en(OptionGroup, [("name_en", "name")])
    fill_en(Option, [("name_en", "name")])
    fill_en(ProductImage, [("alt_en", "alt")])


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0007_category_name_en_category_name_ka_category_name_ru_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
