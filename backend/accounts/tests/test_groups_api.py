from django.contrib.auth.models import User
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
