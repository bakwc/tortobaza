from django.db import migrations


def grant_schedule(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")
    content_type = ContentType.objects.get(app_label="accounts", model="sectionaccess")
    view_schedule, _created = Permission.objects.get_or_create(
        content_type=content_type,
        codename="view_schedule",
        defaults={"name": "Schedule: view"},
    )
    edit_schedule, _created = Permission.objects.get_or_create(
        content_type=content_type,
        codename="edit_schedule",
        defaults={"name": "Schedule: edit timesheet and schedule"},
    )
    view_employees = Permission.objects.get(content_type=content_type, codename="view_employees")
    edit_employees = Permission.objects.get(content_type=content_type, codename="edit_employees")
    for group in Group.objects.filter(permissions=view_employees):
        group.permissions.add(view_schedule)
    for group in Group.objects.filter(permissions=edit_employees):
        group.permissions.add(edit_schedule)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_catalog_section"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="sectionaccess",
            options={
                "default_permissions": (),
                "managed": False,
                "permissions": [
                    ("view_orders", "Orders: view and change status"),
                    ("edit_orders", "Orders: create, edit, delete"),
                    ("view_menu", "Menu: view"),
                    ("edit_menu", "Menu: edit"),
                    ("view_inventory", "Inventory: view"),
                    ("edit_inventory", "Inventory: edit"),
                    ("view_finance", "Finance: view"),
                    ("edit_finance", "Finance: edit"),
                    ("view_employees", "Employees: view"),
                    ("edit_employees", "Employees: edit"),
                    ("view_schedule", "Schedule: view"),
                    ("edit_schedule", "Schedule: edit timesheet and schedule"),
                    ("view_rsge", "RSGE: view"),
                    ("edit_rsge", "RSGE: edit"),
                    ("view_analytics", "Analytics: view"),
                    ("view_history", "History: view"),
                    ("view_costs", "See costs, suppliers and supplies"),
                    ("view_catalog", "Catalog: view"),
                    ("edit_catalog", "Catalog: edit"),
                ],
            },
        ),
        migrations.RunPython(grant_schedule, migrations.RunPython.noop),
    ]
