"""Fill the catalogue card fields in from each category.

The fields fall back to the category when blank, so the page looked right
already — but the editor opened on three empty boxes and had to infer what
the card was showing. Seeding them means the form shows the real content,
which is the thing an editor is there to change.

Only blank fields are touched, so anything already written by hand survives.
The image points at the category's existing file rather than copying it; the
two are separate from here on, and uploading a new one on either side leaves
the other alone.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    for category in Category.objects.all():
        changed = []
        if not category.catalogue_title and category.name:
            category.catalogue_title = category.name
            changed.append("catalogue_title")
        if not category.catalogue_subtitle and category.subtitle:
            category.catalogue_subtitle = category.subtitle
            changed.append("catalogue_subtitle")
        if not category.catalogue_image:
            source = category.thumbnail_image.name or category.banner_image.name
            if source:
                category.catalogue_image.name = source
                changed.append("catalogue_image")
        if changed:
            category.save(update_fields=changed)


def backwards(apps, schema_editor):
    """Empty the seeded fields again, returning every card to the fallback.

    This cannot tell a seeded value from one an editor typed, so it clears
    only those that still match the category they were copied from.
    """
    Category = apps.get_model("catalog", "Category")
    for category in Category.objects.all():
        changed = []
        if category.catalogue_title == category.name:
            category.catalogue_title = ""
            changed.append("catalogue_title")
        if category.catalogue_subtitle == category.subtitle:
            category.catalogue_subtitle = ""
            changed.append("catalogue_subtitle")
        if category.catalogue_image.name in {category.thumbnail_image.name, category.banner_image.name}:
            category.catalogue_image = None
            changed.append("catalogue_image")
        if changed:
            category.save(update_fields=changed)


class Migration(migrations.Migration):

    dependencies = [("catalog", "0013_catalogue_card_content")]

    operations = [migrations.RunPython(forwards, backwards)]
