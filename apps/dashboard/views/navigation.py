"""Editing the Collections mega menu: its category columns and the links inside them.

The rest of the header bar (About, Communications, Catalogues, Contact) is fixed and is
not exposed here — only the dropdown that opens under 'Collections'.
"""
from django.contrib import messages
from django.http import Http404, JsonResponse
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.core.models import NavigationItem, NavigationMenu

from ..forms import MegaMenuItemForm
from ..mixins import DashboardPermissionMixin
from .base import (
    DashboardCreateView,
    DashboardDeleteView,
    DashboardUpdateView,
    ReorderView,
    ToggleFieldView,
    _redirect_back,
)

PAGE_TITLE = "Collections menu"
INTRO = "The dropdown that opens under COLLECTIONS. Each column is a category; the rows inside it are its sub-categories. Use the arrows to change the order."


def collections_root():
    """The 'Collections' bar item whose children are rendered as the mega menu."""
    menu, _ = NavigationMenu.objects.get_or_create(slug="header", defaults={"name": "Header"})
    top_level = list(menu.items.filter(parent__isnull=True).order_by("order", "id"))
    for item in top_level:
        if item.children.exists():
            return item
    for item in top_level:
        if "collection" in item.label.lower():
            return item
    return NavigationItem.objects.create(menu=menu, label="Collections", link_type="none", order=0)


def subtree_ids(root):
    ids, frontier = set(), [root.pk]
    while frontier:
        frontier = list(NavigationItem.objects.filter(parent_id__in=frontier).values_list("pk", flat=True))
        ids.update(frontier)
    return ids


class MegaMenuView(DashboardPermissionMixin, TemplateView):
    """Columns and their links as one indented, drag-sortable list."""

    template_name = "dashboard/navigation/mega_menu.html"
    permission_required = "core.view_navigationitem"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        root = collections_root()
        user = self.request.user
        can_add = user.has_perm("core.add_navigationitem")
        can_change = user.has_perm("core.change_navigationitem")

        columns = list(
            NavigationItem.objects.filter(parent=root)
            .select_related("category", "collection")
            .prefetch_related("children__category", "children__collection")
        )
        rows = []
        for position, column in enumerate(columns):
            rows.append(self.row(column, 0, can_add, position, len(columns)))
            links = list(column.children.all())
            for link_position, link in enumerate(links):
                rows.append(self.row(link, 1, can_add, link_position, len(links)))

        context.update({
            "page_title": PAGE_TITLE,
            "intro": INTRO,
            "root": root,
            "rows": rows,
            "column_count": len(columns),
            "create_url": reverse("dashboard:mega_menu_item_create") if can_add else "",
            "reorder_url": reverse("dashboard:mega_menu_item_reorder") if can_change else "",
            "can_add": can_add,
            "can_change": can_change,
            "can_delete": user.has_perm("core.delete_navigationitem"),
            "breadcrumbs": [{"label": "Content"}, {"label": PAGE_TITLE}],
        })
        return context

    def row(self, item, depth, can_add, position, sibling_count):
        return {
            "obj": item,
            "depth": depth,
            "level_label": "Column" if depth == 0 else "Link",
            "parent_key": item.parent_id or 0,
            "child_count": item.children.count() if depth == 0 else 0,
            "is_first": position == 0,
            "is_last": position == sibling_count - 1,
            "move_up_url": reverse("dashboard:mega_menu_item_move", args=[item.pk, "up"]),
            "move_down_url": reverse("dashboard:mega_menu_item_move", args=[item.pk, "down"]),
            "edit_url": reverse("dashboard:mega_menu_item_update", args=[item.pk]),
            "delete_url": reverse("dashboard:mega_menu_item_delete", args=[item.pk]),
            "toggle_url": reverse("dashboard:mega_menu_item_toggle_active", args=[item.pk]),
            "add_child_url": f"{reverse('dashboard:mega_menu_item_create')}?column={item.pk}" if depth == 0 and can_add else "",
        }


