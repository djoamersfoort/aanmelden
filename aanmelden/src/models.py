from django.db import models
from django.contrib.auth.models import User


class Presence(models.Model):
    user = models.OneToOneField(to=User, blank=False, null=False, on_delete=models.CASCADE)
    date = models.DateField()
