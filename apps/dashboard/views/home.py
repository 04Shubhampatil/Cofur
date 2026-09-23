from django.views.generic import TemplateView

from apps.catalog.models import Category, Collection, Product
from apps.enquiries.models import Enquiry
from apps.team.models import TeamMember

from ..mixins import StaffRequiredMixin


class DashboardIndexView(StaffRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        enquiries = Enquiry.objects.all()
        context.update({
            "page_title": "Dashboard",
            "stats": [
                {"label": "Total products", "value": Product.objects.count(), "url": "dashboard:product_list", "icon": "box", "perm": "catalog.view_product"},
                {"label": "Sub-categories", "value": Collection.objects.count(), "url": "dashboard:collection_list", "icon": "layers", "perm": "catalog.view_collection"},
                {"label": "Categories", "value": Category.objects.count(), "url": "dashboard:category_list", "icon": "grid", "perm": "catalog.view_category"},
                {"label": "Total enquiries", "value": enquiries.count(), "url": "dashboard:enquiry_list", "icon": "mail", "perm": "enquiries.view_enquiry"},
                {"label": "Featured products", "value": Product.objects.filter(is_featured=True).count(), "url": "dashboard:product_list", "icon": "star", "perm": "catalog.view_product", "query": "?featured=1"},
                {"label": "Active team members", "value": TeamMember.objects.filter(is_active=True).count(), "url": "dashboard:team_list", "icon": "users", "perm": "team.view_teammember"},
            ],
            "enquiry_stats": {
                "total": enquiries.count(),
                "new": enquiries.filter(status=Enquiry.STATUS_NEW).count(),
                "pending": enquiries.filter(status__in=Enquiry.PENDING_STATUSES).count(),
                "converted": enquiries.filter(status=Enquiry.STATUS_CONVERTED).count(),
            },
            "recent_products": Product.objects.select_related("collection").order_by("-created_at")[:5],
            "updated_products": Product.objects.select_related("collection").order_by("-updated_at")[:5],
            "recent_enquiries": enquiries.select_related("product")[:6],
            "recent_collections": Collection.objects.order_by("-created_at")[:5],
            "quick_actions": [
                {"label": "Add product", "url": "dashboard:product_create", "perm": "catalog.add_product", "icon": "plus"},
                {"label": "Add sub-category", "url": "dashboard:collection_create", "perm": "catalog.add_collection", "icon": "plus"},
                {"label": "Add category", "url": "dashboard:category_create", "perm": "catalog.add_category", "icon": "plus"},
                {"label": "Add team member", "url": "dashboard:team_create", "perm": "team.add_teammember", "icon": "plus"},
                {"label": "View enquiries", "url": "dashboard:enquiry_list", "perm": "enquiries.view_enquiry", "icon": "mail"},
                {"label": "Edit home page", "url": "dashboard:page_home", "perm": "pages.change_homepage", "icon": "home"},
                {"label": "Edit about page", "url": "dashboard:page_about", "perm": "pages.change_aboutpage", "icon": "info"},
                {"label": "Edit contact page", "url": "dashboard:page_contact", "perm": "pages.change_contactpage", "icon": "phone"},
            ],
        })
        context["stats"] = [s for s in context["stats"] if user.has_perm(s["perm"])]
        context["quick_actions"] = [a for a in context["quick_actions"] if user.has_perm(a["perm"])]
        return context
