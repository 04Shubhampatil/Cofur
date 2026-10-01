from django.db import models
from django.urls import reverse

from apps.core.images import optimise_fields
from apps.core.mixins import SEOFieldsMixin, TimeStampedModel, unique_slugify


class StoryQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Story.STATUS_PUBLISHED)


class Story(SEOFieldsMixin, TimeStampedModel):
    """A post in the Our Story section: an announcement, a blog entry or news."""

    KIND_ANNOUNCEMENT = "announcement"
    KIND_BLOG = "blog"
    KIND_NEWS = "news"
    KIND_OTHER = "other"
    KIND_CHOICES = [
        (KIND_ANNOUNCEMENT, "Announcement"),
        (KIND_BLOG, "Blog"),
        (KIND_NEWS, "News"),
        (KIND_OTHER, "Other"),
    ]

    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_CHOICES = [(STATUS_DRAFT, "Draft"), (STATUS_PUBLISHED, "Published")]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, db_index=True, blank=True)
    kind = models.CharField("Category", max_length=20, choices=KIND_CHOICES, default=KIND_BLOG, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    published_at = models.DateField(db_index=True, help_text="Used for ordering and shown on the card.")

    cover_image = models.ImageField(upload_to="stories/", blank=True, null=True, help_text="Shown on the card and at the top of the post.")
    cover_alt = models.CharField(max_length=255, blank=True, help_text="Describes the cover image. Falls back to the title.")
    excerpt = models.TextField(blank=True, help_text="One or two lines shown on the card. Falls back to the opening of the body.")
    body = models.TextField(blank=True, help_text="One paragraph per blank line.")

    objects = StoryQuerySet.as_manager()

    class Meta:
        ordering = ["-published_at", "-id"]
        verbose_name = "Story"
        verbose_name_plural = "Stories"
        indexes = [models.Index(fields=["status", "-published_at"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.title)
        super().save(*args, **kwargs)
        optimise_fields(self, "cover_image")

    def get_absolute_url(self):
        return reverse("website:story_detail", kwargs={"slug": self.slug})

    #: Roughly six lines in a card before it is cut.
    SUMMARY_WORDS = 46

    @property
    def summary(self):
        """Card text: the excerpt and the body together, cut on a word boundary."""
        text = " ".join(f"{self.excerpt} {self.body}".split())
        words = text.split(" ")
        if len(words) <= self.SUMMARY_WORDS:
            return text
        return " ".join(words[: self.SUMMARY_WORDS]) + " […]"
