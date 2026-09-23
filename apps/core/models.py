from django.db import models
from django.urls import NoReverseMatch, reverse

from .mixins import ActivatableModel, OrderableModel, SingletonModel


class SiteSettings(SingletonModel):
    """Site-wide configuration. Exactly one row exists (pk=1)."""

    site_name = models.CharField(max_length=120, default="COFUR")
    tagline = models.CharField(max_length=255, blank=True, default="Change the way you work")
    logo = models.ImageField(upload_to="site/", blank=True, null=True, help_text="Dark logo used in the header.")
    logo_light = models.ImageField(upload_to="site/", blank=True, null=True, help_text="Light logo used in the footer.")
    favicon = models.ImageField(upload_to="site/", blank=True, null=True)

    contact_email = models.EmailField(blank=True)
    whatsapp_number = models.CharField(max_length=30, blank=True, help_text="International format without +, e.g. 919320461618")
    whatsapp_message = models.CharField(max_length=255, blank=True, default="Hello Cofur, I would like to know more about your furniture.")
    address = models.TextField(blank=True)
    google_maps_url = models.URLField(blank=True)

    footer_eyebrow = models.CharField(max_length=120, blank=True, default="Let's build better workspaces")
    footer_title = models.CharField(max_length=255, blank=True, default="We’ll help you find the\nright solution.")
    footer_primary_cta_text = models.CharField(max_length=60, blank=True, default="Contact us")
    footer_primary_cta_url = models.CharField(max_length=255, blank=True, default="/contact/")
    footer_secondary_cta_text = models.CharField(max_length=60, blank=True, default="Download catalog")
    footer_secondary_cta_url = models.CharField(max_length=255, blank=True, default="/categories/soft-seating/")
    copyright_text = models.CharField(max_length=255, blank=True, default="Copyright © {year} COFUR Pvt. Ltd. All rights reserved.")

    linkedin_url = models.URLField("LinkedIn URL", blank=True)
    instagram_url = models.URLField("Instagram URL", blank=True)
    twitter_url = models.URLField("X URL", blank=True)

    # Site-level SEO defaults
    default_meta_title = models.CharField(max_length=255, blank=True)
    default_meta_description = models.CharField(max_length=320, blank=True)
    default_meta_keywords = models.CharField(max_length=255, blank=True)
    default_og_image = models.ImageField(upload_to="seo/", blank=True, null=True)
    default_robots = models.CharField(max_length=40, default="index, follow")

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return self.site_name

    def copyright_rendered(self):
        from django.utils import timezone

        return (self.copyright_text or "").replace("{year}", str(timezone.now().year))


class NavigationMenu(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, help_text="header, footer, ...")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def top_level_items(self):
        return self.items.filter(parent__isnull=True, is_active=True).select_related("collection", "category", "product")


class NavigationItem(OrderableModel, ActivatableModel):
    LINK_TYPES = [
        ("internal", "Internal page"),
        ("collection", "Collection"),
        ("category", "Category"),
        ("product", "Product"),
        ("external", "External / custom URL"),
        ("none", "No link (heading / dropdown)"),
    ]
    INTERNAL_PAGES = [
        ("website:home", "Home"),
        ("website:about", "About"),
        ("website:contact", "Contact"),
        ("website:collection_list", "Collections"),
        ("website:enquire", "Enquire"),
    ]
    menu = models.ForeignKey(NavigationMenu, related_name="items", on_delete=models.CASCADE)
    parent = models.ForeignKey("self", null=True, blank=True, related_name="children", on_delete=models.CASCADE)
    label = models.CharField(max_length=120)
    link_type = models.CharField(max_length=20, choices=LINK_TYPES, default="internal")
    internal_page = models.CharField(max_length=60, choices=INTERNAL_PAGES, blank=True)
    collection = models.ForeignKey("catalog.Collection", null=True, blank=True, on_delete=models.SET_NULL)
    category = models.ForeignKey("catalog.Category", null=True, blank=True, on_delete=models.SET_NULL)
    product = models.ForeignKey("catalog.Product", null=True, blank=True, on_delete=models.SET_NULL)
    external_url = models.CharField(max_length=500, blank=True, help_text="Full URL or a path such as /about/#team")
    url_suffix = models.CharField(max_length=120, blank=True, help_text="Optional anchor/query appended to internal links, e.g. #sustainability or ?collection=pebble")
    open_in_new_tab = models.BooleanField(default=False)
    css_class = models.CharField(max_length=60, blank=True)

    class Meta(OrderableModel.Meta):
        verbose_name = "Navigation item"

    def __str__(self):
        return self.label

    def get_url(self):
        url = "#"
        if self.link_type == "internal" and self.internal_page:
            try:
                url = reverse(self.internal_page)
            except NoReverseMatch:
                url = "#"
        elif self.link_type == "collection" and self.collection_id:
            url = self.collection.get_absolute_url()
        elif self.link_type == "category" and self.category_id:
            url = self.category.get_absolute_url()
        elif self.link_type == "product" and self.product_id:
            url = self.product.get_absolute_url()
        elif self.link_type == "external":
            url = self.external_url or "#"
        elif self.link_type == "none":
            return "#"
        if self.url_suffix and url != "#":
            url = f"{url}{self.url_suffix}"
        return url

    def active_children(self):
        return self.children.filter(is_active=True).select_related("collection", "category", "product")
