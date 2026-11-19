from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.permissions import grant
from wishlist.models import WishlistItem


class WishlistApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.viewer = User.objects.create_user(username="wishlist-view", password="password")
        self.editor = User.objects.create_user(username="wishlist-edit", password="password")
        self.stranger = User.objects.create_user(username="wishlist-none", password="password")
        grant(self.viewer, "view_wishlist")
        grant(self.editor, "edit_wishlist")

    def test_forbidden_without_permission(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get("/api/wishlist/")
        self.assertEqual(response.status_code, 403)

    def test_list_sorted_by_priority(self):
        later = WishlistItem.objects.create(title="Телевизор", purpose="", priority=2, cost=Decimal("800"))
        first = WishlistItem.objects.create(
            title="Отопление",
            purpose="Для цеха",
            priority=1,
            cost=None,
        )
        same = WishlistItem.objects.create(title="Пленка", purpose="", priority=2, cost=Decimal("150.50"))
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get("/api/wishlist/")
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in response.json()]
        self.assertEqual(ids, [first.id, later.id, same.id])
        rows = {row["id"]: row for row in response.json()}
        self.assertIsNone(rows[first.id]["cost"])
        self.assertEqual(rows[same.id]["cost"], "150.50")

    def test_viewer_cannot_edit(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.post(
            "/api/wishlist/",
            {"title": "Телевизор", "purpose": "", "priority": 1, "cost": None},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_editor_creates_updates_deletes(self):
        self.client.force_authenticate(user=self.editor)
        created = self.client.post(
            "/api/wishlist/",
            {"title": "Телевизор", "purpose": "В цех", "priority": 3, "cost": "900.00"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        item_id = created.json()["id"]
        self.assertEqual(created.json()["title"], "Телевизор")
        self.assertEqual(created.json()["cost"], "900.00")
        updated = self.client.put(
            f"/api/wishlist/{item_id}/",
            {"title": "Телевизор 55", "purpose": "", "priority": 1, "cost": None},
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["title"], "Телевизор 55")
        self.assertEqual(updated.json()["priority"], 1)
        self.assertIsNone(updated.json()["cost"])
        deleted = self.client.delete(f"/api/wishlist/{item_id}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(WishlistItem.objects.filter(pk=item_id).exists())
