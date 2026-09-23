"""Reusable dashboard CRUD views (list with search/filter/pagination, create, update, delete, reorder)."""
import json

from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from ..mixins import DashboardPermissionMixin


class DashboardListView(DashboardPermissionMixin, ListView):
    """Generic paginated table.

    Subclasses set ``model``, ``columns`` (list of dicts: label, field, type),
    ``search_fields``, ``filters`` (list of dicts: name, label, choices|queryset,
    lookup), ``ordering`` and URL names for actions.
    """

    template_name = "dashboard/generic/list.html"
    paginate_by = settings.DASHBOARD_PAGE_SIZE
    page_title = ""
    columns = []
    search_fields = []
    filters = []
    default_ordering = None
    create_url_name = None
    update_url_name = None
    delete_url_name = None
    reorder_url_name = None
    row_template = None
    empty_message = "Nothing here yet."
    breadcrumbs = []
    allow_page_size = True

    def get_paginate_by(self, queryset):
        if self.allow_page_size:
            try:
                size = int(self.request.GET.get("per_page", 0))
                if 5 <= size <= 200:
                    return size
            except ValueError:
                pass
        return self.paginate_by

    def get_base_queryset(self):
        return self.model._default_manager.all()

    def get_queryset(self):
        qs = self.get_base_queryset()
        q = self.request.GET.get("q", "").strip()
        if q and self.search_fields:
            query = Q()
            for field in self.search_fields:
                query |= Q(**{f"{field}__icontains": q})
            qs = qs.filter(query)
        for flt in self.filters:
            value = self.request.GET.get(flt["name"], "").strip()
            if value == "":
                continue
            lookup = flt.get("lookup", flt["name"])
            if flt.get("type") == "bool":
                qs = qs.filter(**{lookup: value == "1"})
            elif flt.get("type") == "date_from":
                qs = qs.filter(**{f"{lookup}__date__gte": value})
            elif flt.get("type") == "date_to":
                qs = qs.filter(**{f"{lookup}__date__lte": value})
            else:
                qs = qs.filter(**{lookup: value})
        ordering = self.request.GET.get("sort") or self.default_ordering
        if ordering:
            allowed = {c["field"] for c in self.columns if c.get("sortable")}
            allowed |= {self.default_ordering.lstrip("-")} if self.default_ordering else set()
            if ordering.lstrip("-") in allowed:
                qs = qs.order_by(ordering)
        return qs

    def get_filters_context(self):
        rendered = []
        for flt in self.filters:
            data = dict(flt)
            data["value"] = self.request.GET.get(flt["name"], "")
            if "queryset" in flt:
                data["choices"] = [(obj.pk, str(obj)) for obj in flt["queryset"]()]
            elif flt.get("type") == "bool":
                data["choices"] = [("1", flt.get("true_label", "Yes")), ("0", flt.get("false_label", "No"))]
            rendered.append(data)
        return rendered

    def row_actions(self, obj):
        actions = []
        if self.update_url_name and self.request.user.has_perm(self.change_perm()):
            actions.append({"label": "Edit", "url": reverse(self.update_url_name, args=[obj.pk]), "icon": "edit"})
        if self.delete_url_name and self.request.user.has_perm(self.delete_perm()):
            actions.append({"label": "Delete", "url": reverse(self.delete_url_name, args=[obj.pk]), "icon": "trash", "danger": True})
        return actions

    def perm(self, action):
        return f"{self.model._meta.app_label}.{action}_{self.model._meta.model_name}"

    def add_perm(self):
        return self.perm("add")

    def change_perm(self):
        return self.perm("change")

    def delete_perm(self):
        return self.perm("delete")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        rows = [{"obj": obj, "actions": self.row_actions(obj)} for obj in context["object_list"]]
        context.update({
            "page_title": self.page_title or self.model._meta.verbose_name_plural.title(),
            "columns": self.columns,
            "rows": rows,
            "search_query": self.request.GET.get("q", ""),
            "filters": self.get_filters_context(),
            "create_url": reverse(self.create_url_name) if self.create_url_name and self.request.user.has_perm(self.add_perm()) else "",
            "reorder_url": reverse(self.reorder_url_name) if self.reorder_url_name and self.request.user.has_perm(self.change_perm()) else "",
            "empty_message": self.empty_message,
            "breadcrumbs": self.breadcrumbs,
            "row_template": self.row_template,
            "per_page": self.get_paginate_by(None),
            "total_count": context["paginator"].count if context.get("paginator") else len(rows),
            "model_name": self.model._meta.verbose_name,
        })
        return context


