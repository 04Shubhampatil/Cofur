from django.db import migrations

# The rest of the meta tags, per landing page. Both start blank: the page is
# then indexed the way the whole site is, and points at its own address.
META_ROWS = [
    ("seo_robots", "Search engines: allow indexing (leave empty to follow the site setting)"),
    ("seo_canonical", "Canonical address (leave empty to use this page's own address)"),
]

PAGES = ["wall", "ceilings"]


def seed(apps, schema_editor):
    LandingText = apps.get_model("pages", "LandingText")
    for page in PAGES:
        for offset, (key, label) in enumerate(META_ROWS, start=1):
            LandingText.objects.update_or_create(
                page=page, key=key,
                defaults={"label": label, "value": "", "order": 956 + offset},
            )


def unseed(apps, schema_editor):
    LandingText = apps.get_model("pages", "LandingText")
    LandingText.objects.filter(page__in=PAGES, key__in=[key for key, _ in META_ROWS]).delete()


class Migration(migrations.Migration):

    dependencies = [("pages", "0018_landing_ceiling_product_links")]

    operations = [migrations.RunPython(seed, unseed)]
