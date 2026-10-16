from django.db import migrations

# How each landing page describes itself to Google and to social networks.
# Seeded with the wording the pages already used, so nothing changes until
# someone edits it in the admin panel. Blank rows fall back: the social title
# and description reuse the search listing, and the share image reuses the
# site-wide Open Graph image from Settings.
SEO_TEXT = {
    "wall": [
        ("seo_title", "Search listing: page title (about 60 characters)",
         "Acoustic Wall Panels for Offices | COFUR India"),
        ("seo_description", "Search listing: description (about 155 characters)",
         "Explore COFUR acoustic wall panel designs for commercial offices, meeting rooms "
         "and workplace interiors. Enquire about grooved, printed and fluted wall panels "
         "for your project."),
        ("seo_keywords", "Search listing: keywords (optional)", ""),
        ("seo_og_title", "Social share: title (optional — leave empty to reuse the page title)", ""),
        ("seo_og_description", "Social share: description (optional — leave empty to reuse the description)", ""),
    ],
    "ceilings": [
        ("seo_title", "Search listing: page title (about 60 characters)",
         "Acoustic Ceilings for Commercial Offices | COFUR"),
        ("seo_description", "Search listing: description (about 155 characters)",
         "Acoustic ceilings for commercial offices, corporate workplaces and modern "
         "interiors. Explore Wave, Petal, Blade, Planks, Grid, Waffle and Hive acoustic "
         "ceiling designs by COFUR."),
        ("seo_keywords", "Search listing: keywords (optional)", ""),
        ("seo_og_title", "Social share: title (optional — leave empty to reuse the page title)", ""),
        ("seo_og_description", "Social share: description (optional — leave empty to reuse the description)", ""),
    ],
}

# One upload per page: the picture used when the link is shared.
SEO_IMAGE = ("img_seo_share", "Social share image (1200 × 630, optional)")


def seed(apps, schema_editor):
    LandingText = apps.get_model("pages", "LandingText")
    for page, rows in SEO_TEXT.items():
        for offset, (key, label, text) in enumerate(rows, start=1):
            LandingText.objects.update_or_create(
                page=page, key=key,
                defaults={"label": label, "value": text, "order": 950 + offset},
            )
        key, label = SEO_IMAGE
        LandingText.objects.update_or_create(
            page=page, key=key,
            defaults={"label": label, "order": 950 + len(rows) + 1},
        )


def unseed(apps, schema_editor):
    LandingText = apps.get_model("pages", "LandingText")
    keys = [key for rows in SEO_TEXT.values() for key, _, _ in rows] + [SEO_IMAGE[0]]
    for page in SEO_TEXT:
        LandingText.objects.filter(page=page, key__in=keys).delete()


class Migration(migrations.Migration):

    dependencies = [("pages", "0016_landing_form_text")]

    operations = [migrations.RunPython(seed, unseed)]
