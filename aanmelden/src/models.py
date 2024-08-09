import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.forms.models import model_to_dict
from django.utils import timezone

DAY_NUMBERS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

POD_CHOICES = (
    ("m", "Ochtend"),
    ("a", "Middag"),
    ("e", "Avond"),
)

DAY_CHOICES = (
    ("mon", "Maandag"),
    ("tue", "Dinsdag"),
    ("wed", "Woensdag"),
    ("thu", "Donderdag"),
    ("fri", "Vrijdag"),
    ("sat", "Zaterdag"),
    ("sun", "Zondag"),
)

DjangoUser = get_user_model()


class DjoUser(DjangoUser):
    class Meta:
        proxy = True
        ordering = ["first_name", "last_name"]

    @staticmethod
    def is_begeleider(account_type):
        types = account_type.split(",")
        return (
            "begeleider" in types
            or "aspirant_begeleider" in types
            or "ondersteuning" in types
        )

    @staticmethod
    def has_strippenkaart(account_type):
        types = account_type.split(",")
        return "strippenkaart" in types

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"


class UserInfo(models.Model):
    user: DjoUser = models.OneToOneField(get_user_model(), on_delete=models.CASCADE)
    days = models.IntegerField(default=1, null=False)
    account_type = models.CharField(max_length=100, default="", null=False)
    stripcard_used = models.IntegerField(default=0, null=False)
    stripcard_count = models.IntegerField(default=0, null=False)
    stripcard_expires = models.DateField(
        default=timezone.datetime(year=2099, month=1, day=1).date(), null=False
    )

    def __str__(self):
        return f"User details for {self.user}"


class Slot(models.Model):
    class Meta:
        unique_together = ["name", "pod"]

    name = models.CharField(max_length=3, choices=DAY_CHOICES)
    pod = models.CharField(choices=POD_CHOICES, max_length=1)
    description = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name}-{self.pod}: {self.description}"

    @property
    def date(self):
        today = datetime.date.today()
        return today + datetime.timedelta(
            (DAY_NUMBERS[self.name] - today.weekday()) % 7
        )

    @property
    def closed(self):
        return SpecialDate.is_closed(self.date, self.pod)

    @property
    def available(self):
        return Presence.slots_available(self.date, self.pod)

    @property
    def taken(self):
        return Presence.slots_taken(self.date, self.pod)

    @property
    def tutor_count(self):
        return Presence.get_tutor_count(self.date, self.pod)

    @property
    def tutors(self):
        return list(
            Presence.objects.filter(
                date=self.date, pod=self.pod, user__is_superuser=True
            ).values_list("user__first_name", flat=True)
        )

    @property
    def announcement(self):
        try:
            special_date = SpecialDate.objects.get(date=self.date, pod=self.pod)
        except SpecialDate.DoesNotExist:
            return ""
        return special_date.announcement

    def is_registered(self, user):
        return (
            Presence.objects.filter(user=user, date=self.date, pod=self.pod).count() > 0
        )

    @staticmethod
    def get_enabled_slots(user=None):
        slots = Slot.objects.filter(enabled=True)
        available_slots = []
        for slot in slots:
            available_slot = model_to_dict(slot)
            available_slot.pop("id")
            for field in [
                "date",
                "taken",
                "available",
                "closed",
                "tutor_count",
                "tutors",
                "announcement",
            ]:
                available_slot[field] = getattr(slot, field)
            if user:
                available_slot["is_registered"] = slot.is_registered(user)
            available_slots.append(available_slot)
        return available_slots

    @staticmethod
    def get(day: str, pod: str):
        try:
            slot = Slot.objects.get(name=day, pod=pod)
        except Slot.DoesNotExist:
            slot = None
        return slot


class Presence(models.Model):
    class Meta:
        unique_together = ("user", "date", "pod")
        indexes = [
            models.Index(fields=["date", "pod"]),
            models.Index(fields=["date", "user"]),
            models.Index(fields=["date", "user", "pod"]),
            models.Index(fields=["date"]),
        ]

    @staticmethod
    def get_tutor_count(date, pod=None):
        if pod:
            return Presence.objects.filter(
                date=date, pod=pod, user__is_superuser=True
            ).count()
        return Presence.objects.filter(date=date, user__is_superuser=True).count()

    @staticmethod
    def slots_available(on_date, pod=None):
        try:
            special_date = SpecialDate.objects.get(date=on_date, pod=pod)
        except SpecialDate.DoesNotExist:
            try:
                special_date = SpecialDate.objects.get(date=on_date, pod=None)
            except SpecialDate.DoesNotExist:
                special_date = None

        slots_available = 0
        if special_date and special_date.free_slots >= 0:
            slots_available = special_date.free_slots
            if special_date.closed:
                slots_available = 0
        else:
            # Add more slots depending on nr of tutors
            tutor_count = Presence.get_tutor_count(on_date, pod)
            for amount, extra in settings.SLOT_LEVELS.items():
                if tutor_count >= amount:
                    slots_available += extra

        return slots_available - Presence.slots_taken(on_date, pod)

    @staticmethod
    def slots_taken(on_date, pod=None):
        return Presence.objects.filter(
            date=on_date, pod=pod, user__is_superuser=False
        ).count()

    def __str__(self):
        return f"{self.date}/{self.pod}: {self.user}"

    SEEN_BY_CHOICES = (("mac", "Mac Adres"), ("manual", "Handmatig Aangemeld"))

    user = models.ForeignKey(DjoUser, models.CASCADE)
    date = models.DateField()
    pod = models.CharField(choices=POD_CHOICES, max_length=1, null=True)
    seen = models.BooleanField(default=False)
    seen_by = models.CharField(
        max_length=6, choices=SEEN_BY_CHOICES, default="manual", null=False
    )


class SpecialDate(models.Model):
    date = models.DateField()
    free_slots = models.IntegerField()
    pod = models.CharField(choices=POD_CHOICES, max_length=1, null=True, blank=True)
    announcement = models.TextField(null=True, blank=True)
    closed = models.BooleanField()

    @staticmethod
    def is_closed(on_date, pod=None):
        try:
            special_date = SpecialDate.objects.get(date=on_date, pod=pod)
        except SpecialDate.DoesNotExist:
            try:
                special_date = SpecialDate.objects.get(date=on_date, pod=None)
            except SpecialDate.DoesNotExist:
                special_date = None

        closed = False
        if special_date:
            closed = special_date.closed

        return closed

    def __str__(self):
        return f"{self.date}, Pod: {self.pod}, Slots: {self.free_slots}, Closed: {self.closed}"


class MacAddress(models.Model):
    class Meta:
        verbose_name_plural = "Mac Addresses"
        order_with_respect_to = "user"

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}: {self.mac}"

    user = models.ForeignKey(DjoUser, models.CASCADE)
    mac = models.CharField(max_length=17, null=False, unique=True)
