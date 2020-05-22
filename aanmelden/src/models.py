from django.db import models
from django.contrib.auth.models import User
import datetime


class Presence(models.Model):

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
        return 16 - Presence.slots_taken(on_date)

    @staticmethod
    def slots_taken(on_date):
        return Presence.objects.filter(date=on_date).count()

    user = models.OneToOneField(to=User, blank=False, null=False, on_delete=models.CASCADE)
    date = models.DateField()
