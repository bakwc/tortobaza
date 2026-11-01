from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.permissions import grant


class GroupApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.viewer = User.objects.create_user(username="viewer", password="password")
        self.editor = User.objects.create_user(username="editor", password="password")
        grant(self.viewer, "view_employees")
        grant(self.editor, "edit_employees")

    def test_viewer_can_list_but_not_change(self):
        self.client.force_authenticate(user=self.viewer)
        listed = self.client.get("/api/accounts/groups/")
        self.assertEqual(listed.status_code, 200)
        created = self.client.post(
            "/api/accounts/groups/",
            {"name": "Кухня", "permissions": ["view_orders"]},
            format="json",
        )
        self.assertEqual(created.status_code, 403)
        permissions = self.client.get("/api/accounts/permissions/")
        self.assertEqual(permissions.status_code, 200)
        codes = [row["code"] for row in permissions.json()]
        self.assertIn("view_orders", codes)
        self.assertIn("edit_orders", codes)
        self.assertIn("view_costs", codes)

    def test_editor_creates_updates_and_deletes_group(self):
        self.client.force_authenticate(user=self.editor)
        created = self.client.post(
            "/api/accounts/groups/",
            {"name": "Кухня", "permissions": ["view_orders", "edit_menu"]},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        body = created.json()
        self.assertEqual(body["name"], "Кухня")
        self.assertEqual(body["permissions"], ["edit_menu", "view_orders"])
        group_id = body["id"]
        updated = self.client.put(
            f"/api/accounts/groups/{group_id}/",
            {"name": "Зал", "permissions": ["view_inventory"]},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(updated.json()["name"], "Зал")
        self.assertEqual(updated.json()["permissions"], ["view_inventory"])
        unknown = self.client.put(
            f"/api/accounts/groups/{group_id}/",
            {"name": "Зал", "permissions": ["delete_orders"]},
            format="json",
        )
        self.assertEqual(unknown.status_code, 400)
        deleted = self.client.delete(f"/api/accounts/groups/{group_id}/")
        self.assertEqual(deleted.status_code, 204)
        missing = self.client.get("/api/accounts/groups/")
        self.assertEqual([row["id"] for row in missing.json() if row["id"] == group_id], [])

    def test_edit_catalog_grants_catalog_model_permissions(self):
        self.client.force_authenticate(user=self.editor)
        created = self.client.post(
            "/api/accounts/groups/",
            {"name": "Сайт", "permissions": ["edit_catalog"]},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        member = User.objects.create_user(username="anna", password="password")
        member.groups.add(created.json()["id"])
        self.assertTrue(member.has_perm("catalog.change_product"))
        self.assertTrue(member.has_perm("catalog.view_category"))

    def test_view_catalog_does_not_grant_change(self):
        self.client.force_authenticate(user=self.editor)
        created = self.client.post(
            "/api/accounts/groups/",
            {"name": "Витрина", "permissions": ["view_catalog"]},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        member = User.objects.create_user(username="reader", password="password")
        member.groups.add(created.json()["id"])
        self.assertTrue(member.has_perm("catalog.view_product"))
        self.assertFalse(member.has_perm("catalog.change_product"))

    def test_group_save_keeps_unrelated_permissions(self):
        order_view = Permission.objects.get(content_type__app_label="orders", codename="view_order")
        group = Group.objects.create(name="Смесь")
        group.permissions.add(order_view)
        self.client.force_authenticate(user=self.editor)
        updated = self.client.put(
            f"/api/accounts/groups/{group.id}/",
            {"name": "Смесь", "permissions": ["view_orders"]},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertTrue(group.permissions.filter(pk=order_view.pk).exists())

    def test_removing_edit_catalog_drops_change_product(self):
        self.client.force_authenticate(user=self.editor)
        created = self.client.post(
            "/api/accounts/groups/",
            {"name": "Каталог", "permissions": ["edit_catalog"]},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        group_id = created.json()["id"]
        updated = self.client.put(
            f"/api/accounts/groups/{group_id}/",
            {"name": "Каталог", "permissions": ["view_orders"]},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertFalse(
            Group.objects.get(pk=group_id).permissions.filter(
                content_type__app_label="catalog",
                codename="change_product",
            ).exists()
        )
