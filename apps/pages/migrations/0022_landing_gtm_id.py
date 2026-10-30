from django.db import migrations

# A campaign page can report to its own Tag Manager container instead of the
# site's. Empty means "use the site's", which is what both pages start with.
PAGES = ["wall", "ceilings"]

ROW = (
    "gtm_id",
    "Google Tag Manager ID (optional — leave empty to use the site's)",
)


def seed(apps, schema_editor):
    LandingText = apps.get_model("pages", "LandingText")
    key, label = ROW
    for page in PAGES:
        LandingText.objects.update_or_create(
            page=page, key=key, defaults={"label": label, "value": "", "order": 970},
        )


def unseed(apps, schema_editor):
    LandingText = apps.get_model("pages", "LandingText")
    LandingText.objects.filter(page__in=PAGES, key=ROW[0]).delete()


class Migration(migrations.Migration):

    dependencies = [("pages", "0021_landing_ceiling_product_urls")]

    operations = [migrations.RunPython(seed, unseed)]
