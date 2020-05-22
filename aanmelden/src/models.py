from django.db import models
from django.contrib.auth.models import User


class Presence(models.Model):
    user = models.OneToOneField(to=User, blank=False, null=False)
    date = models.DateField()
