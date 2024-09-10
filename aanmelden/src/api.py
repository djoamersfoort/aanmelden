from datetime import date
from datetime import datetime
from json import loads

from django.conf import settings
from django.db.models import Value, F
from django.db.models.functions import Concat
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View

from aanmelden.src.mixins import (
    ClientCredentialsRequiredMixin,
    SlotContextMixin,
    AuthenticatedMixin,
)
from aanmelden.src.models import DjoUser
from aanmelden.src.models import Presence, MacAddress, Slot, DAY_NUMBERS
from aanmelden.src.utils import (
    register,
    register_future,
    deregister,
    deregister_future,
    NotEnoughSlotsException,
    TooManyDaysException,
    StripcardLimitReachedException,
    AlreadySeenException,
    mark_seen,
)


class FreeV2(View):
    def get(self, request, *args, **kwargs):
        slots = Slot.get_enabled_slots()
        for slot in slots:
            slot.pop("tutors", None)
            slot.pop("is_registered", None)

        return JsonResponse(slots, safe=False)


@method_decorator(csrf_exempt, name="dispatch")
class MacEvent(View):
    def post(self, request, *args, **kwargs):
        body = request.body.decode("utf8")
        parts = body.split(" ")
        if len(parts) != 3:
            return HttpResponseBadRequest("Malformed body received")

        event_type = parts[0]
        mac = parts[1]

        if event_type != "join":
            return HttpResponse("Ignored")
        if mac.count(":") < 5:
            return HttpResponseBadRequest("Malformed mac address received")

        # Get user that owns this MAC address
        try:
            mac_address = MacAddress.objects.get(mac=mac.lower())
        except MacAddress.DoesNotExist:
            return HttpResponse("Unknown MAC address")

        try:
            presence = Presence.objects.get(date=date.today(), user=mac_address.user)
            presence.seen = True
            presence.seen_by = "mac"
            presence.save()
        except Presence.DoesNotExist:
            pass

        return HttpResponse("OK")


@method_decorator(csrf_exempt, name="dispatch")
class IsPresentV2(ClientCredentialsRequiredMixin, SlotContextMixin, View):
    whitelisted_client_ids = settings.API_CLIENT_WHITELIST

    def post(self, request, *args, **kwargs):
        # Check if a user is present on a certain dow/pod (auth required)
        userid = self.kwargs.get("userid").strip()

        try:
            Presence.objects.get(
                date=self.slot.date, pod=self.slot.pod, user__username=userid, seen=True
            )
        except Presence.DoesNotExist:
            return JsonResponse({"present": False})
        return JsonResponse({"present": True})


@method_decorator(csrf_exempt, name="dispatch")
class ArePresentV2(ClientCredentialsRequiredMixin, SlotContextMixin, View):
    whitelisted_client_ids = settings.API_CLIENT_WHITELIST

    # Return a list of present user ids (IDP backend ids)
    def post(self, request, *args, **kwargs):
        presences = Presence.objects.filter(
            date=self.slot.date, pod=self.slot.pod, seen=True
        )
        present_members = [presence.user.username for presence in presences]
        return JsonResponse({"members": present_members})


class PresentSinceDate(View):
    def get(self, request, *args, **kwargs):
        userid = kwargs.get("userid")
        from_date = date(
            year=kwargs.get("year"), month=kwargs.get("month"), day=kwargs.get("day")
        )
        count = Presence.objects.filter(
            user__username=userid, date__gte=from_date, seen=True
        ).count()
        return JsonResponse({"count": count})


class Slots(AuthenticatedMixin, View):
    def get(self, request):
        slots = Slot.get_enabled_slots(request.user)
        if not self.request.user.is_superuser:
            return JsonResponse({"slots": slots})

        for slot in slots:
            slot["presence"] = list(
                Presence.objects.filter(
                    date=slot["date"], pod=slot["pod"], user__is_superuser=False
                )
                .values("id", "seen")
                .annotate(
                    name=Concat("user__first_name", Value(" "), "user__last_name"),
                    stripcard_used=F("user__userinfo__stripcard_used"),
                    stripcard_count=F("user__userinfo__stripcard_count"),
                )
            )

        members = list(
            DjoUser.objects.filter(is_active=True)
            .values("id")
            .annotate(
                name=Concat("first_name", Value(" "), "last_name"),
                stripcard_used=F("userinfo__stripcard_used"),
                stripcard_count=F("userinfo__stripcard_count"),
            )
        )

        registered_dates = list(
            request.user.presence_set.filter(date__gte=datetime.today())
            .order_by("date")
            .values_list("date", flat=True)
        )

        return JsonResponse(
            {"slots": slots, "members": members, "registered_dates": registered_dates}
        )


class MarkSeen(AuthenticatedMixin, View):
    def get(self, *args, **kwargs):
        if not self.request.user.is_superuser:
            return HttpResponse(status=403)

        pk = int(kwargs.get("pk"))
        seen = kwargs.get("seen")

        mark_seen(pk, seen)
        return JsonResponse({"ok": True})


class Register(AuthenticatedMixin, SlotContextMixin, View):
    def get(self, request, *args, **kwargs):
        future_date = kwargs.get("date")
        try:
            if future_date:
                register_future(parse_date(future_date), self.slot, request.user)
            else:
                register(self.slot, request.user, request.user.is_superuser)

        except NotEnoughSlotsException:
            return JsonResponse({"error": "Not enough slots available"}, status=400)
        except TooManyDaysException:
            return JsonResponse(
                {"error": "You can only register for one day"}, status=400
            )
        except StripcardLimitReachedException:
            return JsonResponse(
                {"error": "You have reached the limit on your strip card"}, status=400
            )

        return JsonResponse({"error": None})


class RegisterManual(AuthenticatedMixin, SlotContextMixin, View):
    def get(self, request, *args, **kwargs):
        if not self.request.user.is_superuser:
            return HttpResponse(status=403)

        user = DjoUser.objects.get(id=int(kwargs.get("pk")))
        register(self.slot, user, True)
        return JsonResponse({"ok": True})


class DeRegister(AuthenticatedMixin, SlotContextMixin, View):
    def get(self, request, *args, **kwargs):
        future_date = kwargs.get("date")
        try:
            if request.user.is_superuser and future_date:
                deregister_future(parse_date(future_date), self.slot, request.user)
            else:
                deregister(self.slot, request.user)

        except AlreadySeenException:
            return JsonResponse({"error": "Je bent al aanwezig"})

        return JsonResponse({"error": None})


@method_decorator(csrf_exempt, name="dispatch")
class FutureUpdate(AuthenticatedMixin, View):
    def patch(self, request, *args, **kwargs):
        if not self.request.user.is_superuser:
            return HttpResponse(status=403)

        body = loads(request.body.decode("utf8"))
        if "add" in body:
            for add in body["add"]:
                add_date = parse_date(add)
                register_future(
                    add_date,
                    Slot.objects.filter(
                        name=list(DAY_NUMBERS.keys())[
                            list(DAY_NUMBERS.values()).index(add_date.weekday())
                        ]
                    ).first(),
                    request.user,
                )

        if "remove" in body:
            for remove in body["remove"]:
                remove_date = parse_date(remove)
                deregister_future(
                    remove_date,
                    Slot.objects.filter(
                        name=list(DAY_NUMBERS.keys())[
                            list(DAY_NUMBERS.values()).index(remove_date.weekday())
                        ]
                    ).first(),
                    request.user,
                )

        return JsonResponse({"error": None})
