import logging

from django.contrib import messages
from django.contrib.auth import views as auth_views

from apps.enquiries.services import client_ip

from ..security import lockout_seconds, record_failure, reset_failures

log = logging.getLogger("cofur.security")
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy


class DashboardAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": "form-input", "autofocus": True, "autocomplete": "username"})
        self.fields["password"].widget.attrs.update({"class": "form-input", "autocomplete": "current-password"})

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            from django.core.exceptions import ValidationError

            raise ValidationError("This account does not have dashboard access.", code="not_staff")


class LoginView(auth_views.LoginView):
    template_name = "dashboard/auth/login.html"
    authentication_form = DashboardAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return self.get_redirect_url() or reverse_lazy("dashboard:index")

    def get_context_data(self, **kwargs):
        # LoginView adds a RequestSite as ``site``; restore our SiteSettings object.
        from apps.core.models import SiteSettings

        context = super().get_context_data(**kwargs)
        context["site"] = SiteSettings.load()
        return context

    def post(self, request, *args, **kwargs):
        ip = client_ip(request)
        username = request.POST.get("username", "")
        wait = lockout_seconds(ip, username)
        if wait:
            minutes = max(1, -(-wait // 60))
            form = self.get_form()
            form.add_error(None, f"Too many failed sign-in attempts. Try again in {minutes} minute{'s' if minutes != 1 else ''}.")
            response = self.render_to_response(self.get_context_data(form=form))
            response.status_code = 429
            return response
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        record_failure(client_ip(self.request), self.request.POST.get("username", ""))
        return super().form_invalid(form)

    def form_valid(self, form):
        reset_failures(client_ip(self.request), form.cleaned_data.get("username", ""))
        log.info("Admin login: %s from %s", form.get_user(), client_ip(self.request))
        remember = self.request.POST.get("remember")
        response = super().form_valid(form)
        self.request.session.cycle_key()
        if not remember:
            self.request.session.set_expiry(0)
        return response


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("dashboard:login")


class PasswordChangeView(LoginRequiredMixin, auth_views.PasswordChangeView):
    template_name = "dashboard/auth/password_change.html"
    success_url = reverse_lazy("dashboard:index")
    form_class = PasswordChangeForm

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "form-input"
        return form

    def form_valid(self, form):
        messages.success(self.request, "Your password has been changed.")
        return super().form_valid(form)