class DashboardFormMixin:
    template_name = "dashboard/generic/form.html"
    page_title = ""
    breadcrumbs = []
    success_message = "Saved."
    list_url_name = None
    fieldsets = None  # list of (title, [field names]) rendered as tabs/sections

    def get_success_url(self):
        if "_continue" in self.request.POST and hasattr(self, "update_url_name") and self.update_url_name:
            return reverse(self.update_url_name, args=[self.object.pk])
        if self.list_url_name:
            return reverse(self.list_url_name)
        return self.request.path

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, self.success_message)
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Please fix the errors below.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": self.page_title,
            "breadcrumbs": self.breadcrumbs,
            "fieldsets": self.fieldsets,
            "cancel_url": reverse(self.list_url_name) if self.list_url_name else reverse("dashboard:index"),
        })
        return context


class DashboardCreateView(DashboardFormMixin, DashboardPermissionMixin, CreateView):
    update_url_name = None


class DashboardUpdateView(DashboardFormMixin, DashboardPermissionMixin, UpdateView):
    update_url_name = None


class DashboardDeleteView(DashboardPermissionMixin, DeleteView):
    template_name = "dashboard/generic/confirm_delete.html"
    list_url_name = None
    success_message = "Deleted."
    breadcrumbs = []

    def get_success_url(self):
        return reverse(self.list_url_name)

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = reverse(self.list_url_name)
        context["breadcrumbs"] = self.breadcrumbs
        context["verbose_name"] = self.model._meta.verbose_name
        return context


class ReorderView(DashboardPermissionMixin, View):
    """POST JSON {"order": [id, id, ...]} -> updates the ``order`` field."""

    model = None
    http_method_names = ["post"]

    def get_queryset(self):
        return self.model._default_manager.all()

    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body or "{}")
            ids = [int(pk) for pk in payload.get("order", [])]
        except (ValueError, TypeError, json.JSONDecodeError):
            return HttpResponseBadRequest("Invalid payload")
        objects = {obj.pk: obj for obj in self.get_queryset().filter(pk__in=ids)}
        for position, pk in enumerate(ids):
            obj = objects.get(pk)
            if obj is not None and obj.order != position:
                obj.order = position
                obj.save(update_fields=["order"])
        return JsonResponse({"ok": True})


class ToggleFieldView(DashboardPermissionMixin, View):
    """POST toggles a boolean field (or sets it from the ``value`` param)."""

    model = None
    field = None
    http_method_names = ["post"]

    def post(self, request, pk, *args, **kwargs):
        obj = self.model._default_manager.filter(pk=pk).first()
        if obj is None:
            return JsonResponse({"ok": False, "error": "Not found"}, status=404)
        value = request.POST.get("value")
        new_value = (value == "1") if value in ("0", "1") else not getattr(obj, self.field)
        setattr(obj, self.field, new_value)
        obj.save(update_fields=[self.field, "updated_at"] if hasattr(obj, "updated_at") else [self.field])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "value": new_value})
        messages.success(request, f"{obj} updated.")
        return _redirect_back(request)


def _redirect_back(request, fallback="dashboard:index"):
    from django.shortcuts import redirect
    from django.utils.http import url_has_allowed_host_and_scheme

    target = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    return redirect(fallback)
