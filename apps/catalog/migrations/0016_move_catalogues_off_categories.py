"""Give every existing catalogue card a record of its own.

The cards lived on ``Category`` — a catalogue existed because a range did, and
there was no way to add one without inventing a range. This copies each card
into ``Catalogue`` and leaves the categories alone; the old columns are dropped
in the next migration, once the content is safely across.

Slugs are carried over unchanged so a link already handed out, such as
``/catalogues/soft-seating/preview/``, keeps working.

Only categories that actually read as a catalogue move: one shown on the page,
or one carrying a PDF. A range that was never part of the section does not
become an empty card.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    Category = apps.get_model("catalog", "Category")
    Catalogue = apps.get_model("catalog", "Catalogue")

    if Catalogue.objects.exists():
        return

    sources = Category.objects.filter(show_on_catalogues=True) | Category.objects.exclude(catalogue_pdf="")
    for category in sources.distinct().order_by("catalogue_order", "pk"):
        Catalogue.objects.create(
            title=category.catalogue_title or category.name,
            slug=category.slug,
            subtitle=category.catalogue_subtitle or category.subtitle,
            # The card's own picture, else whatever the range showed on its card.
            image=category.catalogue_image.name or category.thumbnail_image.name or category.banner_image.name or "",
            pdf=category.catalogue_pdf.name or "",
            category=category,
            order=category.catalogue_order,
            # A card was only on the page when both switches were on.
            is_active=bool(category.is_active and category.show_on_catalogues),
        )


def backwards(apps, schema_editor):
    """Write the cards back onto their categories, then empty the table.

    Only a catalogue that still points at a category can go back; one added
    after the split has nowhere to return to and is dropped, which is the
    honest outcome of undoing the split.
    """
    Catalogue = apps.get_model("catalog", "Catalogue")

    for catalogue in Catalogue.objects.select_related("category"):
        category = catalogue.category
        if category is None:
            continue
        category.catalogue_title = catalogue.title
        category.catalogue_subtitle = catalogue.subtitle
        category.catalogue_image = catalogue.image.name or ""
        category.catalogue_pdf = catalogue.pdf.name or ""
        category.catalogue_order = catalogue.order
        category.show_on_catalogues = catalogue.is_active
        category.save(update_fields=[
            "catalogue_title", "catalogue_subtitle", "catalogue_image",
            "catalogue_pdf", "catalogue_order", "show_on_catalogues",
        ])
    Catalogue.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0015_catalogue_model"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
