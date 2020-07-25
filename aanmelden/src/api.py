from django.views.generic import View
from .models import Presence
from django.http import JsonResponse


class FreeDay(View):
    def get(self, request, *args, **kwargs):
        day = self.kwargs.get('day')
        if day == 'fri':
            free = Presence.slots_available(Presence.next_friday())
        else:
            free = Presence.slots_available(Presence.next_saturday())
        return JsonResponse(data={"free": free})


class Free(View):
    def get(self, request, *args, **kwargs):
        fri = Presence.slots_available(Presence.next_friday())
        sat = Presence.slots_available(Presence.next_saturday())
        return JsonResponse({
            "friday": fri,
            "saturday": sat
        })
