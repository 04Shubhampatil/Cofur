from django.db import models

from apps.core.images import optimise_fields
from apps.core.mixins import ActivatableModel, OrderableModel, SEOFieldsMixin, SingletonModel, banner_mobile_alt_field, banner_mobile_image_field


class HomePage(SEOFieldsMixin, SingletonModel):
    """Editable content for the home page (single row)."""

    # Hero
    hero_heading = models.CharField(max_length=200, default="Furniture for the way people actually work")
    hero_visible = models.BooleanField(default=True)

    # Intro / category rail
    intro_heading = models.CharField(max_length=200, default="We help create spaces that people")
    intro_heading_highlight = models.CharField(max_length=120, blank=True, default="want to work in.", help_text="Bold part of the intro heading.")
    intro_visible = models.BooleanField(default=True)

    # Category rail (categories themselves are managed under Catalog > Categories)
    category_section_visible = models.BooleanField(default=True)

    # Brand statement
    statement_heading = models.CharField(max_length=255, blank=True, default="We design spaces that work better. We build solutions that last. We create comfort that matters.", help_text="Accessible summary of the statement lines.")
    statement_description = models.CharField(max_length=255, blank=True, default="You bring the vision. We bring expertise and design to make it work.")
    statement_cta_text = models.CharField(max_length=60, blank=True, default="About us")
    statement_cta_url = models.CharField(max_length=255, blank=True, default="/about/")
    statement_visible = models.BooleanField(default=True)

    # Featured products
    featured_heading = models.CharField(max_length=200, blank=True, default="Featured products")
    featured_cta_text = models.CharField(max_length=60, blank=True, default="View products")
    featured_visible = models.BooleanField(default=True)

    # Differentiators
    why_heading = models.CharField(max_length=200, blank=True, default="What makes COFUR different")
    why_image = models.ImageField(upload_to="home/", blank=True, null=True)
    why_image_alt = models.CharField(max_length=255, blank=True)
    why_visible = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Home page"

    def __str__(self):
        return "Home page"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        optimise_fields(self, "why_image")

    def featured_products(self):
        """Published products flagged 'Featured' in the product editor, in catalogue order."""
        from apps.catalog.models import Product

        return list(Product.objects.featured().select_related("collection"))


class HomeHeroSlide(OrderableModel, ActivatableModel):
    page = models.ForeignKey(HomePage, related_name="hero_slides", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="home/hero/")
    mobile_image = banner_mobile_image_field(upload_to="home/hero/")
    mobile_alt = banner_mobile_alt_field()
    alt_text = models.CharField(max_length=255, blank=True)

    class Meta(OrderableModel.Meta):
        verbose_name = "Hero slide"

    def __str__(self):
        return self.alt_text or f"Slide {self.order}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        optimise_fields(self, "image", "mobile_image")


class HomeStatementLine(OrderableModel, ActivatableModel):
    page = models.ForeignKey(HomePage, related_name="statement_lines", on_delete=models.CASCADE)
    verb = models.CharField(max_length=40, help_text="Opening words, e.g. 'We design'")
    text = models.CharField(max_length=160, help_text="Rest of the sentence, e.g. 'spaces that work better.'")
    image = models.ImageField(upload_to="home/statement/", blank=True, null=True)
    alt_text = models.CharField(max_length=255, blank=True)

    class Meta(OrderableModel.Meta):
        verbose_name = "Statement line"

    def __str__(self):
        return f"{self.verb} {self.text}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        optimise_fields(self, "image")


class Differentiator(OrderableModel, ActivatableModel):
    page = models.ForeignKey(HomePage, related_name="differentiators", on_delete=models.CASCADE)
    heading = models.CharField(max_length=120)

    class Meta(OrderableModel.Meta):
        verbose_name = "Differentiator"

    def __str__(self):
        return self.heading


