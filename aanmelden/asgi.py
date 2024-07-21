"""
ASGI config for aanmelden project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from socketio import ASGIApp

from aanmelden.sockets import sio

# Only used in debug/devel mode
static_files = {
    "/static": "./aanmelden/static",
}

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aanmelden.settings")

application = ASGIApp(sio, get_asgi_application(), static_files=static_files)
