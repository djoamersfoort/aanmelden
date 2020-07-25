from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import datetime


class DjoUser(User):
    class Meta:
        proxy = True
        ordering = ["first_name", "last_name"]

    @staticmethod
    def is_begeleider(account_type):
        types = account_type.split(',')
        return 'begeleider' in types or 'aspirant_begeleider' in types or 'ondersteuning' in types

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"


class Presence(models.Model):

    class Meta:
        unique_together = ('user', 'date')

    @staticmethod
    def next_friday():
        today = datetime.date.today()
        return today + datetime.timedelta((4 - today.weekday()) % 7)

    @staticmethod
    def next_saturday():
        today = datetime.date.today()
        return today + datetime.timedelta((5 - today.weekday()) % 7)

    @staticmethod
    def slots_available(on_date):
        slots_available = settings.SLOTS
        try:
            special_date = SpecialDate.objects.get(date=on_date)
            slots_available = special_date.free_slots
            if special_date.closed:
                slots_available = 0
        except SpecialDate.DoesNotExist:
            pass

        return slots_available - Presence.slots_taken(on_date)

    @staticmethod
    def slots_taken(on_date):
        return Presence.objects.filter(date=on_date).count()

    def __str__(self):
        return f"{self.date}: {self.user}"

    user = models.ForeignKey(DjoUser, models.CASCADE)
    date = models.DateField()
    seen = models.BooleanField(default=False)


class SpecialDate(models.Model):
    date = models.DateField()
    free_slots = models.IntegerField()
    closed = models.BooleanField()

    @staticmethod
    def is_closed(on_date):
        try:
            special_date = SpecialDate.objects.get(date=on_date)
            closed = special_date.closed
        except SpecialDate.DoesNotExist:
            closed = False

        return closed

    def __str__(self):
        return f"{self.date}, Slots: {self.free_slots}, Closed: {self.closed}"
