from django.contrib.auth.mixins import UserPassesTestMixin
from .models import DjoUser


class PermissionRequiredMixin(UserPassesTestMixin):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_begeleider'] = DjoUser.is_begeleider(self.request.session['account_type'])
        return context

    def test_func(self):
        user = self.request.user
        if user.is_authenticated and user.is_active:
            return True
        return False


class BegeleiderRequiredMixin(UserPassesTestMixin):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_begeleider'] = self.test_func()
        return context

    def test_func(self):
        return DjoUser.is_begeleider(self.request.session['account_type'])
