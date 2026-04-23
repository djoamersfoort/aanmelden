import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from aanmelden.src.models import Slot, UserInfo, Presence

DjoUser = get_user_model()


class ViewsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a normal user
        self.user = DjoUser.objects.create_user(
            username="idp-1", email="user@example.com"
        )
        self.user_info = UserInfo.objects.create(
            user=self.user, days=3, account_type="lid"
        )

        # Create a superuser (begeleider)
        self.superuser = DjoUser.objects.create_superuser(
            username="idp-2", email="admin@example.com"
        )
        self.superuser_info = UserInfo.objects.create(
            user=self.superuser, days=7, account_type="begeleider"
        )

        # Create a slot for today
        today = datetime.date.today()
        # DAY_CHOICES = (('mon', 'Maandag'), ...)
        day_name = today.strftime("%a").lower()
        self.slot = Slot.objects.create(
            name=day_name, pod="m", description="Test Slot", enabled=True  # Ochtend
        )

    def test_main_view_requires_login(self):
        response = self.client.get(reverse("main"))
        self.assertEqual(response.status_code, 302)
        # Login URL usually has a next parameter
        self.assertIn(reverse("login"), response.url)

    def test_main_view_authenticated(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("main"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "main.html")
        self.assertIn("slots", response.context)

    def test_register_view(self):
        self.client.force_login(self.user)
        # Match URL pattern: register/day/<str:day>/<str:pod>
        response = self.client.get(
            reverse("register", kwargs={"day": self.slot.name, "pod": self.slot.pod})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registered.html")
        self.assertTrue(
            Presence.objects.filter(user=self.user, pod=self.slot.pod).exists()
        )

    def test_deregister_view(self):
        self.client.force_login(self.user)
        # First register
        Presence.objects.create(
            user=self.user, date=datetime.date.today(), pod=self.slot.pod
        )

        response = self.client.get(
            reverse("deregister", kwargs={"day": self.slot.name, "pod": self.slot.pod})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "deregistered.html")
        self.assertFalse(
            Presence.objects.filter(user=self.user, pod=self.slot.pod).exists()
        )

    def test_report_view_requires_begeleider(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("report"))
        self.assertEqual(
            response.status_code, 403
        )  # BegeleiderRequiredMixin returns Forbidden

    def test_report_view_begeleider(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("report"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "report.html")

    def test_calendar_view_begeleider(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("calendar"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "calendar.html")

    def test_mark_as_seen(self):
        self.client.force_login(self.superuser)
        presence = Presence.objects.create(
            user=self.user, date=datetime.date.today(), pod=self.slot.pod
        )

        # seen/int:pk/str:seen
        response = self.client.get(
            reverse("seen", kwargs={"pk": presence.pk, "seen": "true"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"ok": True})
        presence.refresh_from_db()
        self.assertTrue(presence.seen)

    def test_register_manual(self):
        self.client.force_login(self.superuser)
        # register-manual/<str:day>/<str:pod>
        # This is a CreateView for Presence, but it has custom post logic
        response = self.client.post(
            reverse(
                "register-manual", kwargs={"day": self.slot.name, "pod": self.slot.pod}
            ),
            {"user": self.user.pk},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Presence.objects.filter(user=self.user, pod=self.slot.pod).exists()
        )
