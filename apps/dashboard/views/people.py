from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView

from apps.enquiries.models import Enquiry
from apps.team.models import TeamMember

from ..forms import EnquiryUpdateForm, TeamMemberForm
from ..mixins import DashboardPermissionMixin
from .base import DashboardCreateView, DashboardDeleteView, DashboardListView, DashboardUpdateView, ReorderView, ToggleFieldView


# ------------------------------------------------------------------ team
class TeamListView(DashboardListView):
    model = TeamMember
    permission_required = "team.view_teammember"
    page_title = "Team members"
    columns = [
        {"label": "Photo", "field": "thumbnail", "type": "image"},
        {"label": "Name", "field": "name", "type": "title", "sortable": True},
        {"label": "Designation", "field": "designation"},
        {"label": "Status", "field": "is_active", "type": "active"},
        {"label": "Order", "field": "order", "sortable": True},
        {"label": "Updated", "field": "updated_at", "type": "date", "sortable": True},
    ]
    search_fields = ["name", "designation", "biography"]
    filters = [{"name": "is_active", "label": "Status", "type": "bool", "true_label": "Active", "false_label": "Inactive"}]
    create_url_name = "dashboard:team_create"
    update_url_name = "dashboard:team_update"
    delete_url_name = "dashboard:team_delete"
    reorder_url_name = "dashboard:team_reorder"
    breadcrumbs = [{"label": "People"}, {"label": "Team members"}]


TEAM_FIELDSETS = [
    ("Profile", ["name", "designation", "image", "quote", "biography"]),
    ("Contact", ["linkedin_url", "email"]),
    ("Display", ["order", "is_active"]),
]


class TeamCreateView(DashboardCreateView):
    model = TeamMember
    form_class = TeamMemberForm
    permission_required = "team.add_teammember"
    page_title = "Add team member"
    list_url_name = "dashboard:team_list"
    update_url_name = "dashboard:team_update"
    fieldsets = TEAM_FIELDSETS
    success_message = "Team member added."
    breadcrumbs = [{"label": "People"}, {"label": "Team members", "url": "dashboard:team_list"}, {"label": "Add"}]


class TeamUpdateView(DashboardUpdateView):
    model = TeamMember
    form_class = TeamMemberForm
    permission_required = "team.change_teammember"
    list_url_name = "dashboard:team_list"
    update_url_name = "dashboard:team_update"
    fieldsets = TEAM_FIELDSETS
    success_message = "Team member updated."
    breadcrumbs = [{"label": "People"}, {"label": "Team members", "url": "dashboard:team_list"}, {"label": "Edit"}]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit team member: {self.object.name}"
        context["preview_url"] = reverse("website:about")
        return context


class TeamDeleteView(DashboardDeleteView):
    model = TeamMember
    permission_required = "team.delete_teammember"
    list_url_name = "dashboard:team_list"
    success_message = "Team member deleted."


class TeamReorderView(ReorderView):
    model = TeamMember
    permission_required = "team.change_teammember"


class TeamToggleActiveView(ToggleFieldView):
    model = TeamMember
    field = "is_active"
    permission_required = "team.change_teammember"


# ------------------------------------------------------------------ enquiries
class EnquiryListView(DashboardListView):
    model = Enquiry
    permission_required = "enquiries.view_enquiry"
    page_title = "Enquiries"
    template_name = "dashboard/enquiries/list.html"
    columns = [
        {"label": "Name", "field": "name", "type": "title", "sortable": True},
        {"label": "Email", "field": "email"},
        {"label": "Phone", "field": "phone"},
        {"label": "Product / interest", "field": "product"},
        {"label": "Status", "field": "status", "type": "enquiry_status"},
        {"label": "Received", "field": "created_at", "type": "datetime", "sortable": True},
    ]
    search_fields = ["name", "email", "phone", "company", "city", "message", "collection_ref"]
    filters = [
        {"name": "status", "label": "Status", "choices": Enquiry.STATUS_CHOICES},
        {"name": "source", "label": "Source", "choices": Enquiry.SOURCE_CHOICES},
        {"name": "date_from", "label": "From", "type": "date_from", "lookup": "created_at"},
        {"name": "date_to", "label": "To", "type": "date_to", "lookup": "created_at"},
    ]
    default_ordering = "-created_at"
    update_url_name = "dashboard:enquiry_detail"
    delete_url_name = "dashboard:enquiry_delete"
    breadcrumbs = [{"label": "Leads"}, {"label": "Enquiries"}]
    empty_message = "No enquiries yet. They will appear here as soon as visitors submit the contact or product forms."

    def get_base_queryset(self):
        return Enquiry.objects.select_related("product")

    def row_actions(self, obj):
        actions = [{"label": "View", "url": reverse("dashboard:enquiry_detail", args=[obj.pk]), "icon": "eye"}]
        if self.request.user.has_perm("enquiries.delete_enquiry"):
            actions.append({"label": "Delete", "url": reverse("dashboard:enquiry_delete", args=[obj.pk]), "icon": "trash", "danger": True})
        return actions

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = Enquiry.objects.all()
        context["enquiry_stats"] = {
            "total": qs.count(),
            "new": qs.filter(status=Enquiry.STATUS_NEW).count(),
            "pending": qs.filter(status__in=Enquiry.PENDING_STATUSES).count(),
            "converted": qs.filter(status=Enquiry.STATUS_CONVERTED).count(),
        }
        return context


class EnquiryDetailView(DashboardPermissionMixin, DetailView):
    model = Enquiry
    permission_required = "enquiries.view_enquiry"
    template_name = "dashboard/enquiries/detail.html"

    def get_queryset(self):
        return Enquiry.objects.select_related("product__collection")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = kwargs.get("form") or EnquiryUpdateForm(instance=self.object)
        context["page_title"] = f"Enquiry from {self.object.name}"
        context["breadcrumbs"] = [{"label": "Leads"}, {"label": "Enquiries", "url": "dashboard:enquiry_list"}, {"label": self.object.name}]
        context["can_change"] = self.request.user.has_perm("enquiries.change_enquiry")
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm("enquiries.change_enquiry"):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        self.object = self.get_object()
        form = EnquiryUpdateForm(request.POST, instance=self.object)
        if form.is_valid():
            form.save()
            messages.success(request, "Enquiry updated.")
            return redirect("dashboard:enquiry_detail", pk=self.object.pk)
        messages.error(request, "Please fix the errors below.")
        return self.render_to_response(self.get_context_data(form=form))


class EnquiryDeleteView(DashboardDeleteView):
    model = Enquiry
    permission_required = "enquiries.delete_enquiry"
    list_url_name = "dashboard:enquiry_list"
    success_message = "Enquiry deleted."


class EnquiryStatusView(DashboardPermissionMixin, DetailView):
    """Quick status change from the list (POST)."""

    model = Enquiry
    permission_required = "enquiries.change_enquiry"
    http_method_names = ["post"]

    def post(self, request, pk):
        enquiry = get_object_or_404(Enquiry, pk=pk)
        status = request.POST.get("status")
        if status in dict(Enquiry.STATUS_CHOICES):
            enquiry.status = status
            enquiry.save(update_fields=["status", "updated_at"])
            messages.success(request, f"Enquiry marked as {enquiry.get_status_display()}.")
        from .base import _redirect_back

        return _redirect_back(request, "dashboard:enquiry_list")
