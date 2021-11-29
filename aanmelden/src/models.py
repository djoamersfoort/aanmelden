from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.forms.models import model_to_dict
import datetime

POD_CHOICES = (
    ('m', 'Ochtend'),
    ('a', 'Middag'),
    ('e', 'Avond'),
)

DAY_CHOICES = (
    ('fri', 'Vrijdag'),
    ('sat', 'Zaterdag')
)


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


class UserInfo(models.Model):
    user: DjoUser = models.OneToOneField(User, on_delete=models.CASCADE)
    days = models.IntegerField(default=1, null=False)
    age = models.IntegerField(default=0, null=False)

    def __str__(self):
        return f"User details for {self.user.first_name} {self.user.last_name}"


class Slot(models.Model):
    class Meta:
        unique_together = ['name', 'pod']

    name = models.CharField(max_length=3, choices=DAY_CHOICES)
    pod = models.CharField(choices=POD_CHOICES, max_length=1)
    description = models.CharField(max_length=255)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name}-{self.pod}: {self.description}"

    @property
    def date(self):
        day_numbers = {
            'fri': 4,
            'sat': 5,
        }

        today = datetime.date.today()
        return today + datetime.timedelta((day_numbers[self.name] - today.weekday()) % 7)

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
        return list(Presence.objects.filter(date=self.date, pod=self.pod, user__is_superuser=True)
                    .values_list('user__first_name', flat=True))

    def is_registered(self, user):
        return Presence.objects.filter(user=user, date=self.date, pod=self.pod).count() > 0

    @staticmethod
    def get_enabled_slots(user=None):
        slots = Slot.objects.filter(enabled=True)
        available_slots = []
        for slot in slots:
            available_slot = model_to_dict(slot)
            available_slot.pop('id')
            for field in ['date', 'taken', 'available', 'closed', 'tutor_count', 'tutors']:
                available_slot[field] = slot.__getattribute__(field)
            if user:
                available_slot['is_registered'] = slot.is_registered(user)
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
        unique_together = ('user', 'date', 'pod')
        indexes = [
            models.Index(fields=['date', 'pod']),
            models.Index(fields=['date', 'user']),
            models.Index(fields=['date', 'user', 'pod']),
            models.Index(fields=['date']),
        ]

    # @staticmethod
    # def next_friday():
    #     today = datetime.date.today()
    #     return today + datetime.timedelta((4 - today.weekday()) % 7)
    #
    # @staticmethod
    # def next_saturday():
    #     today = datetime.date.today()
    #     return today + datetime.timedelta((5 - today.weekday()) % 7)

    @staticmethod
    def get_tutor_count(date, pod=None):
        if pod:
            return Presence.objects.filter(date=date, pod=pod, user__is_superuser=True).count()
        else:
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
        if special_date:
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
        return Presence.objects.filter(date=on_date, pod=pod, user__is_superuser=False).count()

    def __str__(self):
        return f"{self.date}/{self.pod}: {self.user}"

    SEEN_BY_CHOICES = (
        ('mac', 'Mac Adres'),
        ('manual', 'Handmatig Aangemeld')
    )

    user = models.ForeignKey(DjoUser, models.CASCADE)
    date = models.DateField()
    pod = models.CharField(choices=POD_CHOICES, max_length=1, null=True)
    seen = models.BooleanField(default=False)
    seen_by = models.CharField(max_length=6, choices=SEEN_BY_CHOICES, default='manual', null=False)


class SpecialDate(models.Model):
    date = models.DateField()
    free_slots = models.IntegerField()
    pod = models.CharField(choices=POD_CHOICES, max_length=1, null=True, blank=True)
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
