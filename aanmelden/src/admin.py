from django.contrib import admin
from .models import Presence, SpecialDate, MacAddress

admin.site.register(Presence)
admin.site.register(SpecialDate)
admin.site.register(MacAddress)