class MegaMenuItemFormMixin:
    form_class = MegaMenuItemForm
    template_name = "dashboard/navigation/item_form.html"
    fieldsets = [
        ("Placement", ["parent", "label", "is_active"]),
        ("Destination", ["link_type", "category", "collection", "external_url", "url_suffix", "open_in_new_tab"]),
    ]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["root"] = collections_root()
        return kwargs

    def menu_url(self):
        return reverse("dashboard:mega_menu")

    def get_success_url(self):
        if "_continue" in self.request.POST:
            return reverse("dashboard:mega_menu_item_update", args=[self.object.pk])
        return self.menu_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = self.menu_url()
        context["breadcrumbs"] = [
            {"label": "Content"},
            {"label": PAGE_TITLE, "url": self.menu_url()},
            {"label": "Edit" if getattr(self, "object", None) else "Add"},
        ]
        return context


class MegaMenuItemCreateView(MegaMenuItemFormMixin, DashboardCreateView):
    model = NavigationItem
    permission_required = "core.add_navigationitem"
    page_title = "Add menu item"
    success_message = "Menu item added."

    def get_initial(self):
        initial = super().get_initial()
        column = self.request.GET.get("column")
        if column and str(column).isdigit():
            candidate = NavigationItem.objects.filter(pk=column, parent=collections_root()).first()
            if candidate is not None:
                initial["parent"] = candidate.pk
                initial["link_type"] = "collection"
        else:
            initial["link_type"] = "category"
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Add link" if self.request.GET.get("column") else "Add column"
        return context


class MegaMenuItemUpdateView(MegaMenuItemFormMixin, DashboardUpdateView):
    model = NavigationItem
    permission_required = "core.change_navigationitem"
    success_message = "Menu item updated."

    def get_queryset(self):
        return NavigationItem.objects.filter(pk__in=subtree_ids(collections_root()))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit: {self.object.label}"
        return context


class MegaMenuItemDeleteView(DashboardDeleteView):
    model = NavigationItem
    permission_required = "core.delete_navigationitem"
    success_message = "Menu item deleted."

    def get_queryset(self):
        return NavigationItem.objects.filter(pk__in=subtree_ids(collections_root()))

    def get_success_url(self):
        return reverse("dashboard:mega_menu")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = reverse("dashboard:mega_menu")
        child_count = self.object.children.count()
        if child_count:
            context["extra_warning"] = f"This column also holds {child_count} link(s), which are deleted with it."
        return context


class MegaMenuItemToggleActiveView(ToggleFieldView):
    model = NavigationItem
    field = "is_active"
    permission_required = "core.change_navigationitem"

    def post(self, request, pk, *args, **kwargs):
        if pk not in subtree_ids(collections_root()):
            return JsonResponse({"ok": False, "error": "Not found"}, status=404)
        return super().post(request, pk, *args, **kwargs)


class MegaMenuItemReorderView(ReorderView):
    """Reorders within the mega menu only; ids outside it are ignored."""

    model = NavigationItem
    permission_required = "core.change_navigationitem"

    def get_queryset(self):
        return NavigationItem.objects.filter(pk__in=subtree_ids(collections_root()))


class MegaMenuItemMoveView(DashboardPermissionMixin, View):
    """Move one row up or down among its own siblings — the no-drag way to reorder."""

    permission_required = "core.change_navigationitem"
    http_method_names = ["post"]

    def post(self, request, pk, direction, *args, **kwargs):
        item = NavigationItem.objects.filter(pk=pk, pk__in=subtree_ids(collections_root())).first()
        if item is None:
            raise Http404("Not part of the Collections menu")
        siblings = list(NavigationItem.objects.filter(parent_id=item.parent_id).order_by("order", "id"))
        index = next(position for position, sibling in enumerate(siblings) if sibling.pk == item.pk)
        target = index - 1 if direction == "up" else index + 1
        if 0 <= target < len(siblings):
            siblings[index], siblings[target] = siblings[target], siblings[index]
            for position, sibling in enumerate(siblings):
                if sibling.order != position:
                    sibling.order = position
                    sibling.save(update_fields=["order"])
            messages.success(request, f"“{item.label}” moved {direction}.")
        return _redirect_back(request, "dashboard:mega_menu")
