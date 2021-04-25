from django.views.generic import View
from .models import Presence, MacAddress
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datetime import date


class FreeDay(View):
    def get(self, request, *args, **kwargs):
        day = self.kwargs.get('day')
        if day == 'fri':
            free = Presence.slots_available(Presence.next_friday(), pod='e')
        else:
            free = Presence.slots_available(Presence.next_saturday(), pod='m') + Presence.slots_available(
                Presence.next_saturday(), pod='a')
        return JsonResponse(data={"free": free})


class Free(View):
    def get(self, request, *args, **kwargs):
        fri = Presence.slots_available(Presence.next_friday(), pod='e')
        sat = Presence.slots_available(Presence.next_saturday(), pod='m') + Presence.slots_available(
            Presence.next_saturday(), pod='a')
        return JsonResponse({
            "friday": fri,
            "saturday": sat
        })


class FreeV2(View):
    def get(self, request, *args, **kwargs):
        slots = Presence.get_available_slots()
        for slot in slots:
            slot.pop('registered', None)
            slot.pop('day_registered', None)

        return JsonResponse(slots, safe=False)


@method_decorator(csrf_exempt, name='dispatch')
class MacEvent(View):
    def post(self, request, *args, **kwargs):
        body = request.body.decode('utf8')
        parts = body.split(' ')
        if len(parts) != 3:
            return HttpResponseBadRequest('Malformed body received')

        event_type = parts[0]
        mac = parts[1]

        if event_type != 'join':
            return HttpResponse('Ignored')
        if mac.count(':') < 5:
            return HttpResponseBadRequest('Malformed mac address received')

        # Get user that owns this MAC address
        try:
            mac_address = MacAddress.objects.get(mac=mac.lower())
        except MacAddress.DoesNotExist:
            return HttpResponse('Unknown MAC address')

        try:
            presence = Presence.objects.get(date=date.today(), user=mac_address.user)
            presence.seen = True
            presence.seen_by = 'mac'
            presence.save()
        except Presence.DoesNotExist:
            pass

        return HttpResponse('OK')
