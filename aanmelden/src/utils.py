import asyncio
from datetime import timedelta
from functools import lru_cache

import requests
from django.conf import settings
from django.db import IntegrityError
from jwt import PyJWKClient

from aanmelden.sockets import sio
from aanmelden.src.models import Presence, DjoUser


class RegisterException(Exception):
    pass


class NotEnoughSlotsException(RegisterException):
    pass


class TooManyDaysException(RegisterException):
    pass


class StripcardLimitReachedException(RegisterException):
    pass


class JochDetectedException(RegisterException):
    pass


def register(slot, user, skip_checks=False):
    if not skip_checks:
        if Presence.slots_available(slot.date, slot.pod) <= 0:
            raise NotEnoughSlotsException()

        date = slot.date
        start = date - timedelta(days=date.weekday())
        end = start + timedelta(days=6)

        reg_count = Presence.objects.filter(
            date__gte=start, date__lte=end, user=user
        ).count()

        if reg_count >= user.userinfo.days:
            raise TooManyDaysException()

        if DjoUser.has_strippenkaart(user.userinfo.account_type):
            if user.userinfo.stripcard_used >= user.userinfo.stripcard_count:
                raise StripcardLimitReachedException()

    presence = Presence()
    presence.date = slot.date
    presence.pod = slot.pod
    presence.user = user

    try:
        presence.save()
    except IntegrityError as e:
        # Already registered -> ignore
        pass

    asyncio.run(sio.emit("update_report_page"))
    asyncio.run(sio.emit("update_main_page"))

    return presence


def register_future(date, slot, user):
    if not user.is_superuser:
        raise JochDetectedException

    if date.weekday() != slot.date.weekday():
        raise JochDetectedException

    presence = Presence()
    presence.date = date
    presence.pod = slot.pod
    presence.user = user

    try:
        presence.save()
    except IntegrityError as e:
        # Already registered -> ignore
        pass

    # only update if register date is in current week
    date_start = slot.date - timedelta(days=slot.date.weekday())
    date_end = date_start + timedelta(days=6)

    if date >= date_start and date <= date_end:
        asyncio.run(sio.emit("update_report_page"))
        asyncio.run(sio.emit("update_main_page"))

    return presence


def mark_seen(pk, seen):
    try:
        presence = Presence.objects.get(pk=pk)
        presence.seen = seen == "true"
        presence.seen_by = "manual"
        presence.save()
    except Presence.DoesNotExist:
        # Presence not found, who cares
        pass

    asyncio.run(sio.emit("update_report_page"))


class DeRegisterException(Exception):
    pass


class AlreadySeenException(DeRegisterException):
    pass


def deregister(slot, user):
    try:
        presence = Presence.objects.get(date=slot.date, user=user, pod=slot.pod)
    except Presence.DoesNotExist:
        return

    if presence.seen:
        raise AlreadySeenException()
    else:
        presence.delete()

    asyncio.run(sio.emit("update_report_page"))
    asyncio.run(sio.emit("update_main_page"))


def deregister_future(date, slot, user):
    try:
        presence = Presence.objects.get(date=date, user=user, pod=slot.pod)
    except Presence.DoesNotExist:
        return

    presence.delete()

    # only update if deregister date is in current week
    date_start = slot.date - timedelta(days=slot.date.weekday())
    date_end = date_start + timedelta(days=6)

    if date >= date_start and date <= date_end:
        asyncio.run(sio.emit("update_report_page"))
        asyncio.run(sio.emit("update_main_page"))


@lru_cache()
def get_openid_configuration():
    return requests.get(settings.OPENID_CONFIGURATION, timeout=10).json()


@lru_cache()
def get_jwks_client():
    return PyJWKClient(uri=get_openid_configuration()["jwks_uri"])


def get_access_token(request) -> (str, None):
    token = request.GET.get("access_token", "").strip()
    if token == "":
        parts = request.headers.get("authorization", "").split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
    if token == "":
        return None
    return token
