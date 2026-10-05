"""CMS screens for the Our Story posts."""
from ..forms import SEO_FIELDS, StoryForm, StoryImageFormSet
from .base import DashboardCreateView, DashboardDeleteView, DashboardListView, DashboardUpdateView

from apps.stories.models import Story

STORY_CRUMB = {"label": "Our Story"}
STORY_FIELDSETS = [
    ("Post", ["title", "slug", "kind", "status", "published_at"]),
    ("Cover", ["cover_image", "cover_alt"]),
    ("Writing", ["excerpt", "body"]),
    ("SEO", SEO_FIELDS),
]
# The cover leads the slider; these follow it in order. One photograph means
# no slider at all, so a post that never needs one is unaffected.
STORY_FORMSETS = {"images": (StoryImageFormSet, "More photographs", "photograph")}


class StoryListView(DashboardListView):
    model = Story
    permission_required = "stories.view_story"
    page_title = "Posts"
    columns = [
        {"label": "Cover", "field": "cover_image", "type": "image"},
        {"label": "Title", "field": "title", "type": "title", "sortable": True},
        {"label": "Category", "field": "get_kind_display"},
        {"label": "Status", "field": "status", "type": "status"},
        {"label": "Published", "field": "published_at", "type": "date", "sortable": True},
    ]
    search_fields = ["title", "excerpt", "body"]
    filters = [
        {"name": "kind", "label": "Category", "choices": Story.KIND_CHOICES},
        {"name": "status", "label": "Status", "choices": Story.STATUS_CHOICES},
    ]
    default_ordering = "-published_at"
    create_url_name = "dashboard:story_create"
    update_url_name = "dashboard:story_update"
    delete_url_name = "dashboard:story_delete"
    breadcrumbs = [STORY_CRUMB, {"label": "Posts"}]
    empty_message = "No posts yet. Write the first one."


class StoryCreateView(DashboardCreateView):
    model = Story
    form_class = StoryForm
    permission_required = "stories.add_story"
    page_title = "New post"
    list_url_name = "dashboard:story_list"
    update_url_name = "dashboard:story_update"
    fieldsets = STORY_FIELDSETS
    formset_classes = STORY_FORMSETS
    success_message = "Post created."
    breadcrumbs = [STORY_CRUMB, {"label": "Posts", "url": "dashboard:story_list"}, {"label": "New"}]


class StoryUpdateView(DashboardUpdateView):
    model = Story
    form_class = StoryForm
    permission_required = "stories.change_story"
    list_url_name = "dashboard:story_list"
    update_url_name = "dashboard:story_update"
    fieldsets = STORY_FIELDSETS
    formset_classes = STORY_FORMSETS
    success_message = "Post updated."
    breadcrumbs = [STORY_CRUMB, {"label": "Posts", "url": "dashboard:story_list"}, {"label": "Edit"}]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit post: {self.object.title}"
        if self.object.status == Story.STATUS_PUBLISHED:
            context["preview_url"] = self.object.get_absolute_url()
        return context


class StoryDeleteView(DashboardDeleteView):
    model = Story
    permission_required = "stories.delete_story"
    list_url_name = "dashboard:story_list"
    success_message = "Post deleted."
