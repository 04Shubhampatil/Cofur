"""Completed installations, shown as a grid of cards and an individual page.

The page is four blocks, in this order: the heading, a carousel beside a panel
of facts, a written section, then a row of supporting photographs. Everything
in those blocks is editable, including the two sub-headings, because the words
that suit an office fit-out do not suit a showroom.
"""
from django.db import models
from django.urls import reverse

from apps.core.images import optimise_fields
from apps.core.mixins import OrderableModel, SEOFieldsMixin, TimeStampedModel, unique_slugify


class ProjectQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Project.STATUS_PUBLISHED)


class Project(SEOFieldsMixin, OrderableModel, TimeStampedModel):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_CHOICES = [(STATUS_DRAFT, "Draft"), (STATUS_PUBLISHED, "Published")]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, db_index=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)

    studio = models.CharField(
        max_length=200,
        blank=True,
        help_text="The line under the title on the card, e.g. the architect or client.",
    )
    cover_image = models.ImageField(upload_to="projects/", blank=True, null=True, help_text="Shown on the card in the projects grid.")
    cover_alt = models.CharField(max_length=255, blank=True, help_text="Describes the cover image. Falls back to the title.")

    body_heading = models.CharField(max_length=200, blank=True, help_text="Sub-heading above the written section.")
    body = models.TextField(blank=True, help_text="Use the toolbar for headings, lists, links and emphasis.")

    gallery_heading = models.CharField(max_length=200, blank=True, help_text="Sub-heading above the row of photographs.")

    objects = ProjectQuerySet.as_manager()

    class Meta(OrderableModel.Meta):
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        indexes = [models.Index(fields=["status", "order"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.title)
        super().save(*args, **kwargs)
        optimise_fields(self, "cover_image")

    def get_absolute_url(self):
        return reverse("website:project_detail", kwargs={"slug": self.slug})

    def carousel_images(self):
        return self.images.filter(kind=ProjectImage.KIND_CAROUSEL)

    def gallery_images(self):
        return self.images.filter(kind=ProjectImage.KIND_GALLERY)

    @property
    def lead_image(self):
        """The first carousel shot, falling back to the cover.

        A project can be written before its carousel is filled, and the page
        should still open on a picture rather than a gap.
        """
        first = self.carousel_images().first()
        return first.image if first else self.cover_image


class ProjectFact(OrderableModel):
    """One line in the facts panel: "Client", "Area", "Completed" and so on.

    A list rather than fixed columns, because what is worth stating differs
    per project and an empty "Number of students" row reads worse than none.
    """

    project = models.ForeignKey(Project, related_name="facts", on_delete=models.CASCADE)
    label = models.CharField(max_length=80)
    value = models.CharField(max_length=255)

    class Meta(OrderableModel.Meta):
        verbose_name = "Project fact"

    def __str__(self):
        return f"{self.label}: {self.value}"


class ProjectImage(OrderableModel):
    """A photograph, either in the carousel at the top or the row below."""

    KIND_CAROUSEL = "carousel"
    KIND_GALLERY = "gallery"
    KIND_CHOICES = [(KIND_CAROUSEL, "Carousel (top)"), (KIND_GALLERY, "Gallery row (bottom)")]

    project = models.ForeignKey(Project, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="projects/")
    alt = models.CharField(max_length=255, blank=True, help_text="Describes the photograph. Falls back to the project title.")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_CAROUSEL, db_index=True)

    # Gallery-row cards carry their own words and destination. The carousel
    # ignores these: it is one photograph at a time with nothing written on it.
    title = models.CharField(max_length=120, blank=True, help_text="Name shown under the card image.")
    caption = models.CharField(max_length=160, blank=True, help_text="Small line under the heading on the gallery card.")
    link_url = models.CharField(max_length=500, blank=True, help_text="Where the card goes when clicked, e.g. /collections/cove/ or a full URL. Leave empty for a card that is not a link.")

    class Meta(OrderableModel.Meta):
        verbose_name = "Project image"

    def __str__(self):
        return f"{self.project.title} — {self.get_kind_display()}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        optimise_fields(self, "image")

    @property
    def alt_text(self):
        return self.alt or self.project.title

