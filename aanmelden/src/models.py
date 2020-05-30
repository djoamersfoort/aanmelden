from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import datetime
import requests


class DjoUser(User):
    class Meta:
        proxy = True

    @staticmethod
    def is_begeleider(profile):
        types = profile['types'].split(',')
        print(types)
        return 'begeleider' in types or 'aspirant' in types or 'ondersteuning' in types

    @staticmethod
    def get_user_profile(userid, access_token):
        userid = userid.replace('u-', '')
        url = f'{settings.LEDEN_ADMIN_API_URL}/{userid}/'
        response = requests.get(url, headers={'Authorization': f'IDP {access_token}'})
        if not response.ok:
            raise ValueError(f"Unable to retrieve user profile: {response.content}")

        return response.json()


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