class AboutPage(SEOFieldsMixin, SingletonModel):
    hero_heading = models.CharField(max_length=200, default="DESIGNED FOR SPACE. BUILT FOR COMFORT")
    hero_image = models.ImageField(upload_to="about/", blank=True, null=True)
    hero_mobile_image = banner_mobile_image_field(upload_to="about/")
    hero_mobile_alt = banner_mobile_alt_field()
    hero_image_alt = models.CharField(max_length=255, blank=True)

    intro_heading = models.CharField(max_length=200, blank=True)
    intro_text = models.TextField(blank=True)

    what_we_make_heading = models.CharField(max_length=120, default="What We Make")
    what_we_make_content = models.TextField(blank=True)

    how_we_work_heading = models.CharField(max_length=120, default="How We Work")
    how_we_work_content = models.TextField(blank=True)

    philosophy_heading = models.CharField(max_length=120, default="Our Philosophy")
    philosophy_content = models.TextField(blank=True)

    mission_heading = models.CharField(max_length=120, default="Our Mission")
    mission_content = models.TextField(blank=True)

    team_heading = models.CharField(max_length=120, default="Our Team")
    team_visible = models.BooleanField(default=True)

    find_us_heading = models.CharField(max_length=120, default="Where to find us")
    find_us_company = models.CharField(max_length=120, blank=True)
    find_us_address = models.TextField(blank=True)
    find_us_map_url = models.URLField(max_length=600, blank=True, help_text="Google Maps embed URL.")
    find_us_visible = models.BooleanField(default=True)

    sustainability_heading = models.CharField(max_length=160, default="Sustainability - Our responsibility")
    sustainability_content = models.TextField(blank=True, help_text="Pull quote shown beside the image.")
    sustainability_image = models.ImageField(upload_to="about/", blank=True, null=True)
    sustainability_image_alt = models.CharField(max_length=255, blank=True)

    recycled_heading = models.CharField(max_length=160, default="Recycled materials")
    recycled_content = models.TextField(blank=True)

    tree_heading = models.CharField(max_length=160, default="With every order, we plant a tree.")
    tree_description = models.TextField(blank=True)

    india_image = models.ImageField(upload_to="about/", blank=True, null=True, help_text="Make in India badge.")
    india_text = models.TextField(blank=True)
    india_visible = models.BooleanField(default=True)

    class Meta:
        verbose_name = "About page"

    def __str__(self):
        return "About page"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        optimise_fields(self, "hero_image", "hero_mobile_image", "sustainability_image", "india_image")

    def value_sections(self):
        return [
            {"heading": self.what_we_make_heading, "content": self.what_we_make_content},
            {"heading": self.how_we_work_heading, "content": self.how_we_work_content},
            {"heading": self.philosophy_heading, "content": self.philosophy_content},
        ]


class ContactPage(SEOFieldsMixin, SingletonModel):
    page_title = models.CharField(max_length=120, default="Contact us")
    banner_image = models.ImageField(upload_to="contact/", blank=True, null=True)
    banner_mobile_image = banner_mobile_image_field(upload_to="contact/")
    banner_mobile_alt = banner_mobile_alt_field()
    banner_alt = models.CharField(max_length=255, blank=True)

    eyebrow = models.CharField(max_length=60, blank=True, default="Contact")
    heading = models.CharField(max_length=200, default="Tell us about your space")
    intro_text = models.TextField(blank=True)

    visit_heading = models.CharField(max_length=80, default="Visit us")
    address = models.TextField(blank=True)
    mail_heading = models.CharField(max_length=80, default="Mail us")
    email = models.EmailField(blank=True)
    hours_heading = models.CharField(max_length=80, default="Working hours")
    working_hours = models.TextField(blank=True)

    form_heading = models.CharField(max_length=160, default="Feel free to reach out")
    form_button_text = models.CharField(max_length=60, default="Send Message")
    success_message = models.CharField(max_length=255, default="Thank you. Your message has been recorded and our team will be in touch.")

    class Meta:
        verbose_name = "Contact page"

    def __str__(self):
        return "Contact page"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        optimise_fields(self, "banner_image", "banner_mobile_image")
