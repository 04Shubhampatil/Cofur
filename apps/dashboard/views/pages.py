from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView

from apps.pages.models import AboutPage, ContactPage, HomePage

from ..forms import (
    AboutPageForm,
    ContactPageForm,
    DifferentiatorFormSet,
    HeroSlideFormSet,
    HomePageForm,
    StatementLineFormSet,
)
from ..mixins import DashboardPermissionMixin

CONTENT_CRUMB = {"label": "Content"}


class SingletonPageView(DashboardPermissionMixin, FormView):
    """Edit a singleton page model with optional inline formsets."""

    template_name = "dashboard/pages/page_form.html"
    model = None
    page_title = ""
    tabs = []  # (key, label, [fields]) — extra formsets referenced by key in 'formsets'
    formset_classes = {}
    preview_url_name = None
    breadcrumbs = []

    def get_object(self):
        return self.model.load()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.get_object()
        return kwargs

    def get_formsets(self, instance):
        data = self.request.POST if self.request.method == "POST" else None
        files = self.request.FILES if self.request.method == "POST" else None
        return {key: cls(data, files, prefix=key, instance=instance) for key, cls in self.formset_classes.items()}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = self.get_object()
        context.setdefault("formsets", self.get_formsets(instance))
        context.update({
            "page_title": self.page_title,
            "tabs": self.tabs,
            "object": instance,
            "breadcrumbs": self.breadcrumbs,
            "preview_url": reverse(self.preview_url_name) if self.preview_url_name else "",
        })
        return context

    def form_valid(self, form):
        instance = self.get_object()
        formsets = self.get_formsets(instance)
        if not all(fs.is_valid() for fs in formsets.values()):
            messages.error(self.request, "Please fix the errors below.")
            return self.render_to_response(self.get_context_data(form=form, formsets=formsets))
        with transaction.atomic():
            form.save()
            for formset in formsets.values():
                formset.save()
        messages.success(self.request, f"{self.page_title} saved.")
        return redirect(self.request.path)

    def form_invalid(self, form):
        messages.error(self.request, "Please fix the errors below.")
        return super().form_invalid(form)


class HomePageEditView(SingletonPageView):
    model = HomePage
    form_class = HomePageForm
    permission_required = "pages.change_homepage"
    page_title = "Home page"
    preview_url_name = "website:home"
    breadcrumbs = [CONTENT_CRUMB, {"label": "Home page"}]
    formset_classes = {
        "slides": HeroSlideFormSet,
        "lines": StatementLineFormSet,
        "differentiators": DifferentiatorFormSet,
    }
    tabs = [
        ("hero", "Hero", ["hero_heading", "hero_visible"], "slides", "Hero slides"),
        ("intro", "Intro & categories", ["intro_heading", "intro_heading_highlight", "intro_visible", "category_section_visible"], None, None),
        ("statement", "Brand statement", ["statement_heading", "statement_description", "statement_cta_text", "statement_cta_url", "statement_visible"], "lines", "Statement lines"),
        ("featured", "Featured products", ["featured_heading", "featured_cta_text", "featured_visible"], None, None),
        ("why", "Differentiators", ["why_heading", "why_image", "why_image_alt", "why_visible"], "differentiators", "Differentiator items"),
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["help_text"] = "Categories in the rail come from Products Master › Categories ('Show on home'). Featured products are the ones starred / marked 'Featured' in Products Master › Products."
        return context


class AboutPageEditView(SingletonPageView):
    model = AboutPage
    form_class = AboutPageForm
    permission_required = "pages.change_aboutpage"
    page_title = "About page"
    preview_url_name = "website:about"
    breadcrumbs = [CONTENT_CRUMB, {"label": "About page"}]
    tabs = [
        ("hero", "Hero", ["hero_heading", "hero_image", "hero_image_alt", "hero_mobile_image", "hero_mobile_alt", "intro_heading", "intro_text"], None, None),
        ("make", "What we make", ["what_we_make_heading", "what_we_make_content"], None, None),
        ("work", "How we work", ["how_we_work_heading", "how_we_work_content"], None, None),
        ("philosophy", "Philosophy", ["philosophy_heading", "philosophy_content"], None, None),
        ("mission", "Mission", ["mission_heading", "mission_content"], None, None),
        ("team", "Team & location", ["team_heading", "team_visible", "find_us_heading", "find_us_company", "find_us_address", "find_us_map_url", "find_us_visible"], None, None),
        ("sustainability", "Sustainability", ["sustainability_heading", "sustainability_content", "sustainability_image", "sustainability_image_alt"], None, None),
        ("recycled", "Recycled materials", ["recycled_heading", "recycled_content"], None, None),
        ("tree", "Tree planting", ["tree_heading", "tree_description"], None, None),
        ("india", "Made in India", ["india_image", "india_text", "india_visible"], None, None),
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["help_text"] = "Team members are managed under People › Team members."
        return context


class ContactPageEditView(SingletonPageView):
    model = ContactPage
    form_class = ContactPageForm
    permission_required = "pages.change_contactpage"
    page_title = "Contact page"
    preview_url_name = "website:contact"
    breadcrumbs = [CONTENT_CRUMB, {"label": "Contact page"}]
    tabs = [
        ("hero", "Banner & intro", ["page_title", "banner_image", "banner_alt", "banner_mobile_image", "banner_mobile_alt", "eyebrow", "heading", "intro_text"], None, None),
        ("details", "Contact details", ["visit_heading", "address", "mail_heading", "email", "hours_heading", "working_hours"], None, None),
        ("form", "Contact form", ["form_heading", "form_button_text", "success_message"], None, None),
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["help_text"] = "Social links are managed under Settings › Social links."
        return context
