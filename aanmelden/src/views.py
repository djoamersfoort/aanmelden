import asyncio
from datetime import timedelta

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
        except Exception as e:
            # Something went wrong getting the token
            return HttpResponseForbidden('Geen toegang: {0}'.format(e))

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
        if not request.user.is_superuser:
            # Check if any slots are available server side
            if Presence.slots_available(self.slot.date, self.slot.pod) <= 0:
                return HttpResponseRedirect(reverse('full', kwargs=kwargs))

            # Check if allowed to register for the number of days
            if self.slot.name == 'fri':
                # Reg for Friday, check saturday in the same weekend
                check_date = self.slot.date + timedelta(days=1)
            else:
                # Reg for Saturday, check Friday in the same weekend
                check_date = self.slot.date - timedelta(days=1)
            reg_count = Presence.objects.filter(date=check_date, user=request.user).count()
            if reg_count >= request.user.userinfo.days:
                return HttpResponseRedirect(reverse('only_once'))

        presence = Presence()
        presence.date = self.slot.date
        presence.pod = self.slot.pod
        presence.user = request.user

        try:
            presence.save()
        except IntegrityError as e:
            # Already registered -> ignore
            pass

        asyncio.run(sio.emit("update_report_page"))
        asyncio.run(sio.emit("update_main_page"))

        return super().get(request, args, kwargs)


@method_decorator(never_cache, name='dispatch')
class DeRegister(LoginRequiredMixin, SlotContextMixin, TemplateView):
    template_name = 'deregistered.html'

    def get(self, request, *args, **kwargs):
        try:
            presence = Presence.objects.get(date=self.slot.date, user=self.request.user, pod=self.slot.pod)
            if presence:
                presence.delete()
        except Presence.DoesNotExist:
            pass

        asyncio.run(sio.emit("update_report_page"))
        asyncio.run(sio.emit("update_main_page"))

        return super().get(request, args, kwargs)


class Full(LoginRequiredMixin, SlotContextMixin, TemplateView):
    template_name = 'full.html'


class OnlyOnce(LoginRequiredMixin, TemplateView):
    template_name = 'only_once.html'


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

        # Tell all clients to update the report page
        asyncio.run(sio.emit("update_report_page"))

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
