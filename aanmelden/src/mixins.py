from django.contrib.auth.mixins import UserPassesTestMixin


class PermissionRequiredMixin(UserPassesTestMixin):

    def check_user(self, user):
        if user.is_authenticated and user.is_active:
            return True
        return False

    def test_func(self):
        return self.check_user(self.request.user)


class BegeleiderRequiredMixin(UserPassesTestMixin):

    def test_func(self):
        if 'profile' in self.request.session:
            if 'begeleider' in self.request.session['profile']['types']:
                return True
        return False
