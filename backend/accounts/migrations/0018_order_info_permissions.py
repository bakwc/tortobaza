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
    ("view_order_delivery_cooking_time", "Orders: view delivery cooking time"),
    ("view_order_delivery_address", "Orders: view delivery address"),
    ("view_order_delivery_contacts", "Orders: view delivery contacts"),
    ("view_order_delivery_price", "Orders: view delivery price"),
    ("view_order_pickup_time", "Orders: view pickup time"),
    ("view_order_pickup_cooking_time", "Orders: view pickup cooking time"),
    ("view_order_pickup_address", "Orders: view pickup address"),
    ("view_order_pickup_contacts", "Orders: view pickup contacts"),
    ("view_order_pickup_price", "Orders: view pickup price"),
    ("view_order_payment_link", "Orders: view payment link"),
    ("edit_order_payment_link", "Orders: create payment link"),
]

PRICE_TRIGGER_CODES = (
    "view_orders",
    "edit_orders",
    "view_finance",
    "edit_finance",
    "view_history",
)


def migrate_order_info_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")
    content_type, _created = ContentType.objects.get_or_create(
        app_label="accounts",
        model="sectionaccess",
    )

    def ensure(codename, name):
        perm, _created = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )
        return perm

    pickup_time = ensure("view_order_pickup_time", "Orders: view pickup time")
    delivery_cooking = ensure(
        "view_order_delivery_cooking_time",
        "Orders: view delivery cooking time",
    )
    pickup_cooking = ensure(
        "view_order_pickup_cooking_time",
        "Orders: view pickup cooking time",
    )
    delivery_price = ensure("view_order_delivery_price", "Orders: view delivery price")
    pickup_price = ensure("view_order_pickup_price", "Orders: view pickup price")

    delivery_time = Permission.objects.filter(
        content_type=content_type,
        codename="view_order_delivery_time",
    ).first()
    if delivery_time is not None:
        for group in Group.objects.filter(permissions=delivery_time).distinct():
            group.permissions.add(pickup_time)

    cooking = Permission.objects.filter(
        content_type=content_type,
        codename="view_order_cooking_time",
    ).first()
    if cooking is not None:
        for group in Group.objects.filter(permissions=cooking).distinct():
            group.permissions.add(delivery_cooking, pickup_cooking)
            group.permissions.remove(cooking)
        cooking.delete()

    trigger = Permission.objects.filter(
        content_type=content_type,
        codename__in=PRICE_TRIGGER_CODES,
    )
    for group in Group.objects.filter(permissions__in=trigger).distinct():
        group.permissions.add(delivery_price, pickup_price)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0017_order_payment_link_permissions"),
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
        migrations.RunPython(migrate_order_info_permissions, migrations.RunPython.noop),
    ]
