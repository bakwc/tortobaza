from django.db import migrations, models


PERMISSIONS = [
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
    ("view_rsge", "RSGE: view"),
    ("edit_rsge", "RSGE: edit"),
    ("view_analytics", "Analytics: view"),
    ("view_history", "History: view"),
    ("view_costs", "See costs, suppliers and supplies"),
]

CHEF_CODES = ("view_orders",)
STAFF_CODES = ("edit_orders", "edit_menu", "edit_inventory")


def assign_groups(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    Group = apps.get_model("auth", "Group")
    User = apps.get_model("auth", "User")
    UserProfile = apps.get_model("accounts", "UserProfile")
    content_type, _created = ContentType.objects.get_or_create(
        app_label="accounts",
        model="sectionaccess",
    )
    perms = {}
    for codename, name in PERMISSIONS:
        perm, _created = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )
        perms[codename] = perm
    chefs, _created = Group.objects.get_or_create(name="Кондитеры")
    chefs.permissions.add(*(perms[code] for code in CHEF_CODES))
    staff, _created = Group.objects.get_or_create(name="Персонал")
    staff.permissions.add(*(perms[code] for code in STAFF_CODES))
    finance_codes = [code for code, _name in PERMISSIONS if code not in CHEF_CODES and code not in STAFF_CODES]
    finance, _created = Group.objects.get_or_create(name="Финансы")
    finance.permissions.add(*(perms[code] for code in finance_codes))
    for user in User.objects.all():
        user.groups.add(chefs)
    for user in User.objects.filter(is_staff=True):
        user.groups.add(staff)
    finance_ids = UserProfile.objects.filter(is_finance_admin=True).values_list("user_id", flat=True)
    for user in User.objects.filter(pk__in=list(finance_ids)):
        user.groups.add(finance)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_userprofile_in_schedule_userprofile_position"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="SectionAccess",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
            ],
            options={
                "managed": False,
                "default_permissions": (),
                "permissions": PERMISSIONS,
            },
        ),
        migrations.RunPython(assign_groups, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="userprofile",
            name="is_finance_admin",
        ),
    ]
