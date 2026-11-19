from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.permissions import grant
from wishlist.models import Idea


class IdeaApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.viewer = User.objects.create_user(username="idea-view", password="password")
        self.editor = User.objects.create_user(username="idea-edit", password="password")
        self.stranger = User.objects.create_user(username="idea-none", password="password")
        grant(self.viewer, "view_wishlist")
        grant(self.editor, "edit_wishlist")

    def test_forbidden_without_permission(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get("/api/wishlist/ideas/")
        self.assertEqual(response.status_code, 403)

    def test_list_sorted_by_status_then_priority(self):
        unknown_late = Idea.objects.create(
            priority=2,
            problem="",
            description="Позже",
            status=Idea.STATUS_UNKNOWN,
        )
        doing_low = Idea.objects.create(
            priority=5,
            problem="",
            description="Сейчас низкий",
            status=Idea.STATUS_DOING,
        )
        failed = Idea.objects.create(
            priority=1,
            problem="",
            description="Не взлетела",
            status=Idea.STATUS_FAILED,
        )
        doing_high = Idea.objects.create(
            priority=1,
            problem="",
            description="Сейчас",
            status=Idea.STATUS_DOING,
        )
        planned = Idea.objects.create(
            priority=1,
            problem="",
            description="Будем",
            status=Idea.STATUS_PLANNED,
        )
        rejected = Idea.objects.create(
            priority=1,
            problem="",
            description="Не будем",
            status=Idea.STATUS_REJECTED,
        )
        succeeded = Idea.objects.create(
            priority=1,
            problem="",
            description="Взлетела",
            status=Idea.STATUS_SUCCEEDED,
        )
        unknown_early = Idea.objects.create(
            priority=1,
            problem="",
            description="ХЗ",
            status=Idea.STATUS_UNKNOWN,
        )
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get("/api/wishlist/ideas/")
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in response.json()]
        self.assertEqual(
            ids,
            [
                doing_high.id,
                doing_low.id,
                planned.id,
                unknown_early.id,
                unknown_late.id,
                rejected.id,
                succeeded.id,
                failed.id,
            ],
        )

    def test_viewer_cannot_edit(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.post(
            "/api/wishlist/ideas/",
            {
                "priority": 1,
                "problem": "",
                "description": "Идея",
                "cost": None,
                "duration_seconds": None,
                "status": Idea.STATUS_UNKNOWN,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_editor_creates_updates_deletes(self):
        self.client.force_authenticate(user=self.editor)
        created = self.client.post(
            "/api/wishlist/ideas/",
            {
                "priority": 3,
                "problem": "Долго",
                "description": "Свой курьер",
                "cost": "900.00",
                "duration_seconds": 2 * 24 * 3600 + 5 * 3600,
                "status": Idea.STATUS_PLANNED,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        item_id = created.json()["id"]
        self.assertEqual(created.json()["description"], "Свой курьер")
        self.assertEqual(created.json()["cost"], "900.00")
        self.assertEqual(created.json()["duration_seconds"], 2 * 24 * 3600 + 5 * 3600)
        self.assertEqual(created.json()["status"], Idea.STATUS_PLANNED)
        updated = self.client.put(
            f"/api/wishlist/ideas/{item_id}/",
            {
                "priority": 1,
                "problem": "",
                "description": "Свой курьер",
                "cost": None,
                "duration_seconds": None,
                "status": Idea.STATUS_DOING,
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["priority"], 1)
        self.assertIsNone(updated.json()["cost"])
        self.assertIsNone(updated.json()["duration_seconds"])
        self.assertEqual(updated.json()["status"], Idea.STATUS_DOING)
        stored = Idea.objects.get(pk=item_id)
        self.assertIsNone(stored.duration)
        self.assertIsNone(stored.cost)
        deleted = self.client.delete(f"/api/wishlist/ideas/{item_id}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(Idea.objects.filter(pk=item_id).exists())

    def test_empty_cost_and_duration_round_trip(self):
        idea = Idea.objects.create(
            priority=1,
            problem="Очередь",
            description="Второе окно",
            cost=Decimal("150.50"),
            duration=timedelta(hours=5),
            status=Idea.STATUS_UNKNOWN,
        )
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get("/api/wishlist/ideas/")
        row = response.json()[0]
        self.assertEqual(row["id"], idea.id)
        self.assertEqual(row["cost"], "150.50")
        self.assertEqual(row["duration_seconds"], 5 * 3600)
        self.assertEqual(row["problem"], "Очередь")
