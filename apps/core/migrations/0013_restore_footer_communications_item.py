"""Put the footer's 'Communications' entry back.

Migrations 0004 and 0012 renamed and repointed the bar item, but both filtered
on label alone, so they also caught the footer menu's entry — the rename was
only ever asked for on the header bar. Both are scoped to the header now; this
repairs any database that already ran the broad versions. On a database that
never did, nothing matches and this is a no-op.
"""
from django.db import migrations


def restore(apps, schema_editor):
    NavigationItem = apps.get_model("core", "NavigationItem")
    NavigationItem.objects.filter(label="Our Story", menu__slug="footer").update(
        label="Communications", internal_page="website:about", url_suffix="#sustainability"
    )


def unrestore(apps, schema_editor):
    NavigationItem = apps.get_model("core", "NavigationItem")
    NavigationItem.objects.filter(label="Communications", menu__slug="footer").update(
        label="Our Story", internal_page="website:stories", url_suffix=""
    )


class Migration(migrations.Migration):

    dependencies = [("core", "0012_our_story_menu_link")]

    operations = [migrations.RunPython(restore, unrestore)]
