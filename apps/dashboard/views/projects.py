"""CMS screens for the Projects section.

A project is the page plus the facts panel, the carousel and the row of product
cards. The facts and the carousel are edited inline; the cards are one
multi-select on the form itself, since a card is nothing but a product.
"""
from apps.projects.models import Project

from ..forms import SEO_FIELDS, ProjectCarouselFormSet, ProjectFactFormSet, ProjectForm
from .base import (
    DashboardCreateView,
    DashboardDeleteView,
    DashboardListView,
    DashboardUpdateView,
    ReorderView,
    ToggleFieldView,
)

PROJECT_CRUMB = {"label": "Projects"}
PROJECT_FIELDSETS = [
    ("Project", ["title", "slug", "status", "order", "studio"]),
    ("Card", ["cover_image", "cover_alt"]),
    ("Written section", ["body_heading", "body"]),
    ("More from this project", ["gallery_heading", "cards"]),
    ("SEO", SEO_FIELDS),
]
PROJECT_FORMSETS = {
    "facts": (ProjectFactFormSet, "Project details", "detail"),
    "carousel": (ProjectCarouselFormSet, "Carousel photographs", "photograph"),
}


class ProjectListView(DashboardListView):
    model = Project
    permission_required = "projects.view_project"
    page_title = "Projects"
    columns = [
        {"label": "Cover", "field": "cover_image", "type": "image"},
        {"label": "Title", "field": "title", "type": "title", "sortable": True},
        {"label": "Studio / client", "field": "studio"},
        {"label": "Status", "field": "status", "type": "status"},
    ]
    search_fields = ["title", "studio", "body"]
    filters = [{"name": "status", "label": "Status", "choices": Project.STATUS_CHOICES}]
    create_url_name = "dashboard:project_create"
    update_url_name = "dashboard:project_update"
    delete_url_name = "dashboard:project_delete"
    reorder_url_name = "dashboard:project_reorder"
    breadcrumbs = [PROJECT_CRUMB, {"label": "All projects"}]
    empty_message = "No projects yet. Add the first one."


class ProjectCreateView(DashboardCreateView):
    model = Project
    form_class = ProjectForm
    permission_required = "projects.add_project"
    page_title = "New project"
    list_url_name = "dashboard:project_list"
    update_url_name = "dashboard:project_update"
    fieldsets = PROJECT_FIELDSETS
    formset_classes = PROJECT_FORMSETS
    success_message = "Project created."
    breadcrumbs = [PROJECT_CRUMB, {"label": "All projects", "url": "dashboard:project_list"}, {"label": "New"}]


class ProjectUpdateView(DashboardUpdateView):
    model = Project
    form_class = ProjectForm
    permission_required = "projects.change_project"
    list_url_name = "dashboard:project_list"
    update_url_name = "dashboard:project_update"
    fieldsets = PROJECT_FIELDSETS
    formset_classes = PROJECT_FORMSETS
    success_message = "Project updated."
    breadcrumbs = [PROJECT_CRUMB, {"label": "All projects", "url": "dashboard:project_list"}, {"label": "Edit"}]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit project: {self.object.title}"
        if self.object.status == Project.STATUS_PUBLISHED:
            context["preview_url"] = self.object.get_absolute_url()
        return context


class ProjectDeleteView(DashboardDeleteView):
    model = Project
    permission_required = "projects.delete_project"
    list_url_name = "dashboard:project_list"
    success_message = "Project deleted."


class ProjectReorderView(ReorderView):
    model = Project
    permission_required = "projects.change_project"


class ProjectTogglePublishView(ToggleFieldView):
    model = Project
    field = "status"
    permission_required = "projects.change_project"

    def post(self, request, pk, *args, **kwargs):
        # status is a choice, not a boolean, so the base toggle cannot flip it
        project = self.model._default_manager.filter(pk=pk).first()
        if project is None:
            from django.http import JsonResponse

            return JsonResponse({"ok": False, "error": "Not found"}, status=404)
        project.status = (
            Project.STATUS_DRAFT if project.status == Project.STATUS_PUBLISHED else Project.STATUS_PUBLISHED
        )
        project.save(update_fields=["status", "updated_at"])
        from .base import _redirect_back

        return _redirect_back(request)
