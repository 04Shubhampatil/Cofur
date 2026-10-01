"""Point the Our Story bar item at the new posts section.

It used to jump to an anchor on the About page. Top-level menu items are not
editable from the CMS, so the change travels with the code. An item an editor
has already repointed somewhere else is left alone.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    NavigationItem = apps.get_model("core", "NavigationItem")
    NavigationItem.objects.filter(label="Our Story", parent__isnull=True, menu__slug="header", internal_page="website:about").update(
        internal_page="website:stories", url_suffix=""
    )


def backwards(apps, schema_editor):
    NavigationItem = apps.get_model("core", "NavigationItem")
    NavigationItem.objects.filter(label="Our Story", parent__isnull=True, menu__slug="header", internal_page="website:stories").update(
        internal_page="website:about", url_suffix="#sustainability"
    )


class Migration(migrations.Migration):

    dependencies = [("core", "0011_alter_navigationitem_internal_page")]

    operations = [migrations.RunPython(forwards, backwards)]
