"""Point the new mobile fields at the portrait crops that already shipped.

The statement section and the "What makes COFUR different" picture only ever
had a desktop field, so a phone was served a 3:1 or 3:2 landscape crop and
showed a letterboxed strip. Portrait versions of both have been sitting in
``static/images`` since the original static site; this copies them into media
storage and attaches them, so existing installs pick the change up without a
reseed.

Only blank fields are filled, so anything uploaded by hand survives. The
statement lines are matched on ``order`` because that is what decides which
picture goes with which line.
"""
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.db import migrations

STATIC_IMAGES = Path(settings.BASE_DIR) / "static" / "images"

#: Statement line order -> portrait crop. 387px is the widest that exists for
#: the first line; the field is editable now, so it can be replaced in the CMS.
STATEMENT_MOBILE = {
    0: "statement-1-m387.webp",
    1: "statement-2-m768.webp",
    2: "statement-3-m768.webp",
}
WHY_MOBILE = "why-cofur-v2-m768.webp"


def media_from_static(filename, folder):
    """Copy ``static/images/<filename>`` into media storage, returning its name.

    Mirrors the helper in ``seed_cofur`` so both land on the same path and a
    later reseed finds the file already there instead of duplicating it.
    """
    source = STATIC_IMAGES / filename
    target = f"seed/{folder}/{filename}"
    if default_storage.exists(target):
        return target
    if not source.exists():
        return ""
    with source.open("rb") as fh:
        return default_storage.save(target, File(fh, name=filename))


def forwards(apps, schema_editor):
    HomePage = apps.get_model("pages", "HomePage")
    HomeStatementLine = apps.get_model("pages", "HomeStatementLine")

    for line in HomeStatementLine.objects.all():
        if line.mobile_image:
            continue
        filename = STATEMENT_MOBILE.get(line.order)
        if not filename:
            continue
        name = media_from_static(filename, "home/statement")
        if name:
            line.mobile_image = name
            line.save(update_fields=["mobile_image"])

    for page in HomePage.objects.all():
        if page.why_mobile_image or not page.why_image:
            continue
        name = media_from_static(WHY_MOBILE, "home")
        if name:
            page.why_mobile_image = name
            page.save(update_fields=["why_mobile_image"])


def backwards(apps, schema_editor):
    """Detach the seeded crops, leaving any hand-uploaded ones in place.

    The copied files stay in media storage: another record may point at the
    same name, and an orphaned file is cheaper than a broken image.
    """
    HomePage = apps.get_model("pages", "HomePage")
    HomeStatementLine = apps.get_model("pages", "HomeStatementLine")

    for line in HomeStatementLine.objects.all():
        expected = STATEMENT_MOBILE.get(line.order)
        if expected and line.mobile_image.name == f"seed/home/statement/{expected}":
            line.mobile_image = ""
            line.save(update_fields=["mobile_image"])

    for page in HomePage.objects.all():
        if page.why_mobile_image.name == f"seed/home/{WHY_MOBILE}":
            page.why_mobile_image = ""
            page.save(update_fields=["why_mobile_image"])


class Migration(migrations.Migration):

    dependencies = [
        ("pages", "0011_homepage_why_mobile_alt_homepage_why_mobile_image_and_more"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
