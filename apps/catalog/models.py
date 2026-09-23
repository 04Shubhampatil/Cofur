from django.db import models
from django.urls import reverse

from apps.core.images import make_thumbnail, optimise_fields
from apps.core.mixins import banner_mobile_alt_field, banner_mobile_image_field
from apps.core.mixins import (
    ActivatableModel,
    OrderableModel,
    SEOFieldsMixin,
    TimeStampedModel,
    unique_slugify,
)


class PublishedQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Product.STATUS_PUBLISHED)

    def featured(self):
        return self.published().filter(is_featured=True)


class Category(SEOFieldsMixin, OrderableModel, ActivatableModel, TimeStampedModel):
    """Top-level product grouping (e.g. Soft Seating, Acoustic Lights)."""

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True, db_index=True)
    subtitle = models.CharField(max_length=200, blank=True, help_text="Short line under the name on cards, e.g. 'Lounge, modular & breakout'.")
    description = models.TextField(blank=True)
    banner_image = models.ImageField(upload_to="categories/", blank=True, null=True)
    banner_mobile_image = banner_mobile_image_field(upload_to="categories/")
    banner_mobile_alt = banner_mobile_alt_field()
    thumbnail_image = models.ImageField(upload_to="categories/", blank=True, null=True, help_text="Card image used on the home page rail.")
    lifestyle_image = models.ImageField(upload_to="categories/", blank=True, null=True, help_text="Optional lifestyle photo shown in the sub-category grid on this category page.")
    link_override = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional. Send visitors somewhere else than the category page, e.g. /contact/?collection=acoustic-lights",
    )
    card_link_text = models.CharField(max_length=40, blank=True, default="View items")
    show_on_home = models.BooleanField(default=True, db_index=True)

    class Meta(OrderableModel.Meta):
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        indexes = [models.Index(fields=["is_active", "order"])]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        super().save(*args, **kwargs)
        optimise_fields(self, "banner_image", "banner_mobile_image", "thumbnail_image", "lifestyle_image")

    def get_absolute_url(self):
        return reverse("website:category_detail", kwargs={"slug": self.slug})

    @property
    def link(self):
        return self.link_override or self.get_absolute_url()

    @property
    def card_image(self):
        return self.thumbnail_image or self.banner_image

    @property
    def banner_desktop(self):
        """Desktop banner, falling back to the mobile crop when only that was uploaded."""
        return self.banner_image or self.banner_mobile_image

    def active_collections(self):
        return self.collections.filter(is_active=True)


