from django.db import migrations

CEILINGS = "ceilings"

# Where each ceiling design's "View product details" link goes. The seven
# designs have no product pages of their own in the catalogue yet, so every
# card starts out pointing at the Acoustic Ceilings category page. When a
# design gets its own product page, change that card's link in the admin
# panel — no code change needed.
DEFAULT_URL = "/categories/acoustic-ceilings/"

LINK_TEXT = ("design_link", "Designs: details link", "View product details")

DESIGNS = ["Wave", "Petal", "Blade", "Planks", "Grid", "Waffle", "Hive"]


def seed(apps, schema_editor):
    LandingText = apps.get_model("pages", "LandingText")
    rows = LandingText.objects.filter(page=CEILINGS)

    def order_of(key, fallback):
        row = rows.filter(key=key).first()
        return row.order if row else fallback

    key, label, text = LINK_TEXT
    LandingText.objects.update_or_create(
        page=CEILINGS, key=key,
        defaults={"label": label, "value": text, "order": order_of("design_enquire", 22)},
    )
    for index, design in enumerate(DESIGNS, start=1):
        LandingText.objects.update_or_create(
            page=CEILINGS, key=f"design_{index}_url",
            defaults={
                "label": f"{design}: product page link",
                "value": DEFAULT_URL,
                "order": order_of(f"design_{index}_copy", 66 + index),
            },
        )


def unseed(apps, schema_editor):
    LandingText = apps.get_model("pages", "LandingText")
    keys = [LINK_TEXT[0]] + [f"design_{index}_url" for index in range(1, len(DESIGNS) + 1)]
    LandingText.objects.filter(page=CEILINGS, key__in=keys).delete()


class Migration(migrations.Migration):

    dependencies = [("pages", "0017_landing_seo_text")]

    operations = [migrations.RunPython(seed, unseed)]
