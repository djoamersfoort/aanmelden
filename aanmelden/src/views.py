import asyncio

from django.conf import settings
from django.contrib.auth import logout, login as auth_login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from django.http import HttpResponseRedirect, HttpResponseForbidden, JsonResponse
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic import View, ListView, TemplateView
from django.views.generic.edit import CreateView
from requests_oauthlib import OAuth2Session

from aanmelden.sockets import sio
from aanmelden.src.mixins import BegeleiderRequiredMixin, SlotContextMixin
from aanmelden.src.models import Presence, DjoUser, UserInfo, Slot
from aanmelden.src.utils import (register, deregister, NotEnoughSlotsException, TooManyDaysException,
                                 StripcardLimitReachedException, AlreadySeenException, mark_seen)


@method_decorator(never_cache, name='dispatch')
class LoginView(View):
    def get(self, request, *args, **kwargs):
        oauth = OAuth2Session(client_id=settings.IDP_CLIENT_ID,
                              redirect_uri=settings.IDP_REDIRECT_URL,
                              scope=settings.IDP_API_SCOPES)
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
        except Exception:
            # Something went wrong getting the token
            return HttpResponseForbidden(f'Geen toegang!')

        if 'access_token' in access_token and access_token['access_token'] != '':
            user_profile = oauth.get(settings.IDP_API_URL).json()
            username = "idp-{0}".format(user_profile['id'])

            try:
                found_user = DjoUser.objects.get(username=username)
            except DjoUser.DoesNotExist:
                found_user = DjoUser()
                found_user.username = username
                found_user.set_unusable_password()

            if not hasattr(found_user, 'userinfo'):
                found_user.userinfo = UserInfo()
            found_user.email = user_profile['email']
            found_user.first_name = user_profile['firstName']
            found_user.last_name = user_profile['lastName']
            account_type = user_profile['accountType']
            found_user.is_superuser = DjoUser.is_begeleider(account_type)
            found_user.userinfo.days = user_profile['days']
            found_user.userinfo.account_type = account_type
            if "stripcard_used" in user_profile:
                found_user.userinfo.stripcard_used = user_profile['stripcard_used']
                found_user.userinfo.stripcard_count = user_profile['stripcard_count']
            else:
                # No active stripcard -> reset counters
                found_user.userinfo.stripcard_used = 0
                found_user.userinfo.stripcard_count = 0
            found_user.save()
            found_user.userinfo.save()

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

        return HttpResponseRedirect(settings.IDP_LOGOUT_URL)


@method_decorator(never_cache, name='dispatch')
class Main(LoginRequiredMixin, TemplateView):
    template_name = 'main.html'

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context.update({'slots': Slot.get_enabled_slots(self.request.user)})
        return context


@method_decorator(never_cache, name='dispatch')
class Register(LoginRequiredMixin, SlotContextMixin, TemplateView):
    template_name = 'registered.html'

    def get(self, request, *args, **kwargs):
        try:
            register(self.slot, request.user)
        except NotEnoughSlotsException:
            return HttpResponseRedirect(reverse('full', kwargs=kwargs))
        except TooManyDaysException:
            return HttpResponseRedirect(reverse('only_once'))
        except StripcardLimitReachedException:
            return HttpResponseRedirect(reverse('stripcard_full'))

        return super().get(request, *args, **kwargs)


@method_decorator(never_cache, name='dispatch')
class DeRegister(LoginRequiredMixin, SlotContextMixin, TemplateView):
    template_name = 'deregistered.html'

    def get(self, request, *args, **kwargs):
        try:
            deregister(self.slot, self.request.user)
        except AlreadySeenException:
            self.template_name = "already_seen.html"

        return super().get(request, args, kwargs)


class Full(LoginRequiredMixin, SlotContextMixin, TemplateView):
    template_name = 'full.html'


class OnlyOnce(LoginRequiredMixin, TemplateView):
    template_name = 'only_once.html'


class StripcardFull(LoginRequiredMixin, TemplateView):
    template_name = 'stripcard_full.html'


@method_decorator(never_cache, name='dispatch')
class Report(BegeleiderRequiredMixin, LoginRequiredMixin, ListView):
    template_name = 'report.html'
    model = Presence

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data()
        context.update({'slots': Slot.get_enabled_slots(self.request.user)})
        return context

    def get_queryset(self):
        slots = Slot.objects.filter(enabled=True)
        dates = [slot.date for slot in slots]
        return Presence.objects.filter(date__in=dates).order_by('-user__is_superuser')


class MarkAsSeen(BegeleiderRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        pk = int(kwargs.get('pk'))
        seen = kwargs.get('seen')

        mark_seen(pk, seen)
        return JsonResponse({"ok": True})


# @method_decorator(never_cache, name='dispatch')
class RegisterManual(BegeleiderRequiredMixin, SlotContextMixin, CreateView):
    template_name = 'register_manual.html'
    model = Presence
    fields = ['user']
    success_url = reverse_lazy('report')

    def form_valid(self, form):
        form.instance.date = self.slot.date
        form.instance.pod = self.slot.pod
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):

        try:
            response = super().post(request, *args, **kwargs)
        except IntegrityError as e:
            # Already registered -> ignore
            response = HttpResponseRedirect(reverse('report'))

        # Update pages on all clients
        asyncio.run(sio.emit("update_report_page"))
        asyncio.run(sio.emit("update_main_page"))
        return response