class Collection(SEOFieldsMixin, OrderableModel, ActivatableModel, TimeStampedModel):
    """A product family within a category (Cove, Pebble, Orbit, Grove)."""

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, unique=True, db_index=True)
    category = models.ForeignKey(Category, null=True, blank=True, related_name="collections", on_delete=models.SET_NULL, db_index=True)
    tagline = models.CharField(max_length=200, blank=True, help_text="Short line on cards, e.g. 'Privacy and focus within open spaces'.")
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="collections/", blank=True, null=True, help_text="Card image used on the category page and home page.")
    banner_image = models.ImageField("Banner image (desktop)", upload_to="collections/", blank=True, null=True, help_text="Full-width banner at the top of the collection page. Recommended 1536×1024 or wider.")
    banner_mobile_image = banner_mobile_image_field(upload_to="collections/")
    banner_mobile_alt = banner_mobile_alt_field()
    banner_alt = models.CharField("Banner alt text", max_length=255, blank=True, help_text="Describes the banner photo for screen readers and search engines.")
    heading = models.CharField("Banner title", max_length=200, blank=True, help_text="Shown over the banner. Defaults to '<name> collection'. Press Enter to split it over two lines, e.g. 'Cove' / 'collection'.")
    link_override = models.CharField(max_length=255, blank=True, help_text="Optional. e.g. /contact/?collection=pebble to send visitors to the enquiry form instead of the collection page.")
    card_style = models.CharField(max_length=40, blank=True, help_text="Optional CSS modifier for the card (cove, pebble, orbit, grove).")

    class Meta(OrderableModel.Meta):
        verbose_name = "Sub-category"
        verbose_name_plural = "Sub-categories"
        indexes = [models.Index(fields=["is_active", "order"])]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        # Browsers submit textareas with CRLF; store plain newlines so the banner title renders as two lines.
        self.heading = (self.heading or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        super().save(*args, **kwargs)
        optimise_fields(self, "image", "banner_image", "banner_mobile_image")

    def get_absolute_url(self):
        return reverse("website:collection_detail", kwargs={"slug": self.slug})

    @property
    def banner_desktop(self):
        return self.banner_image or self.banner_mobile_image

    @property
    def link(self):
        return self.link_override or self.get_absolute_url()

    @property
    def display_heading(self):
        return self.heading or f"{self.name}\ncollection"

    def published_products(self):
        return self.products.published()

    @property
    def product_count(self):
        return self.products.count()


class Product(SEOFieldsMixin, OrderableModel, TimeStampedModel):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_CHOICES = [(STATUS_DRAFT, "Draft"), (STATUS_PUBLISHED, "Published")]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, db_index=True)
    sku = models.CharField("Product code / SKU", max_length=60, blank=True, db_index=True)
    collection = models.ForeignKey(Collection, null=True, blank=True, related_name="products", on_delete=models.SET_NULL, db_index=True)
    category = models.ForeignKey(Category, null=True, blank=True, related_name="products", on_delete=models.SET_NULL, db_index=True)
    name_prefix = models.CharField(max_length=60, blank=True, help_text="Italic collection prefix on cards, e.g. 'Cove' for 'Cove Solo Lounge'.")
    tagline = models.CharField(max_length=200, blank=True, help_text="One-line eyebrow, e.g. 'Comfort better shared'.")
    short_description = models.TextField(blank=True)
    description = models.TextField(blank=True, help_text="Full description. Blank lines start a new paragraph.")

    main_image = models.ImageField(upload_to="products/", blank=True, null=True)
    main_image_alt = models.CharField(max_length=255, blank=True)
    card_image = models.ImageField(upload_to="products/", blank=True, null=True, help_text="Optional card image. Falls back to the main image.")
    hover_image = models.ImageField(upload_to="products/", blank=True, null=True, help_text="Lifestyle image revealed on hover on cards.")
    thumbnail = models.ImageField(upload_to="products/thumbs/", blank=True, null=True, editable=False)
    finish_image = models.ImageField(upload_to="products/", blank=True, null=True, help_text="Large image shown beside the specifications accordion.")

    seating_capacity = models.CharField(max_length=60, blank=True)
    areas = models.TextField(blank=True, help_text="One per line, e.g. Workplace / Coworking / Hospitality.")
    materials = models.TextField(blank=True, help_text="One per line.")
    fabric_intro = models.CharField(max_length=255, blank=True, default="Choose from a curated range of high-quality fabrics and colours to match your space.")

    dimension_width = models.CharField(max_length=30, blank=True)
    dimension_depth = models.CharField(max_length=30, blank=True)
    dimension_height = models.CharField(max_length=30, blank=True)
    dimension_seat_height = models.CharField(max_length=30, blank=True)
    dimension_weight = models.CharField(max_length=30, blank=True)
    dimension_unit = models.CharField(max_length=10, blank=True, default="cm")
    weight_unit = models.CharField(max_length=10, blank=True, default="kg")

    # Section headings (editable per product)
    details_heading = models.CharField(max_length=120, blank=True, default="Product details")
    specs_heading = models.CharField(max_length=120, blank=True, default="Specifications")
    gallery_heading = models.CharField(max_length=120, blank=True, default="Gallery")
    related_heading = models.CharField(max_length=120, blank=True, default="Related products")
    fabric_heading = models.CharField(max_length=120, blank=True, default="Fabric options")
    features_heading = models.CharField(max_length=120, blank=True, default="Features")
    dimensions_heading = models.CharField(max_length=120, blank=True, default="Dimensions")
    care_heading = models.CharField(max_length=120, blank=True, default="Material care")

    # Enquiry CTA
    cta_text = models.CharField("CTA text", max_length=60, blank=True, default="Enquire now")
    cta_url = models.CharField("CTA URL", max_length=255, blank=True, help_text="Leave blank to open the enquiry popup.")
    enquiry_title = models.CharField(max_length=120, blank=True, default="Enquire now")
    enquiry_text = models.CharField(max_length=255, blank=True, default="Tell us about your space and our team will come back with the right solution.")

    related_products = models.ManyToManyField("self", symmetrical=False, blank=True, related_name="related_to")

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)

    objects = PublishedQuerySet.as_manager()

    class Meta(OrderableModel.Meta):
        indexes = [
            models.Index(fields=["status", "is_featured"]),
            models.Index(fields=["collection", "status"]),
            models.Index(fields=["category", "status"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name)
        if self.collection_id and not self.category_id and self.collection.category_id:
            self.category_id = self.collection.category_id
        regenerate_thumb = False
        old = Product.objects.filter(pk=self.pk).values("main_image").first() if self.pk else None
        if old:
            regenerate_thumb = old["main_image"] != (self.main_image.name if self.main_image else None)
        else:
            regenerate_thumb = bool(self.main_image)
        super().save(*args, **kwargs)
        optimise_fields(self, "main_image", "card_image", "hover_image", "finish_image")
        if self.main_image and (regenerate_thumb or not self.thumbnail):
            thumb_name = make_thumbnail(self.main_image)
            if thumb_name:
                Product.objects.filter(pk=self.pk).update(thumbnail=thumb_name)
                self.thumbnail.name = thumb_name

    def get_absolute_url(self):
        return reverse("website:product_detail", kwargs={"slug": self.slug})

    @property
    def is_published(self):
        return self.status == self.STATUS_PUBLISHED

    @property
    def display_name_suffix(self):
        """Name without the italic prefix, for card titles like <em>Cove</em> Solo Lounge."""
        if self.name_prefix and self.name.lower().startswith(self.name_prefix.lower()):
            return self.name[len(self.name_prefix):].strip()
        return self.name

    @property
    def card_picture(self):
        return self.card_image or self.main_image

    def card_title_parts(self):
        """(prefix, rest) for card titles such as <em>Cove</em> Solo Lounge.

        Uses ``name_prefix`` when set, otherwise the collection name when the product
        name starts with it. Returns ("", name) when there is nothing to emphasise.
        """
        prefix = (self.name_prefix or "").strip()
        if not prefix and self.collection_id:
            prefix = (self.collection.name or "").strip()
        if prefix and self.name.lower().startswith(prefix.lower()):
            rest = self.name[len(prefix):].strip()
            if rest:
                return self.name[: len(prefix)], rest
        return "", self.name

    @property
    def card_title_prefix(self):
        return self.card_title_parts()[0]

    @property
    def card_title_rest(self):
        return self.card_title_parts()[1]

    def gallery_images(self):
        return self.images.filter(kind=ProductImage.KIND_GALLERY)

    def detail_images(self):
        return self.images.filter(kind=ProductImage.KIND_DETAIL)

    def dimension_images(self):
        return self.images.filter(kind=ProductImage.KIND_DIMENSION)

    def features(self):
        return self.feature_items.filter(kind=ProductFeature.KIND_FEATURE)

    def care_items(self):
        return self.feature_items.filter(kind=ProductFeature.KIND_CARE)

    def get_related_products(self, limit=4):
        related = list(self.related_products.published().select_related("collection")[:limit])
        if related:
            return related
        if self.collection_id:
            return list(self.collection.products.published().exclude(pk=self.pk)[:limit])
        return list(Product.objects.published().exclude(pk=self.pk)[:limit])

    @property
    def has_dimensions(self):
        return any([
            self.dimension_width, self.dimension_depth, self.dimension_height,
            self.dimension_seat_height, self.dimension_weight,
        ])

    def dimension_rows(self):
        rows = [
            ("Width", self.dimension_width, self.dimension_unit),
            ("Depth", self.dimension_depth, self.dimension_unit),
            ("Height", self.dimension_height, self.dimension_unit),
            ("Seat height", self.dimension_seat_height, self.dimension_unit),
            ("Weight", self.dimension_weight, self.weight_unit),
        ]
        return [row for row in rows if row[1]]

    def duplicate(self):
        """Create an unpublished copy of this product including child rows."""
        specs = list(self.specifications.all())
        features = list(self.feature_items.all())
        colors = list(self.colors.all())
        images = list(self.images.all())
        related = list(self.related_products.all())
        clone = Product.objects.get(pk=self.pk)
        clone.pk = None
        clone.id = None
        clone.slug = ""
        clone.name = f"{self.name} (copy)"
        clone.status = Product.STATUS_DRAFT
        clone.is_featured = False
        clone.thumbnail = None
        clone.save()
        for spec in specs:
            spec.pk = None
            spec.product = clone
            spec.save()
        for feature in features:
            feature.pk = None
            feature.product = clone
            feature.save()
        for color in colors:
            color.pk = None
            color.product = clone
            color.save()
        for image in images:
            image.pk = None
            image.product = clone
            image.save()
        clone.related_products.set(related)
        return clone


class ProductImage(OrderableModel):
    KIND_GALLERY = "gallery"
    KIND_DETAIL = "detail"
    KIND_DIMENSION = "dimension"
    KIND_CHOICES = [
        (KIND_GALLERY, "Gallery"),
        (KIND_DETAIL, "Product details mosaic"),
        (KIND_DIMENSION, "Dimension drawing"),
    ]
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="products/gallery/", blank=True, null=True, help_text="For a video tile this is used as the poster frame.")
    video_file = models.FileField("Video (optional, MP4/WebM)", upload_to="products/videos/", blank=True, null=True, help_text="Product details mosaic only. MP4 or WebM up to 100 MB. Shown instead of the image.")
    video_url = models.URLField("Video link (optional)", blank=True, help_text="YouTube or Vimeo page URL, used when no video file is uploaded.")
    thumbnail = models.ImageField(upload_to="products/gallery/thumbs/", blank=True, null=True, editable=False)
    alt_text = models.CharField(max_length=255, blank=True)
    caption = models.CharField(max_length=200, blank=True)
    kind = models.CharField(max_length=12, choices=KIND_CHOICES, default=KIND_GALLERY, db_index=True)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)

    class Meta(OrderableModel.Meta):
        verbose_name = "Product image"

    def __str__(self):
        return self.caption or self.alt_text or (self.image.name if self.image else "") or (self.video_file.name if self.video_file else "") or self.video_url or "Product media"

    @property
    def is_video(self):
        return bool(self.video_file or self.video_url)

    @property
    def embed_url(self):
        """Embeddable player URL for a YouTube/Vimeo page link (empty otherwise)."""
        url = (self.video_url or "").strip()
        if not url:
            return ""
        from urllib.parse import parse_qs, urlparse

        parts = urlparse(url)
        host = parts.netloc.lower().removeprefix("www.").removeprefix("m.")
        path = parts.path.strip("/")
        if host in ("youtube.com", "youtube-nocookie.com"):
            video_id = parse_qs(parts.query).get("v", [""])[0]
            if not video_id and path.startswith(("embed/", "shorts/", "live/")):
                video_id = path.split("/")[1] if "/" in path else ""
            return f"https://www.youtube-nocookie.com/embed/{video_id}" if video_id else ""
        if host == "youtu.be":
            return f"https://www.youtube-nocookie.com/embed/{path.split('/')[0]}" if path else ""
        if host in ("vimeo.com", "player.vimeo.com"):
            segment = path.split("/")[-1] if path else ""
            return f"https://player.vimeo.com/video/{segment}" if segment.isdigit() else ""
        return ""

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if self.image and (is_new or not self.thumbnail):
            from apps.core.images import image_dimensions

            optimise_fields(self, "image")
            self.width, self.height = image_dimensions(self.image)
            thumb = make_thumbnail(self.image, size=(400, 400))
            ProductImage.objects.filter(pk=self.pk).update(width=self.width, height=self.height, thumbnail=thumb or None)
            if thumb:
                self.thumbnail.name = thumb


