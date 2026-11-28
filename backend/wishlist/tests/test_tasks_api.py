from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.permissions import grant
from wishlist.models import Task


class TaskApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.viewer = User.objects.create_user(username="task-view", password="password")
        self.editor = User.objects.create_user(username="task-edit", password="password")
        self.stranger = User.objects.create_user(username="task-none", password="password")
        self.inactive = User.objects.create_user(username="task-gone", password="password", is_active=False)
        grant(self.viewer, "view_wishlist")
        grant(self.editor, "edit_wishlist")

    def body(self, **overrides):
        data = {
            "title": "Купить коробки",
            "description": "На склад",
            "status": Task.STATUS_TODO,
            "assignee": self.viewer.pk,
        }
        data.update(overrides)
        return data

    def test_forbidden_without_permission(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get("/api/wishlist/tasks/", {"hide_old_done": "false"})
        self.assertEqual(response.status_code, 403)

    def test_viewer_cannot_create(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.post("/api/wishlist/tasks/", self.body(), format="json")
        self.assertEqual(response.status_code, 403)

    def test_author_is_current_user(self):
        self.client.force_authenticate(user=self.editor)
        response = self.client.post("/api/wishlist/tasks/", self.body(), format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["author"], self.editor.pk)
        self.assertEqual(response.data["assignee"], self.viewer.pk)
        self.assertIsNone(response.data["completed_at"])

    def test_completed_at_set_and_cleared(self):
        self.client.force_authenticate(user=self.editor)
        created = self.client.post("/api/wishlist/tasks/", self.body(), format="json")
        pk = created.data["id"]
        done = self.client.put(f"/api/wishlist/tasks/{pk}/", self.body(status=Task.STATUS_DONE), format="json")
        self.assertEqual(done.status_code, 200)
        self.assertIsNotNone(done.data["completed_at"])
        back = self.client.put(
            f"/api/wishlist/tasks/{pk}/",
            self.body(status=Task.STATUS_IN_PROGRESS),
            format="json",
        )
        self.assertEqual(back.status_code, 200)
        self.assertIsNone(back.data["completed_at"])

    def test_hide_old_done(self):
        old = Task.objects.create(
            title="Старая",
            status=Task.STATUS_DONE,
            author=self.editor,
            assignee=self.viewer,
            completed_at=timezone.now() - timedelta(days=31),
        )
        recent = Task.objects.create(
            title="Свежая",
            status=Task.STATUS_DONE,
            author=self.editor,
            assignee=self.viewer,
            completed_at=timezone.now() - timedelta(days=29),
        )
        open_task = Task.objects.create(
            title="Открытая",
            status=Task.STATUS_TODO,
            author=self.editor,
            assignee=self.viewer,
        )
        self.client.force_authenticate(user=self.viewer)
        hidden = self.client.get("/api/wishlist/tasks/", {"hide_old_done": "true"})
        self.assertEqual(hidden.status_code, 200)
        hidden_ids = {row["id"] for row in hidden.data}
        self.assertNotIn(old.pk, hidden_ids)
        self.assertIn(recent.pk, hidden_ids)
        self.assertIn(open_task.pk, hidden_ids)
        shown = self.client.get("/api/wishlist/tasks/", {"hide_old_done": "false"})
        shown_ids = {row["id"] for row in shown.data}
        self.assertIn(old.pk, shown_ids)

    def test_hide_old_done_required(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get("/api/wishlist/tasks/")
        self.assertEqual(response.status_code, 400)

    def test_assignees_exclude_inactive(self):
        self.client.force_authenticate(user=self.viewer)
        response = self.client.get("/api/wishlist/tasks/assignees/")
        self.assertEqual(response.status_code, 200)
        ids = [row["id"] for row in response.data]
        self.assertIn(self.viewer.pk, ids)
        self.assertNotIn(self.inactive.pk, ids)
        self.client.force_authenticate(user=self.editor)
        created = self.client.post(
            "/api/wishlist/tasks/",
            self.body(assignee=self.inactive.pk),
            format="json",
        )
        self.assertEqual(created.status_code, 400)
