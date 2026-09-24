from django.urls import reverse

from apps.enquiries.models import Enquiry


def dashboard_nav(request):
    """Sidebar definition filtered by the user's permissions."""
    if not request.path.startswith("/admin/") or not request.user.is_authenticated:
        return {}
    user = request.user

    def item(label, url_name, perm=None, icon="dot", match=None):
        if perm and not user.has_perm(perm):
            return None
        url = reverse(url_name)
        return {"label": label, "url": url, "icon": icon, "active": request.path.startswith(match or url)}

    sections = [
        {"title": "", "items": [item("Dashboard", "dashboard:index", icon="home", match="/admin/$")]},
        {"title": "Content", "items": [
            item("Home page", "dashboard:page_home", "pages.view_homepage", "layout"),
            item("About page", "dashboard:page_about", "pages.view_aboutpage", "info"),
            item("Contact page", "dashboard:page_contact", "pages.view_contactpage", "phone"),
            item("Footer", "dashboard:footer_settings", "core.view_sitesettings", "layout"),
            item("Collections menu", "dashboard:mega_menu", "core.view_navigationitem", "menu"),
        ]},
        {"title": "Products Master", "items": [
            item("Categories", "dashboard:category_list", "catalog.view_category", "grid"),
            item("Sub-Categories", "dashboard:collection_list", "catalog.view_collection", "layers"),
            item("Products", "dashboard:product_list", "catalog.view_product", "box"),
        ]},
        {"title": "People", "items": [item("Team members", "dashboard:team_list", "team.view_teammember", "users")]},
        {"title": "Leads", "items": [item("Enquiries", "dashboard:enquiry_list", "enquiries.view_enquiry", "mail")]},
        {"title": "Settings", "items": [
            item("Site settings", "dashboard:site_settings", "core.view_sitesettings", "settings"),
        ]},
    ]
    for section in sections:
        section["items"] = [i for i in section["items"] if i]
        if section["items"] and section["items"][0]["url"] == reverse("dashboard:index"):
            section["items"][0]["active"] = request.path == reverse("dashboard:index")
    sections = [s for s in sections if s["items"]]
    new_enquiries = Enquiry.objects.filter(status=Enquiry.STATUS_NEW).count() if user.has_perm("enquiries.view_enquiry") else 0
    return {"sidebar_sections": sections, "new_enquiry_count": new_enquiries}
