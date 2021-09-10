from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from dateutil.relativedelta import relativedelta, FR, SA
import datetime


class DjoUser(User):
    class Meta:
        proxy = True
        ordering = ["first_name", "last_name"]

    @staticmethod
    def is_begeleider(account_type):
        types = account_type.split(',')
        return 'begeleider' in types or 'aspirant_begeleider' in types

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"


class Presence(models.Model):

    class Meta:
        unique_together = ('user', 'date')
        indexes = [
            models.Index(fields=['date', 'pod']),
            models.Index(fields=['date', 'user']),
            models.Index(fields=['date', 'user', 'pod']),
            models.Index(fields=['date']),
        ]

    @staticmethod
    def get_available_slots(user=None):
        friday = Presence.next_friday()
        saturday = Presence.next_saturday()
        slots = [
            {
                "description": "Vrijdag (19:00 - 22:00)",
                "pod": "e",
                "name": 'fri',
                "date": friday,
                "closed": SpecialDate.is_closed(friday, 'e'),
                "available": Presence.slots_available(friday, 'e'),
                "taken": Presence.slots_taken(friday, 'e'),
                "tutor_count": Presence.objects.filter(date=friday, pod='e', user__is_superuser=True).count(),
                "tutors": list(Presence.objects.filter(date=friday, pod='e', user__is_superuser=True)
                               .values_list('user__first_name', flat=True)),
                "registered": Presence.objects.filter(user=user, date=friday, pod='e').count() > 0,
                "day_registered": Presence.objects.filter(user=user, date=friday).count() > 0
            },
            {
                "description": "Zaterdag (09:30 - 13:30)",
                "pod": "m",
                "name": 'sat',
                "date": saturday,
                "closed": SpecialDate.is_closed(saturday, 'm'),
                "available": Presence.slots_available(saturday, 'm'),
                "taken": Presence.slots_taken(saturday, 'm'),
                "tutor_count": Presence.objects.filter(date=saturday, pod='m', user__is_superuser=True).count(),
                "tutors": list(Presence.objects.filter(date=saturday, pod='m', user__is_superuser=True)
                               .values_list('user__first_name', flat=True)),
                "registered": Presence.objects.filter(user=user, date=saturday, pod='m').count() > 0,
                "day_registered": Presence.objects.filter(user=user, date=saturday).count() > 0
            },
            # {
            #     "description": "Zaterdag (13:30 - 17:00)",
            #     "pod": "a",
            #     "name": 'sat',
            #     "date": saturday,
            #     "closed": SpecialDate.is_closed(saturday, 'a'),
            #     "available": Presence.slots_available(saturday, 'a'),
            #     "taken": Presence.slots_taken(saturday, 'a'),
            #     "registered": Presence.objects.filter(user=user, date=saturday, pod='a').count() > 0,
            #     "day_registered": Presence.objects.filter(user=user, date=saturday).count() > 0
            # }
        ]
        return slots

    @staticmethod
    def last_friday():
        return datetime.date.today() + relativedelta(weekday=FR(-1))

    @staticmethod
    def last_saturday():
        return datetime.date.today() + relativedelta(weekday=SA(-1))

    @staticmethod
    def next_friday():
        return datetime.date.today() + relativedelta(weekday=FR)

    @staticmethod
    def next_saturday():
        return datetime.date.today() + relativedelta(weekday=SA)

    @staticmethod
    def slots_available(on_date, pod=None):
        try:
            special_date = SpecialDate.objects.get(date=on_date, pod=pod)
        except SpecialDate.DoesNotExist:
            try:
                special_date = SpecialDate.objects.get(date=on_date, pod=None)
            except SpecialDate.DoesNotExist:
                special_date = None

        slots_available = settings.SLOTS
        if special_date:
            slots_available = special_date.free_slots
            if special_date.closed:
                slots_available = 0

        return slots_available - Presence.slots_taken(on_date, pod)

    @staticmethod
    def slots_taken(on_date, pod=None):
        return Presence.objects.filter(date=on_date, pod=pod, user__is_superuser=False).count()

    def __str__(self):
        return f"{self.date}/{self.pod}: {self.user}"

    SEEN_BY_CHOICES = (
        ('mac', 'Mac Adres'),
        ('manual', 'Handmatig Aangemeld')
    )

    POD_CHOICES = (
        ('m', 'Ochtend'),
        ('a', 'Middag'),
        ('e', 'Avond'),
    )

    user = models.ForeignKey(DjoUser, models.CASCADE)
    date = models.DateField()
    pod = models.CharField(choices=POD_CHOICES, max_length=1, null=True)
    seen = models.BooleanField(default=False)
    seen_by = models.CharField(max_length=6, choices=SEEN_BY_CHOICES, default='manual', null=False)


class SpecialDate(models.Model):
    date = models.DateField()
    free_slots = models.IntegerField()
    pod = models.CharField(choices=Presence.POD_CHOICES, max_length=1, null=True, blank=True)
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
        verbose_name_plural = 'Mac Addresses'
        order_with_respect_to = 'user'

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}: {self.mac}"

    user = models.ForeignKey(DjoUser, models.CASCADE)
    mac = models.CharField(max_length=17, null=False, unique=True)
