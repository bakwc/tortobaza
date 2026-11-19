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
    ("view_wishlist", "Wishlist: view"),
    ("edit_wishlist", "Wishlist: edit"),
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


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0019_userprofile_bark_device_key"),
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
    ]
