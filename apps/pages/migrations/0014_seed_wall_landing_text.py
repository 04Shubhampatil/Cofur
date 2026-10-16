from django.db import migrations

from apps.pages.landing_content import WALL_IMAGES, WALL_PAGE, WALL_TEXT


def seed(apps, schema_editor):
    LandingText = apps.get_model("pages", "LandingText")
    order = 0
    for key, label, text in WALL_TEXT:
        order += 1
        LandingText.objects.update_or_create(
            page=WALL_PAGE, key=key,
            defaults={"label": label, "value": text, "order": order},
        )
    for key, label, static_path in WALL_IMAGES:
        order += 1
        LandingText.objects.update_or_create(
            page=WALL_PAGE, key=key,
            defaults={"label": label, "default_image": static_path, "order": order},
        )


def unseed(apps, schema_editor):
    LandingText = apps.get_model("pages", "LandingText")
    LandingText.objects.filter(page=WALL_PAGE).delete()


class Migration(migrations.Migration):

    dependencies = [("pages", "0013_landingtext")]

    operations = [migrations.RunPython(seed, unseed)]
