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
        # select_related: every card asks its product for a URL when rendering.
        return self.images.filter(kind=ProjectImage.KIND_GALLERY).select_related("product")

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
    # Optional, because a card built from a product takes the product's picture.
    # The carousel still demands one; its form asks for it.
    image = models.ImageField(upload_to="projects/", blank=True, null=True)
    alt = models.CharField(max_length=255, blank=True, help_text="Describes the photograph. Falls back to the project title.")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_CAROUSEL, db_index=True)

    # A card in the bottom row is a product: choosing one in the CMS is the
    # whole edit, and the picture, name, line and link all come from it. The
    # carousel ignores all of this — it is one photograph at a time.
    product = models.ForeignKey(
        "catalog.Product",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="project_cards",
        help_text="Search for the product this card shows. Its picture, name and line are used.",
    )

    # Written before the product picker existed. Still rendered for cards that
    # have no product, so older rows keep working; a chosen product wins.
    title = models.CharField(max_length=120, blank=True, help_text="Name shown under the card image.")
    caption = models.CharField(max_length=160, blank=True, help_text="Small line under the heading on the gallery card.")
    link_url = models.CharField(max_length=500, blank=True, help_text="Where the card goes when it has no product.")

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

    # ------------------------------------------------------------------ cards
    # A card reads from its product when it has one. The stored columns are the
    # fallback for rows written before products could be chosen, so an older
    # project keeps its row of cards until someone picks products for it.

    @property
    def card_url(self):
        """Where the card goes, or "" for a card that is not a link."""
        if self.product_id:
            return self.product.get_absolute_url()
        return self.link_url

    @property
    def card_picture(self):
        if self.product_id:
            return self.product.card_picture
        return self.image

    @property
    def card_title(self):
        if self.product_id:
            return self.product.name
        return self.title

    @property
    def card_caption(self):
        if self.product_id:
            return self.product.tagline
        return self.caption

    @property
    def card_alt(self):
        if self.product_id:
            return self.product.main_image_alt or self.product.name
        return self.alt_text

