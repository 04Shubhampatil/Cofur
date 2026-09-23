from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from apps.core.models import SiteSettings

from ..forms import FooterSettingsForm, SiteSettingsForm
from ..mixins import DashboardPermissionMixin

SETTINGS_CRUMB = {"label": "Settings"}


class SiteSettingsBaseView(DashboardPermissionMixin, FormView):
    permission_required = "core.change_sitesettings"
    template_name = "dashboard/generic/form.html"
    page_title = "Site settings"
    fieldsets = None
    breadcrumbs = []

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = SiteSettings.load()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": self.page_title,
            "fieldsets": self.fieldsets,
            "breadcrumbs": self.breadcrumbs,
            "cancel_url": reverse("dashboard:index"),
            "object": SiteSettings.load(),
            "hide_continue": True,
        })
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f"{self.page_title} saved.")
        return redirect(self.request.path)

    def form_invalid(self, form):
        messages.error(self.request, "Please fix the errors below.")
        return super().form_invalid(form)


class SiteSettingsView(SiteSettingsBaseView):
    form_class = SiteSettingsForm
    page_title = "Site settings"
    breadcrumbs = [SETTINGS_CRUMB, {"label": "Site settings"}]
    fieldsets = [
        ("Brand", ["site_name", "tagline", "logo", "logo_light", "favicon"]),
        ("Contact", ["contact_email", "address", "google_maps_url", "whatsapp_number", "whatsapp_message"]),
        ("Social profiles (footer icons)", ["linkedin_url", "instagram_url", "twitter_url"]),
    ]


class FooterSettingsView(SiteSettingsBaseView):
    form_class = FooterSettingsForm
    page_title = "Footer"
    breadcrumbs = [{"label": "Content"}, {"label": "Footer"}]
    fieldsets = [
        ("Footer content", ["logo_light", "footer_eyebrow", "footer_title", "copyright_text"]),
        ("Call to action", ["footer_primary_cta_text", "footer_primary_cta_url", "footer_secondary_cta_text", "footer_secondary_cta_url"]),
        ("Contact information", ["address", "google_maps_url", "contact_email"]),
        ("Social profiles (footer icons)", ["linkedin_url", "instagram_url", "twitter_url"]),
    ]
