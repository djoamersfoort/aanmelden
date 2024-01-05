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


def register(slot, user):
    if not user.is_superuser:
        if Presence.slots_available(slot.date, slot.pod) <= 0:
            raise NotEnoughSlotsException()

        # Check if allowed to register for the number of days
        if slot.name == 'fri':
            # Reg for Friday, check saturday in the same weekend
            check_date = slot.date + timedelta(days=1)
        else:
            # Reg for Saturday, check Friday in the same weekend
            check_date = slot.date - timedelta(days=1)
        reg_count = Presence.objects.filter(date=check_date, user=user).count()
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


@lru_cache()
def get_openid_configuration():
    return requests.get(settings.OPENID_CONFIGURATION, timeout=10).json()


@lru_cache()
def get_jwks_client():
    return PyJWKClient(uri=get_openid_configuration()['jwks_uri'])


def get_access_token(request) -> (str, None):
    token = request.GET.get('access_token', '').strip()
    if token == "":
        parts = request.headers.get('authorization', '').split()
        if len(parts) == 2 and parts[0].lower() == 'bearer':
            token = parts[1]
    if token == "":
        return None
    return token
