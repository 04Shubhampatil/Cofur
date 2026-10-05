"""Point the Projects entries at the Projects page.

Migrations 0014 and 0015 added the item to the header and the footer with no
destination, because there was nothing to link to. There is now.

Only entries still set to "no link" are touched, so an editor who pointed one
somewhere else in the meantime keeps their choice.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    NavigationItem = apps.get_model("core", "NavigationItem")
    NavigationItem.objects.filter(label="Projects", parent__isnull=True, link_type="none").update(
        link_type="internal", internal_page="website:projects", url_suffix=""
    )


def backwards(apps, schema_editor):
    NavigationItem = apps.get_model("core", "NavigationItem")
    NavigationItem.objects.filter(label="Projects", parent__isnull=True, internal_page="website:projects").update(
        link_type="none", internal_page="", url_suffix=""
    )


class Migration(migrations.Migration):

    dependencies = [("core", "0015_footer_matches_header_nav")]

    operations = [migrations.RunPython(forwards, backwards)]
