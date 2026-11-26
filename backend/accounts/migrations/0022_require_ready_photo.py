from django.db import migrations


PERMISSIONS = [
    ("view_orders", "Orders: view"),
    ("edit_orders", "Orders: create, edit, delete"),
    ("require_ready_photo", "Orders: require a photo when marking ready"),
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
    ("set_order_delivery_status_unconfirmed", "Orders: set delivery status to unconfirmed"),
    ("set_order_delivery_status_new", "Orders: set delivery status to new"),
    ("set_order_delivery_status_in_work", "Orders: set delivery status to in work"),
    ("set_order_delivery_status_ready", "Orders: set delivery status to ready"),
    ("set_order_delivery_status_client_approved", "Orders: set delivery status to client approved"),
    ("set_order_delivery_status_in_delivery", "Orders: set delivery status to in delivery"),
    ("set_order_delivery_status_delivered", "Orders: set delivery status to delivered"),
    ("set_order_pickup_status_unconfirmed", "Orders: set pickup status to unconfirmed"),
    ("set_order_pickup_status_new", "Orders: set pickup status to new"),
    ("set_order_pickup_status_in_work", "Orders: set pickup status to in work"),
    ("set_order_pickup_status_ready", "Orders: set pickup status to ready"),
    ("set_order_pickup_status_client_approved", "Orders: set pickup status to client approved"),
    ("set_order_pickup_status_in_delivery", "Orders: set pickup status to in delivery"),
    ("set_order_pickup_status_delivered", "Orders: set pickup status to delivered"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0021_order_status_permissions"),
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
