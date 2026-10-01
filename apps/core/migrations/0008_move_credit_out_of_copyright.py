"""Move the build credit out of the copyright line and into its own fields.

0006 appended "| Develop by Nivtech." to copyright_text. The credit now needs
to be a link, which a plain text field cannot carry, so it moves to credit_text
and credit_url. Any row still holding the combined string is split; a line an
editor has written themselves is left untouched.
"""
from django.db import migrations

COMBINED = "Copyright © {year} COFUR Pvt. Ltd. All rights reserved | Develop by Nivtech."
PLAIN = "Copyright © {year} COFUR Pvt. Ltd. All rights reserved"
CREDIT = "Develop by Nivtech."
CREDIT_URL = "https://nivtech.co.in/"


def forwards(apps, schema_editor):
    SiteSettings = apps.get_model("core", "SiteSettings")
    for settings in SiteSettings.objects.all():
        text = settings.copyright_text or ""
        if " | " in text:
            copyright_part, _, credit_part = text.partition(" | ")
            settings.copyright_text = copyright_part.strip()
            settings.credit_text = credit_part.strip()
        elif text in {PLAIN, PLAIN + ".", ""}:
            settings.credit_text = CREDIT
        if settings.credit_text == CREDIT and not settings.credit_url:
            settings.credit_url = CREDIT_URL
        settings.save(update_fields=["copyright_text", "credit_text", "credit_url"])


def backwards(apps, schema_editor):
    SiteSettings = apps.get_model("core", "SiteSettings")
    for settings in SiteSettings.objects.exclude(credit_text=""):
        settings.copyright_text = f"{settings.copyright_text} | {settings.credit_text}".strip()
        settings.save(update_fields=["copyright_text"])


class Migration(migrations.Migration):

    dependencies = [("core", "0007_sitesettings_credit_text_sitesettings_credit_url_and_more")]

    operations = [migrations.RunPython(forwards, backwards)]
