from django.contrib import admin
from .models import Presence, SpecialDate, MacAddress


@admin.register(Presence)
class PresenceAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    list_filter = ('user',)


admin.site.register(SpecialDate)
admin.site.register(MacAddress)
