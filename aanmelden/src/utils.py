import asyncio
from datetime import timedelta

import requests
from django.db import IntegrityError
from jwt import PyJWKClient

from aanmelden import settings
from aanmelden.sockets import sio
from .models import Presence, DjoUser

openid_configuration = None
jwks_client = None


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



def get_openid_configuration():
    global openid_configuration
    if openid_configuration is None:
        openid_configuration = requests.get(settings.OPENID_CONFIGURATION).json()

    return openid_configuration


def get_jwks_client():
    global jwks_client
    if jwks_client is None:
        jwks_client = PyJWKClient(uri=get_openid_configuration()['jwks_uri'])

    return jwks_client


def get_access_token(request) -> (str, None):
    token = request.GET.get('access_token', '').strip()
    if token == "":
        parts = request.headers.get('authorization', '').split()
        if len(parts) == 2 and parts[0].lower() == 'bearer':
            token = parts[1]
    if token == "":
        return None
    return token
