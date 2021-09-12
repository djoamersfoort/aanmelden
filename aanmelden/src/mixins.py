from django.contrib.auth.mixins import UserPassesTestMixin
from django.http.response import HttpResponseForbidden
from django.conf import settings
from django.core.cache import cache
import requests


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
        introspection_token = cache.get('introspection_token')
        if not introspection_token:
            # No cached token found -> get a new one
            response = requests.post(settings.IDP_TOKEN_URL,
                                     headers={'Content-Type': 'application/x-www-form-urlencoded'},
                                     data=f'grant_type=client_credentials'
                                          f'&client_id={settings.INTROSPECTION_CLIENT_ID}'
                                          f'&client_secret={settings.INTROSPECTION_CLIENT_SECRET}'
                                          f'&scope=introspection')
            if not response.ok:
                # Failed to get an introspection token -> bail
                return False

            result = response.json()
            introspection_token = result["access_token"]
            cache.set('introspection_token', introspection_token, timeout=result['expires_in'])

        print(introspection_token)
        # We now have a token that allows us to call the introspection endpoint
        # Call it to verify the client_token we received
        response = requests.post(settings.IDP_INTROSPECTION_URL,
                                 headers={'Content-Type': 'application/x-www-form-urlencoded',
                                          'Authorization': f'Bearer {introspection_token}'},
                                 data={'token': client_token})
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

        if not self.validate_client_token(client_access_token):
            return HttpResponseForbidden()

        return super().dispatch(request, *args, **kwargs)
