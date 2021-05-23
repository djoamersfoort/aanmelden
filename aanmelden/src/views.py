from django.views.generic import View, ListView, TemplateView
from django.views.generic.edit import CreateView
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from requests_oauthlib import OAuth2Session
from django.contrib.auth import logout, login as auth_login
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.conf import settings
from django.urls import reverse, reverse_lazy
from .mixins import BegeleiderRequiredMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Presence, DjoUser
from django.utils import timezone


@method_decorator(never_cache, name='dispatch')
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
                found_user = DjoUser.objects.get(username=username)
            except DjoUser.DoesNotExist:
                found_user = DjoUser()
                found_user.username = username
                found_user.set_unusable_password()

            found_user.email = user_profile['result']['email']
            found_user.first_name = user_profile['result']['firstName']
            found_user.last_name = user_profile['result']['lastName']
            account_type = user_profile['result']['accountType']
            found_user.is_superuser = DjoUser.is_begeleider(account_type)
            found_user.save()

            auth_login(request, found_user)

            if found_user.is_superuser:
                return HttpResponseRedirect(reverse('report'))
            else:
                return HttpResponseRedirect(reverse('main'))
        else:
            return HttpResponseForbidden('IDP Login mislukt')


class LogoffView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        logout(request)

        return HttpResponse("Je bent succesvol uitgelogd.")


@method_decorator(never_cache, name='dispatch')
class Main(LoginRequiredMixin, TemplateView):
    template_name = 'main.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'slots': Presence.get_available_slots(self.request.user),
            'total_slots': settings.SLOTS
        })
        return context


@method_decorator(never_cache, name='dispatch')
class Register(LoginRequiredMixin, TemplateView):
    template_name = 'registered.html'

    def get(self, request, *args, **kwargs):
        presence = Presence()
        if kwargs.get('day') == 'fri':
            registration_date = Presence.next_friday()
            last_week_date = Presence.last_friday()
        else:
            registration_date = Presence.next_saturday()
            last_week_date = Presence.last_saturday()
        presence.date = registration_date
        presence.pod = self.kwargs.get('pod')
        presence.user = request.user

        if Presence.slots_available(registration_date, presence.pod) <= 0:
            return HttpResponseRedirect(reverse('full', kwargs=kwargs))

        if Presence.objects.filter(user=request.user, date=last_week_date).count() > 0:
            # User was registered last week on the same day -> delay next if weekday < wednesday (2)
            if (registration_date - timezone.datetime.today().date()).days >= 3:
                return HttpResponseRedirect(reverse('try_again_later', kwargs=kwargs))

        try:
            presence.save()
        except IntegrityError as e:
            # Already registered -> ignore
            pass

        return super().get(request, args, kwargs)


@method_decorator(never_cache, name='dispatch')
class DeRegister(LoginRequiredMixin, TemplateView):
    template_name = 'deregistered.html'

    def get(self, request, *args, **kwargs):
        pod = kwargs.get('pod')
        if kwargs.get('day') == 'fri':
            registration_date = Presence.next_friday()
        else:
            registration_date = Presence.next_saturday()
        try:
            presence = Presence.objects.get(date=registration_date, user=self.request.user, pod=pod)
            if presence:
                presence.delete()
        except Presence.DoesNotExist:
            pass

        return super().get(request, args, kwargs)


class Full(LoginRequiredMixin, TemplateView):
    template_name = 'full.html'


class TryAgainLater(LoginRequiredMixin, TemplateView):
    template_name = 'try_again_later.html'


@method_decorator(never_cache, name='dispatch')
class Report(BegeleiderRequiredMixin, LoginRequiredMixin, ListView):
    template_name = 'report.html'
    model = Presence

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context.update({'slots': Presence.get_available_slots(self.request.user)})
        return context

    def get_queryset(self):
        fri = Presence.next_friday()
        sat = Presence.next_saturday()
        return Presence.objects.filter(Q(date=fri) | Q(date=sat))


class MarkAsSeen(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        pk = int(kwargs.get('pk'))
        seen = kwargs.get('seen')
        try:
            presence = Presence.objects.get(pk=pk)
            presence.seen = seen == 'true'
            presence.seen_by = 'manual'
            presence.save()
        except Presence.DoesNotExist:
            # Presence not found, who cares
            pass
        return HttpResponseRedirect(reverse('report'))


@method_decorator(never_cache, name='dispatch')
class RegisterManual(BegeleiderRequiredMixin, CreateView):
    template_name = 'register_manual.html'
    model = Presence
    fields = ['user']
    success_url = reverse_lazy('report')

    def form_valid(self, form):
        form.instance.pod = self.kwargs.get('pod')
        if self.kwargs.get('day') == 'fri':
            form.instance.date = Presence.next_friday()
        else:
            form.instance.date = Presence.next_saturday()
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except IntegrityError as e:
            # Already registered -> ignore
            return HttpResponseRedirect(reverse('report'))
