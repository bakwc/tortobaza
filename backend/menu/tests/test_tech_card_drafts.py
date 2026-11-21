from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.permissions import grant
from menu.models import TechCardDraft
from menu.tests.fixtures import MenuFixture


class TechCardDraftApiTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()
        self.client = APIClient()
        self.user = User.objects.create_user(username="menu", password="password")
        grant(self.user, "view_menu", "edit_menu")
        self.client.force_authenticate(user=self.user)

    def put_draft(self, client_id: str, updated_at: str, name: str, tech_card: int | None):
        return self.client.put(
            "/api/menu/tech-card-drafts/",
            {
                "client_id": client_id,
                "tech_card": tech_card,
                "client_updated_at": updated_at,
                "payload": {"name": name},
            },
            format="json",
        )

    def test_create_and_list(self):
        created = self.put_draft(
            "11111111-1111-1111-1111-111111111111",
            "2026-11-21T10:00:00Z",
            "Draft cake",
            self.menu.cake.id,
        )
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["name"], "Draft cake")
        self.assertEqual(created.json()["updated_by"], "menu")
        self.assertEqual(created.json()["tech_card"], self.menu.cake.id)
        new_card = self.put_draft(
            "22222222-2222-2222-2222-222222222222",
            "2026-11-21T10:05:00Z",
            "New cake",
            None,
        )
        self.assertEqual(new_card.status_code, 200)
        self.assertIsNone(new_card.json()["tech_card"])
        listed = self.client.get("/api/menu/tech-card-drafts/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(
            {row["name"] for row in listed.json()},
            {"Draft cake", "New cake"},
        )

    def test_newer_time_replaces(self):
        self.put_draft(
            "11111111-1111-1111-1111-111111111111",
            "2026-11-21T10:00:00Z",
            "First",
            self.menu.cake.id,
        )
        updated = self.put_draft(
            "11111111-1111-1111-1111-111111111111",
            "2026-11-21T11:00:00Z",
            "Second",
            self.menu.cake.id,
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(TechCardDraft.objects.get().name, "Second")

    def test_older_time_conflicts(self):
        self.put_draft(
            "11111111-1111-1111-1111-111111111111",
            "2026-11-21T10:00:00Z",
            "First",
            self.menu.cake.id,
        )
        conflict = self.put_draft(
            "11111111-1111-1111-1111-111111111111",
            "2026-11-21T09:00:00Z",
            "Older",
            self.menu.cake.id,
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["name"], "First")
        self.assertEqual(TechCardDraft.objects.get().name, "First")

    def test_other_client_id_replaces_same_card(self):
        self.put_draft(
            "11111111-1111-1111-1111-111111111111",
            "2026-11-21T10:00:00Z",
            "First",
            self.menu.cake.id,
        )
        replaced = self.put_draft(
            "33333333-3333-3333-3333-333333333333",
            "2026-11-21T12:00:00Z",
            "From other device",
            self.menu.cake.id,
        )
        self.assertEqual(replaced.status_code, 200)
        self.assertEqual(TechCardDraft.objects.count(), 1)
        self.assertEqual(
            str(TechCardDraft.objects.get().client_id),
            "33333333-3333-3333-3333-333333333333",
        )
        self.assertEqual(TechCardDraft.objects.get().name, "From other device")

    def test_delete_removes_draft_and_missing_is_empty(self):
        self.put_draft(
            "11111111-1111-1111-1111-111111111111",
            "2026-11-21T10:00:00Z",
            "Draft cake",
            self.menu.cake.id,
        )
        deleted = self.client.delete("/api/menu/tech-card-drafts/11111111-1111-1111-1111-111111111111/")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(TechCardDraft.objects.count(), 0)
        missing = self.client.delete("/api/menu/tech-card-drafts/44444444-4444-4444-4444-444444444444/")
        self.assertEqual(missing.status_code, 204)

    def test_view_can_list_and_edit_is_required_to_write(self):
        viewer = User.objects.create_user(username="viewer", password="password")
        grant(viewer, "view_menu")
        self.client.force_authenticate(user=viewer)
        denied = self.put_draft(
            "11111111-1111-1111-1111-111111111111",
            "2026-11-21T10:00:00Z",
            "Draft cake",
            self.menu.cake.id,
        )
        self.assertEqual(denied.status_code, 403)
        listed = self.client.get("/api/menu/tech-card-drafts/")
        self.assertEqual(listed.status_code, 200)
        stranger = User.objects.create_user(username="stranger", password="password")
        self.client.force_authenticate(user=stranger)
        self.assertEqual(self.client.get("/api/menu/tech-card-drafts/").status_code, 403)
