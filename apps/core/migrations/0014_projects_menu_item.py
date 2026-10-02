"""Add a Projects entry to the header bar, with no destination yet.

Top-level bar items are not editable from the CMS (only the Collections mega
menu is), so the entry travels with the code. ``link_type="none"`` is the
model's own "No link (heading / dropdown)" choice, and ``get_url()`` returns
"#" for it — the item shows in the bar and goes nowhere until a page exists.

It sits between Catalogues and Contact, so Contact stays last.
"""
from django.db import migrations
from django.db.models import F

LABEL = "Projects"


def forwards(apps, schema_editor):
    NavigationMenu = apps.get_model("core", "NavigationMenu")
    NavigationItem = apps.get_model("core", "NavigationItem")
    menu = NavigationMenu.objects.filter(slug="header").first()
    if menu is None:
        return

    top_level = NavigationItem.objects.filter(menu=menu, parent__isnull=True)
    if top_level.filter(label=LABEL).exists():
        return

    contact = top_level.filter(label="Contact").first()
    if contact is None:
        position = (top_level.order_by("-order").values_list("order", flat=True).first() or 0) + 1
    else:
        # shift Contact and anything after it along, so Contact stays last
        position = contact.order
        top_level.filter(order__gte=position).update(order=F("order") + 1)

    NavigationItem.objects.create(
        menu=menu,
        parent=None,
        label=LABEL,
        link_type="none",
        internal_page="",
        url_suffix="",
        order=position,
        is_active=True,
    )


def backwards(apps, schema_editor):
    NavigationMenu = apps.get_model("core", "NavigationMenu")
    NavigationItem = apps.get_model("core", "NavigationItem")
    menu = NavigationMenu.objects.filter(slug="header").first()
    if menu is None:
        return
    top_level = NavigationItem.objects.filter(menu=menu, parent__isnull=True)
    projects = top_level.filter(label=LABEL).first()
    if projects is None:
        return
    position = projects.order
    projects.delete()
    # close the gap, so a down/up cycle leaves the orders where it found them
    top_level.filter(order__gt=position).update(order=F("order") - 1)


class Migration(migrations.Migration):

    dependencies = [("core", "0013_restore_footer_communications_item")]

    operations = [migrations.RunPython(forwards, backwards)]
