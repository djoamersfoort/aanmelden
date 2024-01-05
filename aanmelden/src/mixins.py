import jwt
from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.cache import cache
from django.http.response import HttpResponseForbidden, HttpResponseNotFound
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

from aanmelden.src.models import Slot, DjoUser
from aanmelden.src.utils import get_access_token, get_openid_configuration, get_jwks_client


class BegeleiderRequiredMixin(UserPassesTestMixin):

    def test_func(self):
        return self.request.user.is_superuser


class ClientCredentialsRequiredMixin:
    whitelisted_client_ids = []

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
        client_access_token = get_access_token(request)
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


class AuthenticatedMixin:
    def dispatch(self, request, *args, **kwargs):
        token = get_access_token(request)
        if not token:
            return HttpResponseForbidden()

        openid_configuration = get_openid_configuration()
        jwks_client = get_jwks_client()

        signing_key = jwks_client.get_signing_key_from_jwt(token)
        decoded_jwt = jwt.decode(
            token,
            key=signing_key.key,
            algorithms=openid_configuration['id_token_signing_alg_values_supported'],
            options={'verify_aud': False}
        )
        if not decoded_jwt['aanmelden']:
            return HttpResponseForbidden()

        username = f"idp-{decoded_jwt['sub']}"
        try:
            user = DjoUser.objects.get(username=username)
        except DjoUser.DoesNotExist:
            user = DjoUser(username=username)
            user.set_unusable_password()

        user.email = decoded_jwt['email']
        user.first_name = decoded_jwt['given_name']
        user.last_name = decoded_jwt['family_name']
        user.is_superuser = user.is_begeleider(decoded_jwt['account_type'])
        user.userinfo.days = decoded_jwt['days']
        user.userinfo.account_type = decoded_jwt['account_type']
        if decoded_jwt['stripcard'] is not None:
            user.userinfo.stripcard_used = user['stripcard']['used']
            user.userinfo.stripcard_count = user['stripcard']['count']
        else:
            # No active stripcard -> reset counters
            user.userinfo.stripcard_used = 0
            user.userinfo.stripcard_count = 0

        user.save()

        request.user = user

        return super().dispatch(request, *args, **kwargs)
