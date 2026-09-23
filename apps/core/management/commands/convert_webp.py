"""Convert every image already stored by the CMS to WebP (and resize oversized ones).

    python manage.py convert_webp [--dry-run]

Safe to run repeatedly: files that are already WebP and within the size limit are skipped.
"""
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import models

from apps.core.images import optimise_fields

APPS = ("catalog", "pages", "team", "core")
SKIP_FIELDS = {("core", "sitesettings", "favicon")}


class Command(BaseCommand):
    help = "Convert stored images to WebP and resize any that exceed IMAGE_MAX_EDGE."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Only report what would change.")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        converted = scanned = 0
        for app_label in APPS:
            for model in apps.get_app_config(app_label).get_models():
                fields = [f.name for f in model._meta.get_fields() if isinstance(f, models.ImageField) and (app_label, model._meta.model_name, f.name) not in SKIP_FIELDS]
                if not fields:
                    continue
                for instance in model._default_manager.all():
                    # Rows that shared one file with an already-converted row: point them at the WebP.
                    repaired = {}
                    for f in fields:
                        image = getattr(instance, f)
                        if image and not image.name.lower().endswith((".webp", ".svg", ".gif")) and not image.storage.exists(image.name):
                            sibling = image.name.rsplit(".", 1)[0] + ".webp"
                            if image.storage.exists(sibling):
                                repaired[f] = sibling
                                image.name = sibling
                    if repaired and not dry:
                        model._default_manager.filter(pk=instance.pk).update(**repaired)
                        converted += len(repaired)
                        for f, name in repaired.items():
                            self.stdout.write(f"  {model.__name__}#{instance.pk}.{f} -> {name} (shared file)")
                        if hasattr(instance, "thumbnail"):
                            instance.thumbnail = None
                            instance.save()
                    candidates = [f for f in fields if getattr(instance, f) and not getattr(instance, f).name.lower().endswith((".webp", ".svg", ".gif"))]
                    scanned += len(candidates)
                    if not candidates:
                        continue
                    if dry:
                        for f in candidates:
                            self.stdout.write(f"  would convert {model.__name__}#{instance.pk}.{f}: {getattr(instance, f).name}")
                        continue
                    changed = optimise_fields(instance, *candidates)
                    converted += len(changed)
                    for f, new_name in changed.items():
                        self.stdout.write(f"  {model.__name__}#{instance.pk}.{f} -> {new_name}")
                    if hasattr(instance, "thumbnail") and changed:
                        instance.save()  # regenerates the thumbnail from the new file
        self.stdout.write(self.style.SUCCESS(f"{'Would convert' if dry else 'Converted'} {converted if not dry else scanned} image(s)."))
