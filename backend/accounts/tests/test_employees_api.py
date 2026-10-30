from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile


class EmployeesApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.worker = User.objects.create_user(username="worker", password="password")
        self.staff = User.objects.create_user(username="staff", password="password", is_staff=True)
        self.finance = User.objects.create_user(username="finance", password="password")
        UserProfile.objects.create(user=self.finance, is_finance_admin=True, internal_name="Босс")

    def payload(self, password: str) -> dict:
        return {
            "username": "newhire",
            "password": password,
            "first_name": "Nino",
            "last_name": "Beridze",
            "email": "nino@example.com",
            "is_active": True,
            "is_staff": True,
            "hourly_rate": "12.50",
            "monthly_rate": "0.00",
            "can_login": True,
            "telegram_username": "nino",
            "internal_name": "Нино",
            "gender": "female",
            "is_finance_admin": False,
            "is_active_courier": True,
            "pushover_user": "pushover1",
            "position": "Кондитер",
            "in_schedule": True,
        }

    def test_unauthenticated_access_denied(self):
        response = self.client.get("/api/accounts/employees/")
        self.assertEqual(response.status_code, 403)

    def test_staff_without_finance_admin_denied(self):
        self.client.force_authenticate(user=self.staff)
        response = self.client.get("/api/accounts/employees/")
        self.assertEqual(response.status_code, 403)
        response = self.client.post("/api/accounts/employees/", self.payload("secret-pass"), format="json")
        self.assertEqual(response.status_code, 403)

    def test_create_requires_password(self):
        self.client.force_authenticate(user=self.finance)
        response = self.client.post("/api/accounts/employees/", self.payload(""), format="json")
        self.assertEqual(response.status_code, 400)

    def test_finance_admin_creates_and_updates_employee(self):
        self.client.force_authenticate(user=self.finance)
        created = self.client.post("/api/accounts/employees/", self.payload("secret-pass"), format="json")
        self.assertEqual(created.status_code, 201)
        body = created.json()
        self.assertNotIn("password", body)
        user_id = body.pop("id")
        self.assertEqual(
            body,
            {
                "username": "newhire",
                "first_name": "Nino",
                "last_name": "Beridze",
                "email": "nino@example.com",
                "is_active": True,
                "is_staff": True,
                "hourly_rate": "12.50",
                "monthly_rate": "0.00",
                "can_login": True,
                "telegram_username": "nino",
                "internal_name": "Нино",
                "gender": "female",
                "is_finance_admin": False,
                "is_active_courier": True,
                "pushover_user": "pushover1",
                "position": "Кондитер",
                "in_schedule": True,
            },
        )
        user = User.objects.get(pk=user_id)
        self.assertTrue(user.check_password("secret-pass"))

        updated_payload = self.payload("")
        updated_payload["hourly_rate"] = "15.00"
        updated_payload["monthly_rate"] = "800.00"
        updated_payload["is_finance_admin"] = True
        updated_payload["can_login"] = False
        updated_payload["is_active"] = False
        updated = self.client.put(f"/api/accounts/employees/{user_id}/", updated_payload, format="json")
        self.assertEqual(updated.status_code, 200)
        self.assertNotIn("password", updated.json())
        self.assertEqual(updated.json()["hourly_rate"], "15.00")
        self.assertEqual(updated.json()["monthly_rate"], "800.00")
        self.assertEqual(updated.json()["is_finance_admin"], True)
        self.assertEqual(updated.json()["can_login"], False)
        self.assertEqual(updated.json()["is_active"], False)
        user.refresh_from_db()
        self.assertTrue(user.check_password("secret-pass"))
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.hourly_rate, Decimal("15.00"))
        self.assertFalse(profile.can_login)
        self.assertEqual(profile.position, "Кондитер")
        self.assertTrue(profile.in_schedule)

    def test_blank_password_does_not_reset_user_without_profile(self):
        bare = User.objects.create_user(username="bare", password="password", first_name="A")
        self.client.force_authenticate(user=self.finance)
        listed = self.client.get("/api/accounts/employees/")
        self.assertEqual(listed.status_code, 200)
        row = next(item for item in listed.json() if item["username"] == "bare")
        self.assertEqual(row["hourly_rate"], "0.00")
        self.assertEqual(row["can_login"], True)
        self.assertEqual(row["is_finance_admin"], False)
        self.assertEqual(row["gender"], "female")
        self.assertEqual(row["position"], "")
        self.assertEqual(row["in_schedule"], False)
        self.assertNotIn("password", row)

        payload = self.payload("")
        payload["username"] = "bare"
        payload["first_name"] = "A"
        payload["hourly_rate"] = "5.00"
        updated = self.client.put(f"/api/accounts/employees/{bare.pk}/", payload, format="json")
        self.assertEqual(updated.status_code, 200)
        bare.refresh_from_db()
        self.assertTrue(bare.check_password("password"))
        profile = UserProfile.objects.get(user=bare)
        self.assertEqual(profile.hourly_rate, Decimal("5.00"))
        self.assertEqual(profile.internal_name, "Нино")
