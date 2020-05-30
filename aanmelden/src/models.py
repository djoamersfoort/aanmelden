from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import datetime


class DjoUser(User):
    class Meta:
        proxy = True

    @staticmethod
    def is_begeleider(account_type):
        types = account_type.split(',')
        print(types)
        return 'begeleider' in types or 'aspirant_begeleider' in types or 'ondersteuning' in types


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
        return settings.SLOTS - Presence.slots_taken(on_date)

    @staticmethod
    def slots_taken(on_date):
        return Presence.objects.filter(date=on_date).count()

    def __str__(self):
        return f"{self.date}: {self.user}"

    user = models.ForeignKey(DjoUser, models.CASCADE)
    date = models.DateField()
