from django.views.generic import View
from django.views.generic import TemplateView
from requests_oauthlib import OAuth2Session
from django.contrib.auth import logout, login as auth_login
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.conf import settings
import uuid
from .memberapi import MemberApi
from .mixins import PermissionRequiredMixin


class LoginView(View):
    def get(self, request, *args, **kwargs):
        oauth = OAuth2Session(client_id=settings.IDP_CLIENT_ID,
                              redirect_uri=settings.IDP_REDIRECT_URL,
                              scope=['user/basic', 'user/account-type', 'user/names', 'user/email'])
        auth_url, state = oauth.authorization_url(settings.IDP_AUTHORIZE_URL)
        return HttpResponseRedirect(auth_url)


class LoginResponseView(View):
    def get(self, request, *args, **kwargs):
        oauth = OAuth2Session(client_id=settings.IDP_CLIENT_ID,
                              redirect_uri=settings.IDP_REDIRECT_URL)
        full_response_url = request.build_absolute_uri()
        full_response_url = full_response_url.replace('http:', 'https:')
        try:
            access_token = oauth.fetch_token(settings.IDP_TOKEN_URL,
                                             authorization_response=full_response_url,
                                             client_secret=settings.IDP_CLIENT_SECRET)
        except Exception as e:
            # Something went wrong getting the token
            return HttpResponseForbidden('Geen toegang: {0}'.format(e))

        if 'access_token' in access_token and access_token['access_token'] != '':
            user_profile = oauth.get(settings.IDP_API_URL).json()
            username = "idp-{0}".format(user_profile['result']['id'])

            try:
                found_user = User.objects.get(username=username)
            except User.DoesNotExist:
                found_user = User()
                found_user.username = username
                found_user.password = uuid.uuid4()
                found_user.email = user_profile['result']['email']
                found_user.first_name = user_profile['result']['firstName']
                found_user.last_name = user_profile['result']['lastName']
                found_user.is_superuser = True
                found_user.save()

            auth_login(request, found_user)
            request.session['access_token'] = access_token
            request.session['profile'] = MemberApi.get_user_profile(user_profile['result']['backendID'], access_token['access_token'])
            print(request.session['profile'])

            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
        else:
            return HttpResponseForbidden('IDP Login mislukt')


class LogoffView(PermissionRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        logout(request)
        return HttpResponse(content='Uitgelogd')


class Main(TemplateView):
    template_name = 'main.html'
