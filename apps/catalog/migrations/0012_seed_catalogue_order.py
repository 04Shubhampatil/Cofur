"""Seed the new Catalogues page position from the existing order.

`catalogue_order` defaults to 0, so without this every card would land on the
same position and the rail would fall back to insertion order. Copying the
home rail order keeps the page looking exactly as it does today; an editor can
diverge the two afterwards.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    for position, category in enumerate(Category.objects.order_by("order", "pk")):
        if category.catalogue_order != position:
            category.catalogue_order = position
            category.save(update_fields=["catalogue_order"])


def backwards(apps, schema_editor):
    # The column goes away with the schema migration; nothing to restore.
    pass


class Migration(migrations.Migration):

    dependencies = [("catalog", "0011_catalogue_section_controls")]

    operations = [migrations.RunPython(forwards, backwards)]
