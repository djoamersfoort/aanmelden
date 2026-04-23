import datetime
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from aanmelden.src.models import Slot, UserInfo, Presence, MacAddress

DjoUser = get_user_model()


class ApiTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a normal user
        self.user = DjoUser.objects.create_user(
            username="idp-1",
            email="user@example.com",
            first_name="Test",
            last_name="User",
        )
        self.user_info = UserInfo.objects.create(
            user=self.user, days=3, account_type="lid"
        )

        # Create a superuser (begeleider)
        self.superuser = DjoUser.objects.create_superuser(
            username="idp-2",
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
        )
        self.superuser_info = UserInfo.objects.create(
            user=self.superuser, days=7, account_type="begeleider"
        )

        # Create a slot for today
        self.today = datetime.date.today()
        day_name = self.today.strftime("%a").lower()
        self.slot = Slot.objects.create(
            name=day_name, pod="m", description="Test Slot", enabled=True
        )

    def test_free_v2(self):
        response = self.client.get("/api/v2/free")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        if data:
            self.assertNotIn("tutors", data[0])
            self.assertNotIn("is_registered", data[0])

    def test_mac_event(self):
        MacAddress.objects.create(user=self.user, mac="aa:bb:cc:dd:ee:ff")
        Presence.objects.create(user=self.user, date=self.today, pod=self.slot.pod)

        # Malformed body
        response = self.client.post(
            "/api/v1/mac_event",
            data="join aa:bb:cc:dd:ee:ff",
            content_type="text/plain",
        )
        self.assertEqual(response.status_code, 400)

        # Valid join
        response = self.client.post(
            "/api/v1/mac_event",
            data="join aa:bb:cc:dd:ee:ff extra",
            content_type="text/plain",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "OK")

        presence = Presence.objects.get(user=self.user, date=self.today)
        self.assertTrue(presence.seen)
        self.assertEqual(presence.seen_by, "mac")

    def test_present_since_date(self):
        Presence.objects.create(
            user=self.user, date=self.today, pod=self.slot.pod, seen=True
        )
        path = f"/api/v1/present_since_date/{self.user.username}/{self.today.year}/{self.today.month}/{self.today.day}"
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    @patch("aanmelden.src.mixins.get_access_token")
    @patch("aanmelden.src.mixins.get_openid_configuration")
    @patch("aanmelden.src.mixins.get_jwks_client")
    @patch("jwt.decode")
    def test_api_with_auth_mixin(
        self, mock_jwt_decode, _mock_jwks, mock_openid, mock_get_token
    ):
        # Test an API view that uses AuthenticatedMixin
        mock_get_token.return_value = "fake-token"
        mock_openid.return_value = {"id_token_signing_alg_values_supported": ["RS256"]}
        mock_jwt_decode.return_value = {
            "aanmelden": True,
            "sub": "1",  # will become idp-1 which is self.user
            "email": "user@example.com",
            "given_name": "Test",
            "family_name": "User",
            "account_type": "lid",
            "days": 3,
            "stripcard": None,
        }

        # Test Slots API as superuser
        mock_jwt_decode.return_value = {
            "aanmelden": True,
            "sub": "2",  # will become idp-2 which is self.superuser
            "email": "admin@example.com",
            "given_name": "Admin",
            "family_name": "User",
            "account_type": "begeleider",
            "days": 7,
            "stripcard": None,
        }
        response = self.client.get("/api/v1/slots")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("slots", data)
        self.assertIn("members", data)

    @patch("aanmelden.src.mixins.get_access_token")
    @patch("aanmelden.src.mixins.get_openid_configuration")
    @patch("aanmelden.src.mixins.get_jwks_client")
    @patch("jwt.decode")
    def test_mark_seen_api(
        self, mock_jwt_decode, _mock_jwks, mock_openid, mock_get_token
    ):
        mock_get_token.return_value = "fake-token"
        mock_openid.return_value = {"id_token_signing_alg_values_supported": ["RS256"]}
        mock_jwt_decode.return_value = {
            "aanmelden": True,
            "sub": "2",
            "email": "admin@example.com",
            "given_name": "Admin",
            "family_name": "User",
            "account_type": "begeleider",
            "days": 7,
            "stripcard": None,
        }
        presence = Presence.objects.create(
            user=self.user, date=self.today, pod=self.slot.pod
        )

        path = f"/api/v1/seen/{presence.pk}/true"
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})
        presence.refresh_from_db()
        self.assertTrue(presence.seen)

    @patch("aanmelden.src.mixins.get_access_token")
    @patch("aanmelden.src.mixins.get_openid_configuration")
    @patch("aanmelden.src.mixins.get_jwks_client")
    @patch("jwt.decode")
    def test_register_manual_api(
        self, mock_jwt_decode, _mock_jwks, mock_openid, mock_get_token
    ):
        mock_get_token.return_value = "fake-token"
        mock_openid.return_value = {"id_token_signing_alg_values_supported": ["RS256"]}
        mock_jwt_decode.return_value = {
            "aanmelden": True,
            "sub": "2",
            "email": "admin@example.com",
            "given_name": "Admin",
            "family_name": "User",
            "account_type": "begeleider",
            "days": 7,
            "stripcard": None,
        }

        path = (
            f"/api/v1/register_manual/{self.slot.name}/{self.slot.pod}/{self.user.pk}"
        )
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Presence.objects.filter(user=self.user, pod=self.slot.pod).exists()
        )

    @patch("aanmelden.src.mixins.get_access_token")
    @patch("aanmelden.src.mixins.get_openid_configuration")
    @patch("aanmelden.src.mixins.get_jwks_client")
    @patch("jwt.decode")
    def test_future_update_api(
        self, mock_jwt_decode, _mock_jwks, mock_openid, mock_get_token
    ):
        mock_get_token.return_value = "fake-token"
        mock_openid.return_value = {"id_token_signing_alg_values_supported": ["RS256"]}
        mock_jwt_decode.return_value = {
            "aanmelden": True,
            "sub": "2",
            "email": "admin@example.com",
            "given_name": "Admin",
            "family_name": "User",
            "account_type": "begeleider",
            "days": 7,
            "stripcard": None,
        }

        tomorrow = self.today + datetime.timedelta(days=1)
        tomorrow_day_name = tomorrow.strftime("%a").lower()
        Slot.objects.create(
            name=tomorrow_day_name, pod="m", description="Tomorrow Slot", enabled=True
        )

        data = {"add": [tomorrow.isoformat()]}
        response = self.client.patch(
            "/api/v1/future", data=json.dumps(data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Presence.objects.filter(user=self.superuser, date=tomorrow).exists()
        )

        data = {"remove": [tomorrow.isoformat()]}
        response = self.client.patch(
            "/api/v1/future", data=json.dumps(data), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Presence.objects.filter(user=self.superuser, date=tomorrow).exists()
        )

    @patch("aanmelden.src.mixins.get_access_token")
    @patch("aanmelden.src.mixins.get_openid_configuration")
    @patch("aanmelden.src.mixins.get_jwks_client")
    @patch("jwt.decode")
    def test_register_api(
        self, mock_jwt_decode, _mock_jwks, mock_openid, mock_get_token
    ):
        mock_get_token.return_value = "fake-token"
        mock_openid.return_value = {"id_token_signing_alg_values_supported": ["RS256"]}
        mock_jwt_decode.return_value = {
            "aanmelden": True,
            "sub": "1",
            "email": "user@example.com",
            "given_name": "Test",
            "family_name": "User",
            "account_type": "lid",
            "days": 3,
            "stripcard": None,
        }

        # Test Register API
        path = f"/api/v1/register/{self.slot.name}/{self.slot.pod}"
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            Presence.objects.filter(user=self.user, pod=self.slot.pod).exists()
        )

    @patch("aanmelden.src.mixins.get_access_token")
    @patch("aanmelden.src.mixins.get_openid_configuration")
    @patch("aanmelden.src.mixins.get_jwks_client")
    @patch("jwt.decode")
    def test_deregister_api(
        self, mock_jwt_decode, _mock_jwks, mock_openid, mock_get_token
    ):
        mock_get_token.return_value = "fake-token"
        mock_openid.return_value = {"id_token_signing_alg_values_supported": ["RS256"]}
        mock_jwt_decode.return_value = {
            "aanmelden": True,
            "sub": "1",
            "email": "user@example.com",
            "given_name": "Test",
            "family_name": "User",
            "account_type": "lid",
            "days": 3,
            "stripcard": None,
        }
        Presence.objects.create(user=self.user, date=self.today, pod=self.slot.pod)

        # Test DeRegister API
        path = f"/api/v1/deregister/{self.slot.name}/{self.slot.pod}"
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Presence.objects.filter(user=self.user, pod=self.slot.pod).exists()
        )
