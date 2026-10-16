"""Editing the campaign landing pages: their text lines and photographs.

Each page's items live in the LandingText table. This screen lists them for one
page and saves the edits in a single form.
"""
from django import forms
from django.contrib import messages
from django.forms import Textarea, modelformset_factory
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.core.mixins import SEOFieldsMixin
from apps.pages.landing_content import WALL_PAGE
from apps.pages.landing_content_ceilings import CEILING_PAGE
from apps.pages.models import LandingText

from ..mixins import DashboardPermissionMixin


LONG_TEXT = 90  # characters; longer lines get a multi-line box

# "Use the site setting" first, then the same wording the rest of the CMS uses.
ROBOTS_CHOICES = [("", "Use the site setting")] + list(SEOFieldsMixin.ROBOTS_CHOICES)


class LandingItemForm(forms.ModelForm):
    """One editable item: a single-line box for short text, a taller box for paragraphs."""

    class Meta:
        model = LandingText
        fields = ("value", "image")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        value = self.instance.value or ""
        if self.instance.key == "seo_robots":
            self.fields["value"].widget = forms.Select(choices=ROBOTS_CHOICES, attrs={"class": "form-input"})
        elif "\n" in value or len(value) > LONG_TEXT:
            self.fields["value"].widget = Textarea(attrs={"rows": 3, "class": "form-textarea"})
        else:
            self.fields["value"].widget = forms.TextInput(attrs={"class": "form-input"})
        self.fields["value"].required = False

    def clean_value(self):
        """A mistyped canonical address is worse than none, so check it here."""
        value = self.cleaned_data.get("value") or ""
        if self.instance.key == "seo_canonical":
            value = value.strip()
            if value and not value.startswith(("/", "http://", "https://")):
                raise forms.ValidationError(
                    "Enter a full web address (https://cofur.in/...) or a path starting with /."
                )
        return value


# Editor sections, matched by the start of each item's key. First match wins.
SECTION_GROUPS = [
    ("Top bar and menu", ("top_bar", "nav_")),
    ("Hero", ("hero_", "img_hero")),
    ("Trust strip", ("trust_",)),
    ("Products and designs", ("products_", "product_", "design_", "img_product_", "img_design_")),
    ("Applications", ("apps_",)),
    ("Dark band", ("band_",)),
    ("For professional project teams", ("aud_", "role_")),
    ("Enquiry", ("enq_",)),
    ("Enquiry form", ("form_",)),
    ("FAQ", ("faq_",)),
    ("Closing", ("final_",)),
    ("Footer and mobile bar", ("footer_", "sticky_")),
    ("SEO", ("seo_", "img_seo")),
]


def group_forms(forms):
    """Split the formset's forms into (title, [forms]) cards, keeping their order."""
    groups = []
    for title, prefixes in SECTION_GROUPS:
        members = [f for f in forms if f.instance.key.startswith(prefixes)]
        if members:
            groups.append((title, members))
    placed = {id(f) for _, members in groups for f in members}
    rest = [f for f in forms if id(f) not in placed]
    if rest:
        groups.append(("Other", rest))
    return groups


class LandingPageEditView(DashboardPermissionMixin, View):
    """Edit every text line and photo of one landing page."""

    permission_required = "pages.change_landingtext"
    page = None
    page_title = ""
    url_name = None
    template_name = "dashboard/landing/edit.html"

    def get_formset_class(self):
        return modelformset_factory(
            LandingText,
            form=LandingItemForm,
            fields=("value", "image"),
            extra=0,
        )

    def get_queryset(self):
        return LandingText.objects.filter(page=self.page)

    preview_url = None
    help_text = "Edit the wording and photos below, then save. Changes show on the live page straight away."

    def render(self, request, formset):
        return render(request, self.template_name, {
            "page_title": self.page_title,
            "help_text": self.help_text,
            "preview_url": self.preview_url,
            "cancel_url": reverse("dashboard:landing_index"),
            "formset": formset,
            "groups": group_forms(list(formset.forms)),
            "breadcrumbs": [{"label": "Landing pages", "url": "dashboard:landing_index"}, {"label": self.page_title}],
        })

    def get(self, request, *args, **kwargs):
        formset = self.get_formset_class()(queryset=self.get_queryset(), prefix="landing")
        return self.render(request, formset)

    def post(self, request, *args, **kwargs):
        formset = self.get_formset_class()(
            request.POST, request.FILES, queryset=self.get_queryset(), prefix="landing",
        )
        if formset.is_valid():
            formset.save()
            messages.success(request, "Landing page saved.")
            if "_continue" in request.POST:
                return redirect(reverse(self.url_name))
            return redirect(reverse("dashboard:landing_index"))
        messages.error(request, "Please fix the errors below.")
        return self.render(request, formset)


class LandingWallEditView(LandingPageEditView):
    page = WALL_PAGE
    page_title = "Wall panels landing page"
    url_name = "dashboard:landing_wall"
    preview_url = "/acoustic-wall-panels-for-offices/"


class LandingCeilingsEditView(LandingPageEditView):
    page = CEILING_PAGE
    page_title = "Ceilings landing page"
    url_name = "dashboard:landing_ceilings"
    preview_url = "/acoustic-ceilings-for-offices/"


class LandingIndexView(DashboardPermissionMixin, TemplateView):
    """Lists the campaign pages that can be edited."""

    permission_required = "pages.change_landingtext"
    template_name = "dashboard/landing/index.html"
    page_title = "Landing pages"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": self.page_title,
            "pages": [
                ("Wall panels landing page", reverse("dashboard:landing_wall")),
                ("Ceilings landing page", reverse("dashboard:landing_ceilings")),
            ],
        })
        return context
