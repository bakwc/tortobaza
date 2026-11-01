from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.permissions import grant
from inventory.models import FinishedProduction
from menu.tests.fixtures import MenuFixture


class FinishedProductionPermissionTests(TestCase):
    def setUp(self):
        self.menu = MenuFixture()
        self.client = APIClient()
        self.viewer = User.objects.create_user(username="viewer", password="password")
        self.owner = User.objects.create_user(username="owner", password="password")
        self.other = User.objects.create_user(username="other", password="password")
        self.full = User.objects.create_user(username="full", password="password")
        self.inventory = User.objects.create_user(username="inventory", password="password")
        grant(self.viewer, "view_finished")
        grant(self.owner, "edit_own_finished")
        grant(self.other, "edit_own_finished")
        grant(self.full, "edit_finished")
        grant(self.inventory, "edit_inventory")

    def payload(self, user):
        return {
            "date": "2026-10-02",
            "comment": "",
            "created_by": user.pk,
            "lines": [
                {
                    "tech_card": self.menu.bento.pk,
                    "weight_kg": None,
                    "modifiers": [],
                    "quantity": 1,
                }
            ],
        }

    def test_viewer_reads_and_cannot_write(self):
        document = FinishedProduction.objects.create(
            date=date(2026, 10, 2),
            comment="",
            created_by=self.owner,
        )
        self.client.force_authenticate(user=self.viewer)
        listed = self.client.get("/api/inventory/finished-productions/")
        self.assertEqual(listed.status_code, 200)
        read = self.client.get(f"/api/inventory/finished-productions/{document.pk}/")
        self.assertEqual(read.status_code, 200)
        created = self.client.post(
            "/api/inventory/finished-productions/",
            self.payload(self.viewer),
            format="json",
        )
        self.assertEqual(created.status_code, 403)
        updated = self.client.put(
            f"/api/inventory/finished-productions/{document.pk}/",
            self.payload(self.owner),
            format="json",
        )
        self.assertEqual(updated.status_code, 403)
        deleted = self.client.delete(f"/api/inventory/finished-productions/{document.pk}/")
        self.assertEqual(deleted.status_code, 403)

    def test_own_editor_creates_and_changes_only_own_documents(self):
        self.client.force_authenticate(user=self.owner)
        created = self.client.post(
            "/api/inventory/finished-productions/",
            self.payload(self.owner),
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(created.json()["created_by_id"], self.owner.pk)
        document_id = created.json()["id"]
        body = self.payload(self.owner)
        body["comment"] = "own"
        updated = self.client.put(
            f"/api/inventory/finished-productions/{document_id}/",
            body,
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        self.client.force_authenticate(user=self.other)
        foreign = self.client.put(
            f"/api/inventory/finished-productions/{document_id}/",
            body,
            format="json",
        )
        self.assertEqual(foreign.status_code, 403)
        deleted = self.client.delete(f"/api/inventory/finished-productions/{document_id}/")
        self.assertEqual(deleted.status_code, 403)
        self.client.force_authenticate(user=self.owner)
        removed = self.client.delete(f"/api/inventory/finished-productions/{document_id}/")
        self.assertEqual(removed.status_code, 204)

    def test_own_editor_cannot_change_document_without_author(self):
        document = FinishedProduction.objects.create(date=date(2026, 10, 2), comment="", created_by=None)
        self.client.force_authenticate(user=self.owner)
        updated = self.client.put(
            f"/api/inventory/finished-productions/{document.pk}/",
            self.payload(self.owner),
            format="json",
        )
        self.assertEqual(updated.status_code, 403)

    def test_full_editor_changes_another_document(self):
        self.client.force_authenticate(user=self.owner)
        created = self.client.post(
            "/api/inventory/finished-productions/",
            self.payload(self.owner),
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        document_id = created.json()["id"]
        self.client.force_authenticate(user=self.full)
        body = self.payload(self.owner)
        body["comment"] = "all"
        updated = self.client.put(
            f"/api/inventory/finished-productions/{document_id}/",
            body,
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        deleted = self.client.delete(f"/api/inventory/finished-productions/{document_id}/")
        self.assertEqual(deleted.status_code, 204)

    def test_inventory_edit_does_not_open_finished_productions(self):
        self.client.force_authenticate(user=self.inventory)
        created = self.client.post(
            "/api/inventory/finished-productions/",
            self.payload(self.inventory),
            format="json",
        )
        self.assertEqual(created.status_code, 403)

    def test_own_editor_can_read_tech_cards(self):
        self.client.force_authenticate(user=self.owner)
        listed = self.client.get("/api/menu/tech-cards/")
        self.assertEqual(listed.status_code, 200)