class ProductSpecification(OrderableModel):
    product = models.ForeignKey(Product, related_name="specifications", on_delete=models.CASCADE)
    label = models.CharField(max_length=120)
    value = models.CharField(max_length=255)

    class Meta(OrderableModel.Meta):
        verbose_name = "Product specification"

    def __str__(self):
        return f"{self.label}: {self.value}"


class ProductFeature(OrderableModel):
    KIND_FEATURE = "feature"
    KIND_CARE = "care"
    KIND_CHOICES = [(KIND_FEATURE, "Feature / use case"), (KIND_CARE, "Material care")]
    product = models.ForeignKey(Product, related_name="feature_items", on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=KIND_FEATURE, db_index=True)

    class Meta(OrderableModel.Meta):
        verbose_name = "Product feature"

    def __str__(self):
        return self.text


class ProductColor(OrderableModel):
    product = models.ForeignKey(Product, related_name="colors", on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    swatch_image = models.ImageField(upload_to="products/swatches/", blank=True, null=True)
    hex_code = models.CharField(max_length=7, blank=True, help_text="Used when no swatch image is uploaded, e.g. #d4b791")
    finish_image = models.ImageField(upload_to="products/finishes/", blank=True, null=True, help_text="Shown beside the specs when this colour is selected.")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        optimise_fields(self, "swatch_image", "finish_image")

    class Meta(OrderableModel.Meta):
        verbose_name = "Product colour"

    def __str__(self):
        return self.name
