from datetime import date

from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from .mixins import ClientCredentialsRequiredMixin, SlotContextMixin, AuthenticatedMixin
from .models import Presence, MacAddress, Slot
from .utils import register, deregister, NotEnoughSlotsException, TooManyDaysException, StripcardLimitReachedException, AlreadySeenException


class FreeV2(View):
    def get(self, request, *args, **kwargs):
        slots = Slot.get_enabled_slots()
        for slot in slots:
            slot.pop('tutors', None)
            slot.pop('is_registered', None)

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


@method_decorator(csrf_exempt, name='dispatch')
class IsPresentV2(ClientCredentialsRequiredMixin, SlotContextMixin, View):
    whitelisted_client_ids = settings.API_CLIENT_WHITELIST

    def post(self, request, *args, **kwargs):
        # Check if a user is present on a certain dow/pod (auth required)
        userid = self.kwargs.get('userid').strip()

        try:
            Presence.objects.get(date=self.slot.date, pod=self.slot.pod, user__username=userid, seen=True)
        except Presence.DoesNotExist:
            return JsonResponse({'present': False})
        return JsonResponse({'present': True})


@method_decorator(csrf_exempt, name='dispatch')
class ArePresentV2(ClientCredentialsRequiredMixin, SlotContextMixin, View):
    whitelisted_client_ids = settings.API_CLIENT_WHITELIST

    # Return a list of present user ids (IDP backend ids)
    def post(self, request, *args, **kwargs):
        presences = Presence.objects.filter(date=self.slot.date, pod=self.slot.pod, seen=True)
        present_members = [presence.user.username for presence in presences]
        return JsonResponse({'members': present_members})


class PresentSinceDate(View):
    def get(self, request, *args, **kwargs):
        userid = kwargs.get('userid')
        from_date = date(year=kwargs.get('year'), month=kwargs.get('month'), day=kwargs.get('day'))
        count = Presence.objects.filter(user__username=userid, date__gte=from_date, seen=True).count()
        return JsonResponse({'count': count})


class Slots(AuthenticatedMixin, View):
    def get(self, request):
        return JsonResponse({'slots': Slot.get_enabled_slots(request.user)})


class Register(AuthenticatedMixin, SlotContextMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            register(self.slot, request.user)
        except NotEnoughSlotsException:
            return JsonResponse({'error': 'Not enough slots available'}, status=400)
        except TooManyDaysException:
            return JsonResponse({'error': 'You can only register for one day'}, status=400)
        except StripcardLimitReachedException:
            return JsonResponse({'error': 'You have reached the limit on your strip card'}, status=400)

        return JsonResponse({"error": None})


class DeRegister(AuthenticatedMixin, SlotContextMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            deregister(self.slot, request.user)
        except AlreadySeenException:
            return JsonResponse({'error': 'Je bent al aanwezig'})

        return JsonResponse({'error': None})

