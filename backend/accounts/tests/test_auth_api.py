from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import UserProfile


class AuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.worker = User.objects.create_user(username="worker", password="password")
        self.admin = User.objects.create_user(username="admin", password="password", is_staff=True)

    def test_me_returns_is_staff_false_for_worker(self):
        self.client.force_authenticate(user=self.worker)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["is_staff"], False)
        self.assertEqual(response.json()["is_finance_admin"], False)

    def test_me_returns_is_staff_true_for_staff(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["is_staff"], True)
        self.assertEqual(response.json()["is_finance_admin"], False)

    def test_me_returns_is_finance_admin_from_profile(self):
        UserProfile.objects.create(user=self.worker, is_finance_admin=True)
        self.client.force_authenticate(user=self.worker)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["is_finance_admin"], True)

    def test_login_denied_when_can_login_false(self):
        UserProfile.objects.create(user=self.worker, can_login=False)
        response = self.client.post(
            "/api/auth/login/",
            {"username": "worker", "password": "password"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["non_field_errors"], ["Invalid username or password."])
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 403)

    def test_existing_session_logged_out_when_can_login_false(self):
        UserProfile.objects.create(user=self.worker, can_login=True)
        self.assertTrue(self.client.login(username="worker", password="password"))
        profile = UserProfile.objects.get(user=self.worker)
        profile.can_login = False
        profile.save()
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 403)
