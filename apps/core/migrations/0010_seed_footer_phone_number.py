"""Give the footer a phone number to show beside the email.

The site already stores a WhatsApp number, which is the same line in practice,
so it seeds the new field rather than leaving editors to retype it. Only an
empty field is filled, and the stored WhatsApp value is left alone.
"""
import re

from django.db import migrations


def pretty(raw):
    """'919320461618' / '8007410793' -> '+91 93204 61618'."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 10:
        digits = "91" + digits
    if len(digits) == 12 and digits.startswith("91"):
        return f"+91 {digits[2:7]} {digits[7:]}"
    return f"+{digits}" if digits else ""


def forwards(apps, schema_editor):
    SiteSettings = apps.get_model("core", "SiteSettings")
    for settings in SiteSettings.objects.filter(phone_number=""):
        number = pretty(settings.whatsapp_number)
        if number:
            settings.phone_number = number
            settings.save(update_fields=["phone_number"])


def backwards(apps, schema_editor):
    SiteSettings = apps.get_model("core", "SiteSettings")
    SiteSettings.objects.update(phone_number="")


class Migration(migrations.Migration):

    dependencies = [("core", "0009_sitesettings_phone_number")]

    operations = [migrations.RunPython(forwards, backwards)]
