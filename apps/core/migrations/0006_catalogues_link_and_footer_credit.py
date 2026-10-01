"""Point the Catalogues bar item at its own page, and add the Nivtech credit.

Both are content rather than schema, and neither is reachable from the CMS —
top-level menu items are not editable there, and a site that already stores the
old copyright line would otherwise keep it. Rows an editor has customised are
left alone: only the previous default is replaced.
"""
from django.db import migrations

OLD_COPYRIGHT = "Copyright © {year} COFUR Pvt. Ltd. All rights reserved."
NEW_COPYRIGHT = "Copyright © {year} COFUR Pvt. Ltd. All rights reserved | Develop by Nivtech."


def forwards(apps, schema_editor):
    NavigationItem = apps.get_model("core", "NavigationItem")
    NavigationItem.objects.filter(label="Catalogues", parent__isnull=True).update(
        link_type="internal", internal_page="website:catalogues", category=None, collection=None, product=None, external_url=""
    )
    SiteSettings = apps.get_model("core", "SiteSettings")
    SiteSettings.objects.filter(copyright_text=OLD_COPYRIGHT).update(copyright_text=NEW_COPYRIGHT)


def backwards(apps, schema_editor):
    NavigationItem = apps.get_model("core", "NavigationItem")
    NavigationItem.objects.filter(label="Catalogues", parent__isnull=True).update(
        link_type="internal", internal_page="website:collection_list"
    )
    SiteSettings = apps.get_model("core", "SiteSettings")
    SiteSettings.objects.filter(copyright_text=NEW_COPYRIGHT).update(copyright_text=OLD_COPYRIGHT)


class Migration(migrations.Migration):

    dependencies = [("core", "0005_alter_navigationitem_internal_page_and_more")]

    operations = [migrations.RunPython(forwards, backwards)]
