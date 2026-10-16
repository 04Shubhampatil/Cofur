from django.db import migrations

# Migration 0018 pointed every ceiling card at a category page, because the
# seven designs looked as though they had no product pages. They do:
# /products/wave/ and friends. This sends each card to its own product.
#
# Only rows still holding 0018's address are changed, so a link somebody has
# already edited in the admin panel is left exactly as they set it.
CEILINGS = "ceilings"

OLD_URL = "/categories/acoustic-ceilings/"

DESIGN_URLS = [
    (1, "/products/wave/"),
    (2, "/products/petal/"),
    (3, "/products/blade/"),
    (4, "/products/planks/"),
    (5, "/products/grid/"),
    (6, "/products/waffle/"),
    (7, "/products/hive/"),
]


def point_at_products(apps, schema_editor):
    LandingText = apps.get_model("pages", "LandingText")
    for index, url in DESIGN_URLS:
        LandingText.objects.filter(
            page=CEILINGS, key=f"design_{index}_url", value__in=[OLD_URL, ""],
        ).update(value=url)


def point_at_category(apps, schema_editor):
    LandingText = apps.get_model("pages", "LandingText")
    for index, url in DESIGN_URLS:
        LandingText.objects.filter(
            page=CEILINGS, key=f"design_{index}_url", value=url,
        ).update(value=OLD_URL)


class Migration(migrations.Migration):

    dependencies = [("pages", "0020_landing_seo_labels")]

    operations = [migrations.RunPython(point_at_products, point_at_category)]
