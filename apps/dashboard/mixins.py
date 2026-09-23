from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only active staff users may use the dashboard."""

    login_url = reverse_lazy("dashboard:login")

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_active and user.is_staff

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


class DashboardPermissionMixin(StaffRequiredMixin, PermissionRequiredMixin):
    """Staff + explicit model permission. Raises 403 instead of redirecting when logged in."""

    raise_exception = False

    def has_permission(self):
        if not self.test_func():
            return False
        return super().has_permission()

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


class SuperuserRequiredMixin(StaffRequiredMixin):
    def test_func(self):
        return super().test_func() and self.request.user.is_superuser
