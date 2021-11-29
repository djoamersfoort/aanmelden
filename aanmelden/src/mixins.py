from django.contrib.auth.mixins import UserPassesTestMixin
from django.http.response import HttpResponseForbidden, HttpResponseNotFound
from django.conf import settings
from django.core.cache import cache
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
from .models import Slot


class BegeleiderRequiredMixin(UserPassesTestMixin):

    def test_func(self):
        return self.request.user.is_superuser


class ClientCredentialsRequiredMixin:
    whitelisted_client_ids = []

    @staticmethod
    def get_access_token(request) -> (str, None):
        token = request.GET.get('access_token', '').strip()
        if token == "":
            parts = request.headers.get('authorization', '').split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
        if token == "":
            return None
        return token

    def validate_client_token(self, client_token) -> bool:
        # Get a token with introspection scope
        client = BackendApplicationClient(client_id=settings.INTROSPECTION_CLIENT_ID, scope=["introspection"])
        oauth = OAuth2Session(client=client)
        introspection_token = cache.get('introspection_token')
        if not introspection_token:
            # No cached token found -> get a new one
            try:
                introspection_token = oauth.fetch_token(token_url=settings.IDP_TOKEN_URL,
                                                        client_secret=settings.INTROSPECTION_CLIENT_SECRET)
            except Exception as e:
                # Failed to get an introspection token -> bail
                print(e)
                return False

            cache.set('introspection_token', introspection_token, timeout=introspection_token['expires_in'])
        else:
            oauth.token = introspection_token

        # We now have a token that allows us to call the introspection endpoint
        # Call it to verify the client_token we received
        response = oauth.post(settings.IDP_INTROSPECTION_URL, data={'token': client_token})
        if not response.ok:
            # The token we verified was not valid
            return False

        result = response.json()
        if result['active'] and result['client_id'] in self.whitelisted_client_ids:
            return True

        return False

    def dispatch(self, request, *args, **kwargs):
        client_access_token = self.get_access_token(request)
        if not client_access_token:
            return HttpResponseForbidden()

        token_valid = cache.get(client_access_token)
        if token_valid is None:
            # No cached result found for this token, query IDP
            token_valid = self.validate_client_token(client_access_token)
            cache.set(client_access_token, token_valid, timeout=1800)

        if not token_valid:
            return HttpResponseForbidden()

        return super().dispatch(request, *args, **kwargs)


class SlotContextMixin:
    def __init__(self):
        self.slot = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'slot': self.slot
        })
        return context

    def dispatch(self, request, *args, **kwargs):
        day = self.kwargs.get('day')
        pod = self.kwargs.get('pod')
        self.slot = Slot.get(day, pod)

        if not self.slot:
            return HttpResponseNotFound("Slot with the specified parameters does not exist!")

        return super().dispatch(request, *args, **kwargs)
