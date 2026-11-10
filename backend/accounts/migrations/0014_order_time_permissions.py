from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0013_leads_section"),
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
                ],
            },
        ),
    ]
