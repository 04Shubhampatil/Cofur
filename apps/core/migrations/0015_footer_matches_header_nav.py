"""Bring the footer nav in line with the header bar.

The footer kept "Communications" pointing at an anchor on the About page,
which is what migration 0013 deliberately restored — at the time the live
footer was the reference and the rename was an accident. The ask now is the
opposite: the two menus should read the same. So the footer gets "Our Story"
and the new "Projects" entry too.

"Collections" is left alone. In the header it is the mega-menu trigger and
links nowhere; in the footer it has to be an ordinary link, so it keeps its
own target.
"""
from django.db import migrations
from django.db.models import F

PROJECTS = "Projects"


def forwards(apps, schema_editor):
    NavigationMenu = apps.get_model("core", "NavigationMenu")
    NavigationItem = apps.get_model("core", "NavigationItem")
    menu = NavigationMenu.objects.filter(slug="footer").first()
    if menu is None:
        return
    top_level = NavigationItem.objects.filter(menu=menu, parent__isnull=True)

    top_level.filter(label="Communications").update(
        label="Our Story", internal_page="website:stories", url_suffix=""
    )

    if not top_level.filter(label=PROJECTS).exists():
        contact = top_level.filter(label="Contact").first()
        if contact is None:
            position = (top_level.order_by("-order").values_list("order", flat=True).first() or 0) + 1
        else:
            position = contact.order
            top_level.filter(order__gte=position).update(order=F("order") + 1)
        NavigationItem.objects.create(
            menu=menu, parent=None, label=PROJECTS, link_type="none",
            internal_page="", url_suffix="", order=position, is_active=True,
        )


def backwards(apps, schema_editor):
    NavigationMenu = apps.get_model("core", "NavigationMenu")
    NavigationItem = apps.get_model("core", "NavigationItem")
    menu = NavigationMenu.objects.filter(slug="footer").first()
    if menu is None:
        return
    top_level = NavigationItem.objects.filter(menu=menu, parent__isnull=True)

    projects = top_level.filter(label=PROJECTS).first()
    if projects is not None:
        position = projects.order
        projects.delete()
        top_level.filter(order__gt=position).update(order=F("order") - 1)

    top_level.filter(label="Our Story").update(
        label="Communications", internal_page="website:about", url_suffix="#sustainability"
    )


class Migration(migrations.Migration):

    dependencies = [("core", "0014_projects_menu_item")]

    operations = [migrations.RunPython(forwards, backwards)]
