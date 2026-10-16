from django.db import migrations

# The enquiry form's editable wording, per landing page.
FORM_TEXT = {
    "wall": [
        ("form_heading", "Enquiry form: heading", "Tell us about your project"),
        ("form_submit", "Enquiry form: button", "Submit project enquiry"),
        ("form_placeholder", "Enquiry form: project details placeholder", "Quantity, preferred finish, project stage, timeline or other requirements."),
        ("form_success", "Enquiry form: thank-you message", "Thank you. Our team will be in touch about your project shortly."),
    ],
    "ceilings": [
        ("form_heading", "Enquiry form: heading", "Request project quote"),
        ("form_submit", "Enquiry form: button", "Request project quote"),
        ("form_placeholder", "Enquiry form: project details placeholder", "Project type, approximate ceiling area, project stage, timeline or other requirements."),
        ("form_success", "Enquiry form: thank-you message", "Thank you. Our team will be in touch about your project shortly."),
    ],
}


def seed(apps, schema_editor):
    LandingText = apps.get_model("pages", "LandingText")
    for page, rows in FORM_TEXT.items():
        for offset, (key, label, text) in enumerate(rows, start=1):
            LandingText.objects.update_or_create(
                page=page, key=key,
                defaults={"label": label, "value": text, "order": 900 + offset},
            )


def unseed(apps, schema_editor):
    LandingText = apps.get_model("pages", "LandingText")
    for page, rows in FORM_TEXT.items():
        LandingText.objects.filter(page=page, key__in=[key for key, _, _ in rows]).delete()


class Migration(migrations.Migration):

    dependencies = [("pages", "0015_seed_ceiling_landing_text")]

    operations = [migrations.RunPython(seed, unseed)]
