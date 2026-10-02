"""The Catalogues page section.

The rail on /catalogues/ is built from the same Category rows as the home rail,
so there was nowhere to control it on its own: every active category appeared,
in the home rail's order. These views give that section its own screen, backed
by ``show_on_catalogues`` and ``catalogue_order`` so changing it here leaves the
home rail alone.

Cards are not created or deleted here — a card exists because a category does.
"""
from django.urls import reverse

from apps.catalog.models import Category

from ..forms import CatalogueCardForm
from .base import DashboardListView, DashboardUpdateView, ReorderView, ToggleFieldView

CATALOGUE_CRUMB = {"label": "Catalogues"}


class CatalogueCardListView(DashboardListView):
    model = Category
    permission_required = "catalog.view_category"
    page_title = "Catalogue cards"
    template_name = "dashboard/generic/list.html"
    default_ordering = None
    allow_page_size = False
    search_fields = ["name", "slug", "subtitle"]
    update_url_name = "dashboard:catalogue_card_update"
    reorder_url_name = "dashboard:catalogue_card_reorder"
    breadcrumbs = [CATALOGUE_CRUMB, {"label": "Catalogue cards"}]
    empty_message = "Add a category first — each one becomes a card here."
    columns = [
        {"label": "", "field": "thumbnail_image", "type": "image"},
        {"label": "Range", "field": "name", "type": "title"},
        {"label": "Subtitle", "field": "subtitle"},
        {"label": "Catalogue PDF", "field": "catalogue_pdf", "type": "bool"},
        {"label": "On Catalogues page", "field": "show_on_catalogues", "type": "bool"},
        {"label": "Live", "field": "is_active", "type": "active"},
    ]

    def get_base_queryset(self):
        # Inactive categories are listed too, so it is clear why a card is
        # missing from the page: the range itself is switched off.
        return Category.objects.order_by("catalogue_order", "pk")

    def row_actions(self, obj):
        actions = super().row_actions(obj)
        if self.request.user.has_perm("catalog.change_category"):
            actions.insert(0, {
                "label": "Hide" if obj.show_on_catalogues else "Show",
                "url": reverse("dashboard:catalogue_card_toggle", args=[obj.pk]),
                "icon": "eye",
                "method": "post",
            })
        return actions


class CatalogueCardUpdateView(DashboardUpdateView):
    model = Category
    form_class = CatalogueCardForm
    permission_required = "catalog.change_category"
    list_url_name = "dashboard:catalogue_card_list"
    breadcrumbs = [CATALOGUE_CRUMB, {"label": "Catalogue cards", "url": "dashboard:catalogue_card_list"}]

    def get_context_data(self, **kwargs):
        # page_title is read as an attribute by DashboardFormMixin, so the
        # per-row title is set here rather than through a method.
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"{self.object.name} — catalogue card"
        return context


class CatalogueCardToggleView(ToggleFieldView):
    model = Category
    field = "show_on_catalogues"
    permission_required = "catalog.change_category"


class CatalogueCardReorderView(ReorderView):
    """Drag-to-reorder, writing ``catalogue_order`` instead of ``order``.

    The base view hard-codes ``order``, which is the home rail's. Reordering
    this page must not move the home cards.
    """

    model = Category
    permission_required = "catalog.change_category"
    order_field = "catalogue_order"
