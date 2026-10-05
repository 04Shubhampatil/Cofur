"""Rename the "Our Story" bar entry to "Stories".

Both menus, because 0015 made the footer mirror the header and leaving one
behind would undo that. Only the label changes — the item still points at the
same page, and the URL /our-story/ is untouched so existing links keep working.
"""
from django.db import migrations

OLD, NEW = "Our Story", "Stories"


def forwards(apps, schema_editor):
    NavigationItem = apps.get_model("core", "NavigationItem")
    NavigationItem.objects.filter(label=OLD, parent__isnull=True).update(label=NEW)


def backwards(apps, schema_editor):
    NavigationItem = apps.get_model("core", "NavigationItem")
    NavigationItem.objects.filter(label=NEW, parent__isnull=True).update(label=OLD)


class Migration(migrations.Migration):

    dependencies = [("core", "0017_alter_navigationitem_internal_page")]

    operations = [migrations.RunPython(forwards, backwards)]
