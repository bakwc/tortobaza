from django.db import migrations


PERMISSIONS = [
    ("view_orders", "Orders: view and change status"),
    ("edit_orders", "Orders: create, edit, delete"),
    ("view_menu", "Menu: view"),
    ("edit_menu", "Menu: edit"),
    ("view_inventory", "Inventory: view"),
    ("edit_inventory", "Inventory: edit"),
    ("view_finished", "Finished goods: view"),
    ("edit_own_finished", "Finished goods: create and edit own"),
    ("edit_finished", "Finished goods: create and edit all"),
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
    ("view_leads", "Leads: view"),
    ("edit_leads", "Leads: edit"),
    ("view_order_delivery_time", "Orders: view delivery time"),
    ("view_order_cooking_time", "Orders: view cooking time"),
    ("view_order_delivery_address", "Orders: view delivery address"),
    ("view_order_pickup_address", "Orders: view pickup address"),
    ("view_order_delivery_contacts", "Orders: view delivery contacts"),
    ("view_order_pickup_contacts", "Orders: view pickup contacts"),
]

NEW_PERMISSIONS = [
    ("view_order_delivery_address", "Orders: view delivery address"),
    ("view_order_pickup_address", "Orders: view pickup address"),
    ("view_order_delivery_contacts", "Orders: view delivery contacts"),
    ("view_order_pickup_contacts", "Orders: view pickup contacts"),
]

TRIGGER_CODES = (
    "view_orders",
    "edit_orders",
    "view_finance",
    "edit_finance",
    "view_history",
)


def grant_existing_groups(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")
    content_type, _created = ContentType.objects.get_or_create(
        app_label="accounts",
        model="sectionaccess",
    )
    new_perms = []
    for codename, name in NEW_PERMISSIONS:
        perm, _created = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )
        new_perms.append(perm)
    trigger = Permission.objects.filter(
        content_type=content_type,
        codename__in=TRIGGER_CODES,
    )
    groups = Group.objects.filter(permissions__in=trigger).distinct()
    for group in groups:
        group.permissions.add(*new_perms)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0015_userprofile_skip_late_alerts"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="sectionaccess",
            options={
                "default_permissions": (),
                "managed": False,
                "permissions": PERMISSIONS,
            },
        ),
        migrations.RunPython(grant_existing_groups, migrations.RunPython.noop),
    ]
