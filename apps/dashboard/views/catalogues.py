"""The Catalogues section.

A catalogue is its own record, so this screen is an ordinary list: add one,
edit it, reorder it, hide it, delete it. It used to be a view onto Category —
every range became a card and nothing else could — which meant a catalogue
could not exist without a product range behind it.

A catalogue may still point at a range, but only to give a card somewhere to go
before its PDF is uploaded. Nothing it shows comes from there.
"""
from django.urls import reverse

from apps.catalog.models import Catalogue

from ..forms import CatalogueForm
from .base import (
    DashboardCreateView,
    DashboardDeleteView,
    DashboardListView,
    DashboardUpdateView,
    ReorderView,
    ToggleFieldView,
)

CATALOGUE_CRUMB = {"label": "Catalogues"}


class CatalogueListView(DashboardListView):
    model = Catalogue
    permission_required = "catalog.view_catalogue"
    page_title = "Catalogues"
    template_name = "dashboard/generic/list.html"
    default_ordering = "order"
    allow_page_size = False
    search_fields = ["title", "slug", "subtitle"]
    create_url_name = "dashboard:catalogue_create"
    update_url_name = "dashboard:catalogue_update"
    delete_url_name = "dashboard:catalogue_delete"
    reorder_url_name = "dashboard:catalogue_reorder"
    breadcrumbs = [CATALOGUE_CRUMB, {"label": "Catalogues"}]
    empty_message = "No catalogues yet. Add the first one."
    columns = [
        {"label": "", "field": "image", "type": "image"},
        {"label": "Title", "field": "title", "type": "title"},
        {"label": "Subtitle", "field": "subtitle"},
        {"label": "Range", "field": "category"},
        {"label": "PDF", "field": "pdf", "type": "bool"},
        {"label": "Live", "field": "is_active", "type": "active"},
    ]

    def get_base_queryset(self):
        return Catalogue.objects.select_related("category").order_by("order", "pk")

    def row_actions(self, obj):
        actions = super().row_actions(obj)
        if self.request.user.has_perm("catalog.change_catalogue"):
            actions.insert(0, {
                "label": "Hide" if obj.is_active else "Show",
                "url": reverse("dashboard:catalogue_toggle", args=[obj.pk]),
                "icon": "eye",
                "method": "post",
            })
        return actions


class CatalogueCreateView(DashboardCreateView):
    model = Catalogue
    form_class = CatalogueForm
    permission_required = "catalog.add_catalogue"
    page_title = "New catalogue"
    list_url_name = "dashboard:catalogue_list"
    update_url_name = "dashboard:catalogue_update"
    success_message = "Catalogue created."
    breadcrumbs = [CATALOGUE_CRUMB, {"label": "Catalogues", "url": "dashboard:catalogue_list"}, {"label": "New"}]


class CatalogueUpdateView(DashboardUpdateView):
    model = Catalogue
    form_class = CatalogueForm
    permission_required = "catalog.change_catalogue"
    list_url_name = "dashboard:catalogue_list"
    update_url_name = "dashboard:catalogue_update"
    success_message = "Catalogue updated."
    breadcrumbs = [CATALOGUE_CRUMB, {"label": "Catalogues", "url": "dashboard:catalogue_list"}]

    def get_context_data(self, **kwargs):
        # page_title is read as an attribute by DashboardFormMixin, so the
        # per-row title is set here rather than through a method.
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit catalogue: {self.object.title}"
        return context


class CatalogueDeleteView(DashboardDeleteView):
    model = Catalogue
    permission_required = "catalog.delete_catalogue"
    list_url_name = "dashboard:catalogue_list"
    success_message = "Catalogue deleted."


class CatalogueToggleView(ToggleFieldView):
    model = Catalogue
    field = "is_active"
    permission_required = "catalog.change_catalogue"


class CatalogueReorderView(ReorderView):
    model = Catalogue
    permission_required = "catalog.change_catalogue"
