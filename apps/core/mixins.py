"""Abstract model mixins shared across the CMS."""
from django.db import models
from django.utils.text import slugify



BANNER_MOBILE_LABEL = "Mobile banner image (optional, shown below 768px)"
BANNER_MOBILE_HELP = "Portrait or square crop, minimum 800px wide. Leave empty to reuse the desktop banner."


def banner_mobile_image_field(upload_to, **kwargs):
    kwargs.setdefault("help_text", BANNER_MOBILE_HELP)
    kwargs.setdefault("verbose_name", BANNER_MOBILE_LABEL)
    kwargs.setdefault("blank", True)
    kwargs.setdefault("null", True)
    return models.ImageField(upload_to=upload_to, **kwargs)


def banner_mobile_alt_field():
    return models.CharField("Mobile banner alt text (optional)", max_length=255, blank=True, help_text="Used with the mobile banner; falls back to the desktop alt text.")



class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OrderableModel(models.Model):
    order = models.PositiveIntegerField(default=0, db_index=True, help_text="Lower numbers appear first.")

    class Meta:
        abstract = True
        ordering = ["order", "id"]


class ActivatableModel(models.Model):
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True


class SEOFieldsMixin(models.Model):
    """Reusable SEO metadata. Rendered by ``partials/seo.html``."""

    ROBOTS_CHOICES = [
        ("index, follow", "Index, follow (default)"),
        ("noindex, follow", "No index, follow"),
        ("index, nofollow", "Index, no follow"),
        ("noindex, nofollow", "No index, no follow"),
    ]

    seo_title = models.CharField("SEO title", max_length=255, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)
    meta_keywords = models.CharField(max_length=255, blank=True)
    og_title = models.CharField("Open Graph title", max_length=255, blank=True)
    og_description = models.CharField("Open Graph description", max_length=320, blank=True)
    og_image = models.ImageField("Open Graph image", upload_to="seo/", blank=True, null=True)
    canonical_url = models.URLField(blank=True)
    robots = models.CharField(max_length=40, choices=ROBOTS_CHOICES, default="index, follow")

    class Meta:
        abstract = True

    def seo_context(self, request=None, fallback_title="", fallback_description="", fallback_image=None):
        """Return a dict used by the SEO partial."""
        image = self.og_image or fallback_image
        image_url = ""
        if image:
            try:
                image_url = image.url
            except ValueError:
                image_url = ""
            if request is not None and image_url:
                image_url = request.build_absolute_uri(image_url)
        canonical = self.canonical_url
        if not canonical and request is not None:
            canonical = request.build_absolute_uri(request.path)
        return {
            "title": self.seo_title or fallback_title,
            "description": self.meta_description or fallback_description,
            "keywords": self.meta_keywords,
            "og_title": self.og_title or self.seo_title or fallback_title,
            "og_description": self.og_description or self.meta_description or fallback_description,
            "og_image": image_url,
            "canonical": canonical,
            "robots": self.robots,
        }


class SingletonModel(models.Model):
    """A model that only ever has one row (pk=1)."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):  # pragma: no cover - guard
        raise ValueError("Singleton records cannot be deleted.")

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


def unique_slugify(instance, value, slug_field="slug", queryset=None):
    """Generate a unique slug for ``instance`` based on ``value``."""
    base = slugify(value)[:180] or "item"
    slug = base
    model = instance.__class__
    qs = queryset if queryset is not None else model._default_manager.all()
    if instance.pk:
        qs = qs.exclude(pk=instance.pk)
    counter = 2
    while qs.filter(**{slug_field: slug}).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug
