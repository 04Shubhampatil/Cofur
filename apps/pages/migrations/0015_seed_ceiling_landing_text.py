from django.db import migrations

from apps.pages.landing_content_ceilings import CEILING_IMAGES, CEILING_PAGE, CEILING_TEXT, CEILING_TEXT_EXTRA


def seed(apps, schema_editor):
    LandingText = apps.get_model("pages", "LandingText")
    order = 0
    for key, label, text in CEILING_TEXT:
        order += 1
        LandingText.objects.update_or_create(
            page=CEILING_PAGE, key=key,
            defaults={"label": label, "value": text, "order": order},
        )
    for key, label, text in CEILING_TEXT_EXTRA:
        order += 1
        LandingText.objects.update_or_create(
            page=CEILING_PAGE, key=key,
            defaults={"label": label, "value": text, "order": order},
        )
    for key, label, static_path in CEILING_IMAGES:
        order += 1
        LandingText.objects.update_or_create(
            page=CEILING_PAGE, key=key,
            defaults={"label": label, "default_image": static_path, "order": order},
        )


def unseed(apps, schema_editor):
    LandingText = apps.get_model("pages", "LandingText")
    LandingText.objects.filter(page=CEILING_PAGE).delete()


class Migration(migrations.Migration):

    dependencies = [("pages", "0014_seed_wall_landing_text")]

    operations = [migrations.RunPython(seed, unseed)]
