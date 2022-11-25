from django.contrib import admin
from .models import Presence, SpecialDate, MacAddress, UserInfo, User, Slot
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin


@admin.register(Presence)
class PresenceAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    list_filter = ('user',)


# Define an inline admin descriptor for User model
# which acts a bit like a singleton
class UserInfoInline(admin.StackedInline):
    model = UserInfo
    can_delete = False
    verbose_name_plural = 'User info'


# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (UserInfoInline,)


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.register(UserInfo)
admin.site.register(SpecialDate)
admin.site.register(MacAddress)
admin.site.register(Slot)
