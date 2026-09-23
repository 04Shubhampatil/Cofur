from django.conf import settings

from .models import NavigationMenu, SiteSettings


def site_context(request):
    """Expose site settings and navigation to every template."""
    site = SiteSettings.load()
    menus = {menu.slug: menu for menu in NavigationMenu.objects.prefetch_related("items__children")}
    header_menu = menus.get("header")
    footer_menu = menus.get("footer")
    header_items = list(header_menu.top_level_items()) if header_menu else []
    footer_items = list(footer_menu.top_level_items()) if footer_menu else []
    return {
        "site": site,
        "header_menu_items": header_items,
        "footer_menu_items": footer_items,
        "DEBUG": settings.DEBUG,
    }
