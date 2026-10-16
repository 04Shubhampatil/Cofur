from django.db import migrations

# Name the landing pages' SEO fields the way every other editor in the CMS
# names them (the product and category forms), so the panel reads the same
# wherever you are. (key, label, order) — the order matches those forms too.
SEO_LABELS = [
    ("seo_title", "SEO title", 951),
    ("seo_description", "Meta description", 952),
    ("seo_keywords", "Meta keywords", 953),
    ("seo_og_title", "Open Graph title", 954),
    ("seo_og_description", "Open Graph description", 955),
    ("img_seo_share", "Open Graph image", 956),
    ("seo_canonical", "Canonical url", 957),
    ("seo_robots", "Robots", 958),
]

PAGES = ["wall", "ceilings"]

# What they were called before, in case this migration is rolled back.
PREVIOUS_LABELS = [
    ("seo_title", "Search listing: page title (about 60 characters)", 951),
    ("seo_description", "Search listing: description (about 155 characters)", 952),
    ("seo_keywords", "Search listing: keywords (optional)", 953),
    ("seo_og_title", "Social share: title (optional — leave empty to reuse the page title)", 954),
    ("seo_og_description", "Social share: description (optional — leave empty to reuse the description)", 955),
    ("img_seo_share", "Social share image (1200 × 630, optional)", 956),
    ("seo_robots", "Search engines: allow indexing (leave empty to follow the site setting)", 957),
    ("seo_canonical", "Canonical address (leave empty to use this page's own address)", 958),
]


def apply(rows, LandingText):
    for page in PAGES:
        for key, label, order in rows:
            LandingText.objects.filter(page=page, key=key).update(label=label, order=order)


def rename(apps, schema_editor):
    apply(SEO_LABELS, apps.get_model("pages", "LandingText"))


def restore(apps, schema_editor):
    apply(PREVIOUS_LABELS, apps.get_model("pages", "LandingText"))


class Migration(migrations.Migration):

    dependencies = [("pages", "0019_landing_seo_meta")]

    operations = [migrations.RunPython(rename, restore)]
