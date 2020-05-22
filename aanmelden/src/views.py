from django.views.generic import View, ListView, TemplateView
from requests_oauthlib import OAuth2Session
from django.contrib.auth import logout, login as auth_login
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.conf import settings
import uuid
from .memberapi import MemberApi
from .mixins import PermissionRequiredMixin, BegeleiderRequiredMixin
from .models import Presence


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
            request.session['profile'] = MemberApi.get_user_profile(user_profile['result']['backendID'],
                                                                    access_token['access_token'])

            return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
        else:
            return HttpResponseForbidden('IDP Login mislukt')


class LogoffView(PermissionRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        logout(request)
        return HttpResponse(content='Uitgelogd')


class Main(PermissionRequiredMixin, TemplateView):
    template_name = 'main.html'

    def get(self, request, *args, **kwargs):
        fri = Presence.next_friday()
        sat = Presence.next_saturday()
        reg_fri = Presence.objects.filter(user=self.request.user, date=fri).count() > 0
        reg_sat = Presence.objects.filter(user=self.request.user, date=sat).count() > 0
        self.extra_context = {
            'fri_avail': Presence.slots_available(Presence.next_friday()),
            'sat_avail': Presence.slots_available(Presence.next_saturday()),
            'fri_taken': Presence.slots_taken(Presence.next_friday()),
            'sat_taken': Presence.slots_taken(Presence.next_saturday()),
            'reg_fri': reg_fri,
            'reg_sat': reg_sat,
            'fri': fri,
            'sat': sat
        }
        return super().get(request, args, kwargs)


class Register(PermissionRequiredMixin, TemplateView):
    template_name = 'registered.html'

    def get(self, request, *args, **kwargs):
        presence = Presence()
        if kwargs.get('day') == 'fri':
            registration_date = Presence.next_friday()
        else:
            registration_date = Presence.next_saturday()
        presence.date = registration_date
        presence.user = request.user
        try:
            presence.save()
        except IntegrityError:
            # Already registered -> ignore
            pass

        return super().get(request, args, kwargs)


class DeRegister(PermissionRequiredMixin, TemplateView):
    template_name = 'deregistered.html'

    def get(self, request, *args, **kwargs):
        if kwargs.get('day') == 'fri':
            registration_date = Presence.next_friday()
        else:
            registration_date = Presence.next_saturday()
        try:
            presence = Presence.objects.get(date=registration_date, user=self.request.user)
            if presence:
                presence.delete()
        except Presence.DoesNotExist:
            pass

        return super().get(request, args, kwargs)


class Report(BegeleiderRequiredMixin, ListView):
    template_name = 'report.html'
    model = Presence

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context['fri'] = Presence.next_friday()
        context['sat'] = Presence.next_saturday()
        return context

    def get_queryset(self):
        fri = Presence.next_friday()
        sat = Presence.next_saturday()
        return Presence.objects.filter(Q(date=fri) | Q(date=sat))
