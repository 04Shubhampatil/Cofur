"""Rename the header menu's 'Communications' entry to 'Our Story'.

Top-level bar items are not editable from the CMS (only the Collections mega
menu is), so the rename travels with the code instead of being done by hand on
each environment.
"""
from django.db import migrations

OLD, NEW = "Communications", "Our Story"


def rename(apps, schema_editor):
    NavigationItem = apps.get_model("core", "NavigationItem")
    NavigationItem.objects.filter(label=OLD, menu__slug="header").update(label=NEW)


def unrename(apps, schema_editor):
    NavigationItem = apps.get_model("core", "NavigationItem")
    NavigationItem.objects.filter(label=NEW, menu__slug="header").update(label=OLD)


class Migration(migrations.Migration):

    dependencies = [("core", "0003_remove_media_library")]

    operations = [migrations.RunPython(rename, unrename)]
