"""
Populate the database with the current COFUR website content.

    python manage.py seed_cofur [--force] [--admin-password ...]

The command is idempotent: records are looked up by slug/name and only
created when missing. Existing records are left untouched unless ``--force``
is passed, in which case their text/image fields are refreshed.

Images referenced by the original static site are copied from ``static/images``
into MEDIA_ROOT (``seed/...``) so every picture is editable from the CMS.
"""
import os
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import (
    Category,
    Collection,
    Product,
    ProductColor,
    ProductFeature,
    ProductImage,
    ProductSpecification,
)
from apps.core.models import NavigationItem, NavigationMenu, SiteSettings
from apps.core.roles import ensure_roles
from apps.pages.models import (
    AboutPage,
    ContactPage,
    Differentiator,
    HomeHeroSlide,
    HomePage,
    HomeStatementLine,
)
from apps.team.models import TeamMember

STATIC_IMAGES = Path(settings.BASE_DIR) / "static" / "images"


def media_from_static(filename, folder):
    """Copy ``static/images/<filename>`` into media storage and return the storage name."""
    if not filename:
        return ""
    source = STATIC_IMAGES / filename
    target = f"seed/{folder}/{filename}"
    if default_storage.exists(target):
        return target
    if not source.exists():
        return ""
    with source.open("rb") as fh:
        return default_storage.save(target, File(fh, name=filename))


class Command(BaseCommand):
    help = "Seed the database with the COFUR website content (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Refresh existing records with the seed content.")
        parser.add_argument("--admin-username", default=os.environ.get("ADMIN_USERNAME", "admin"))
        parser.add_argument("--admin-password", default=os.environ.get("ADMIN_PASSWORD", ""))
        parser.add_argument("--admin-email", default=os.environ.get("ADMIN_EMAIL", "admin@cofur.in"))
        parser.add_argument("--skip-images", action="store_true", help="Do not copy images (faster, for tests).")

    def log(self, message):
        if self.verbosity > 0:
            self.stdout.write(message)

    def handle(self, *args, **options):
        self.force = options["force"]
        self.skip_images = options["skip_images"]
        self.verbosity = int(options.get("verbosity", 1))
        with transaction.atomic():
            self.seed_roles_and_admin(options)
            self.seed_site_settings()
            categories = self.seed_categories()
            collections = self.seed_collections(categories)
            products = self.seed_products(collections)
            self.seed_navigation(categories, collections)
            self.seed_home(products)
            self.seed_about()
            self.seed_contact()
            self.seed_team()
        self.log(self.style.SUCCESS("COFUR content seeded."))

    # ------------------------------------------------------------------ helpers
    def img(self, filename, folder):
        if self.skip_images:
            return ""
        return media_from_static(filename, folder)

    def set_image(self, obj, field, filename, folder):
        current = getattr(obj, field)
        if current and not self.force:
            return
        name = self.img(filename, folder)
        if name:
            getattr(obj, field).name = name

    def upsert(self, model, lookup, defaults, images=None, folder=""):
        """get_or_create; on --force update defaults. Images are set only if empty (or --force)."""
        obj, created = model.objects.get_or_create(defaults=defaults, **lookup)
        if not created and self.force:
            for key, value in defaults.items():
                setattr(obj, key, value)
        for field, filename in (images or {}).items():
            self.set_image(obj, field, filename, folder)
        obj.save()
        self.log(f"  {'created' if created else 'kept'} {model.__name__}: {obj}")
        return obj

    # ------------------------------------------------------------------ steps
    def seed_roles_and_admin(self, options):
        ensure_roles()
        User = get_user_model()
        username = options["admin_username"]
        password = options["admin_password"]
        if not User.objects.filter(username=username).exists():
            if not password:
                self.log(self.style.WARNING(
                    "No admin password supplied (ADMIN_PASSWORD env or --admin-password); superuser not created."
                ))
                return
            User.objects.create_superuser(username=username, email=options["admin_email"], password=password)
            self.log(f"  created superuser '{username}'")
        elif password and self.force:
            user = User.objects.get(username=username)
            user.set_password(password)
            user.is_superuser = True
            user.is_staff = True
            user.save()
            self.log(f"  refreshed superuser '{username}'")

    def seed_site_settings(self):
        site = SiteSettings.load()
        defaults = {
            "site_name": "COFUR",
            "tagline": "Change the way you work",
            "contact_email": "info@cofur.in",
            "whatsapp_number": "919320461618",
            "whatsapp_message": "Hello Cofur, I would like to know more about your furniture.",
            "address": "3rd Floor, Odessa Boutique Offices, Road Number 9, Wagle Industrial Estate, Thane West, Maharashtra 400604, India",
            "google_maps_url": "https://maps.google.com/?q=Odessa+Boutique+Offices,+Road+Number+9,+Wagle+Industrial+Estate,+Thane+West,+Maharashtra+400604",
            "footer_eyebrow": "Let's build better workspaces",
            "footer_title": "We’ll help you find the\nright solution.",
            "footer_primary_cta_text": "Contact us",
            "footer_primary_cta_url": "/contact/",
            "footer_secondary_cta_text": "Download catalog",
            "footer_secondary_cta_url": "/categories/soft-seating/",
            "copyright_text": "Copyright © {year} COFUR Pvt. Ltd. All rights reserved.",
            "default_meta_title": "Cofur — Furniture for the way people work",
            "default_meta_description": "Cofur designs considered furniture for offices, coworking spaces and commercial interiors.",
        }
        if self.force or not site.contact_email:
            for key, value in defaults.items():
                setattr(site, key, value)
        self.set_image(site, "logo", "cofur-logo-dark.webp", "site")
        self.set_image(site, "logo_light", "cofur-logo-light.webp", "site")
        self.set_image(site, "favicon", "cofur-o.png", "site")
        self.set_image(site, "default_og_image", "hero-1-d1440.webp", "site")
        site.save()
        self.log("  site settings ready")

    def seed_categories(self):
        data = [
            {
                "slug": "soft-seating",
                "defaults": {
                    "name": "Soft Seating",
                    "subtitle": "Lounge, modular & breakout",
                    "description": "Lounge, modular and breakout seating for focused, flexible and social workplaces.",
                    "order": 0,
                    "seo_title": "Soft Seating — Cofur",
                    "meta_description": "Explore Cofur soft seating collections for focused, flexible and social workplaces.",
                },
                "images": {
                    "thumbnail_image": "category-seating.png",
                    "banner_image": "banner-seating.png",
                    "lifestyle_image": "seating-lifestyle-v2-d736.webp",
                },
            },
            {
                "slug": "acoustic-lights",
                "defaults": {
                    "name": "Acoustic Lights",
                    "subtitle": "Pendants & suspended fixtures",
                    "order": 1,
                },
                "images": {"thumbnail_image": "category-acoustic.png"},
            },
            {
                "slug": "acoustic-ceilings",
                "defaults": {
                    "name": "Acoustic Ceilings",
                    "subtitle": "Rafts, baffles & clouds",
                    "order": 2,
                },
                "images": {"thumbnail_image": "statement-3-d1024.webp"},
            },
            {
                "slug": "phone-booth",
                "defaults": {
                    "name": "Phone Booth",
                    "subtitle": "Focus rooms & quiet pods",
                    "order": 3,
                },
                "images": {"thumbnail_image": "why-cofur-v2-d960.webp"},
            },
        ]
        return {
            item["slug"]: self.upsert(Category, {"slug": item["slug"]}, item["defaults"], item["images"], "categories")
            for item in data
        }

    def seed_collections(self, categories):
        seating = categories["soft-seating"]
        data = [
            {
                "slug": "cove",
                "defaults": {
                    "name": "Cove",
                    "category": seating,
                    "tagline": "Privacy and focus within open spaces",
                    "description": "Explore the Cove collection: open comfort, private focus and shared seating.",
                    "heading": "Cove\ncollection",
                    "banner_alt": "Cove lounge seating beneath a sculptural ring pendant in an open workspace",
                    "card_style": "cove",
                    "order": 0,
                    "seo_title": "Cove Collection — Cofur",
                    "meta_description": "Explore the Cove collection: open comfort, private focus and shared seating.",
                },
                "images": {"image": "green-top2.webp", "banner_image": "banner-cove-d1440.webp", "banner_mobile_image": "banner-cove-m614.webp"},
            },
            {
                "slug": "pebble",
                "defaults": {
                    "name": "Pebble",
                    "category": seating,
                    "tagline": "Flexible, organic seating for fluid environments",
                    "card_style": "pebble",
                    "order": 1,
                },
                "images": {"image": "dark-blue-front1.webp", "banner_image": "framer-pebble.jpg"},
            },
            {
                "slug": "orbit",
                "defaults": {
                    "name": "Orbit",
                    "category": seating,
                    "tagline": "Large-scale social hubs with a biophilic touch",
                    "card_style": "orbit",
                    "order": 2,
                },
                "images": {"image": "red-up1.webp", "banner_image": "framer-orbit.jpg"},
            },
            {
                "slug": "grove",
                "defaults": {
                    "name": "Grove",
                    "category": seating,
                    "tagline": "Nature-inspired comfort for modern workspaces",
                    "card_style": "grove",
                    "order": 3,
                },
                "images": {"image": "beige-front3.webp", "banner_image": "framer-grove.jpg"},
            },
        ]
        return {
            item["slug"]: self.upsert(Collection, {"slug": item["slug"]}, item["defaults"], item["images"], "collections")
            for item in data
        }

    def seed_products(self, collections):
        cove = collections["cove"]
        grove = collections["grove"]
        simple = [
            ("cove-solo-lounge", "Cove Solo Lounge", "Open comfort for casual connections.", "yellow-front3.webp", "cove-hover-solo-lounge.png", "1 seater"),
            ("cove-solo", "Cove Solo", "Your personal sanctuary at work.", "blue-front4.webp", "cove-hover-solo.png", "1 seater"),
            ("cove-duo", "Cove Duo", "A little peace in a busy place", "red-front5.webp", "cove-hover-duo.png", "2 seater"),
            ("cove-team", "Cove Team", "Big ideas need a quiet space", "green-top3.webp", "cove-hover-team.png", "4 seater"),
            ("cove-connect", "Cove Connect", "Designed for effortless collaboration", "dark-blue-top1.webp", "cove-hover-connect.png", "4 seater"),
        ]
        products = {}
        for order, (slug, name, tagline, main, hover, capacity) in enumerate(simple):
            products[slug] = self.upsert(
                Product,
                {"slug": slug},
                {
                    "name": name,
                    "name_prefix": "Cove",
                    "collection": cove,
                    "tagline": tagline,
                    "short_description": tagline,
                    "seating_capacity": capacity,
                    "areas": "Workplace\nCoworking\nHospitality",
                    "status": Product.STATUS_PUBLISHED,
                    "order": order,
                    "seo_title": f"{name} — Cofur",
                    "meta_description": f"{name}: {tagline}",
                },
                {"main_image": main, "hover_image": hover},
                "products",
            )

        social = self.upsert(
            Product,
            {"slug": "cove-social"},
            {
                "name": "Cove Social",
                "name_prefix": "Cove",
                "collection": cove,
                "tagline": "Comfort better shared",
                "short_description": "Comfort better shared",
                "description": (
                    "The Cove Social is designed for shared comfort, bringing people together in a relaxed and welcoming "
                    "setting. Its open, low-back form encourages natural interaction, making it ideal for casual conversations, "
                    "quick meetings, and everyday collaboration. With soft cushioning and a light architectural presence, it "
                    "creates an inviting space where connections happen effortlessly."
                ),
                "main_image_alt": "Cove Social two-seater sofa, front view",
                "seating_capacity": "2 seater",
                "areas": "Workplace\nCoworking\nHospitality",
                "materials": "Powder coated steel\nHigh density foam\nFabric",
                "dimension_width": "160",
                "dimension_depth": "30",
                "dimension_height": "80",
                "dimension_seat_height": "42",
                "dimension_weight": "90",
                "status": Product.STATUS_PUBLISHED,
                "order": 5,
                "seo_title": "Cove Social — Cofur",
                "meta_description": "Cove Social two-seater lounge seating product specifications, finishes, gallery and enquiry.",
            },
            {"main_image": "red-front6.webp", "card_image": "red-front4.webp", "hover_image": "cove-hover-social.png", "finish_image": "social-finish-sand.png"},
            "products",
        )
        products["cove-social"] = social
        self.seed_product_children(social)
        social.related_products.set([products["cove-solo"], products["cove-solo-lounge"], products["cove-duo"], products["cove-team"]])

        products["grove-trio"] = self.upsert(
            Product,
            {"slug": "grove-trio"},
            {
                "name": "Grove Trio",
                "name_prefix": "Grove",
                "collection": grove,
                "tagline": "Nature-inspired comfort for modern workspaces",
                "short_description": "Grove Trio upholstered modular seating with an integrated planter.",
                "main_image_alt": "Grove Trio upholstered modular seating",
                "seating_capacity": "3 seater",
                "areas": "Workplace\nCoworking\nHospitality",
                "status": Product.STATUS_PUBLISHED,
                "is_featured": True,
                "order": 0,
            },
            {"main_image": "featured-grove.jpg", "hover_image": "beige-front3.webp"},
            "products",
        )
        return products

    def seed_product_children(self, product):
        if product.specifications.exists() and not self.force:
            return
        product.specifications.all().delete()
        for order, (label, value) in enumerate([
            ("Frame", "Powder coated steel"),
            ("Upholstery", "High density foam"),
            ("Cover", "Fabric (custom available on request)"),
            ("Base", "White metal frame"),
        ]):
            ProductSpecification.objects.create(product=product, label=label, value=value, order=order)

        product.feature_items.all().delete()
        for order, text in enumerate([
            "Reception areas and waiting lounges",
            "Coworking spaces and breakout zones",
            "Informal meeting points and quick discussions",
            "Collaborative office environments and social hubs",
        ]):
            ProductFeature.objects.create(product=product, text=text, kind=ProductFeature.KIND_FEATURE, order=order)
        for order, text in enumerate([
            "Vacuum upholstery regularly on a low setting to lift surface dust.",
            "Blot spills immediately with a clean, dry cloth — do not rub.",
            "Professional clean recommended; covers are removable on request.",
            "Keep out of prolonged direct sunlight to protect colour fastness.",
        ]):
            ProductFeature.objects.create(product=product, text=text, kind=ProductFeature.KIND_CARE, order=order)

        product.colors.all().delete()
        for order, (name, swatch, finish) in enumerate([
            ("Sand beige", "image35.png", "social-finish-sand.png"),
            ("Deep teal", "image36.png", "blue-zoom21.png"),
            ("Slate violet", "image37.png", "social-gallery-side.png"),
        ]):
            color = ProductColor(product=product, name=name, order=order)
            self.set_image(color, "swatch_image", swatch, "products/swatches")
            self.set_image(color, "finish_image", finish, "products/finishes")
            color.save()

        product.images.all().delete()
        detail = [
            ("red-front6.webp", "Cove Social front view", ""),
            ("social-finish-sand.png", "Cove Social in sand beige upholstery", ""),
            ("red-front6.webp", "Cove Social front view", ""),
            ("social-finish-sand.png", "Cove Social in sand beige upholstery", ""),
        ]
        dimension = [
            ("image38.png", "Cove Social front dimensions", ""),
            ("image39.png", "Cove Social side dimensions", ""),
            ("image40.png", "Cove Social perspective dimensions", ""),
        ]
        gallery = [
            ("why-cofur-v2-d960.webp", "Timber focus booth with an acoustic tile wall", "Focus booth"),
            ("cove-hover-social.png", "Cove Social arranged as a shared meeting island", "Shared meeting island"),
            ("chat-gpt-image-apr222026114530-pm1.jpg", "Cove Social in a relaxed workplace lounge", "Workplace lounge"),
            ("social-finish-sand.png", "Cove Social in sand beige upholstery", "Sand beige colourway"),
            ("social-mosaic-detail.png", "Cove Social upholstery close-up", "Upholstery detail"),
            ("statement-3-d1024.webp", "Acoustic ceiling rafts above a workplace cafe", "Acoustic ceiling"),
        ]
        for kind, items in ((ProductImage.KIND_DETAIL, detail), (ProductImage.KIND_DIMENSION, dimension), (ProductImage.KIND_GALLERY, gallery)):
            for order, (filename, alt, caption) in enumerate(items):
                image = ProductImage(product=product, kind=kind, alt_text=alt, caption=caption, order=order)
                name = self.img(filename, "products/gallery")
                if not name:
                    continue
                image.image.name = name
                image.save()

    def seed_navigation(self, categories, collections):
        header, _ = NavigationMenu.objects.get_or_create(slug="header", defaults={"name": "Header"})
        footer, _ = NavigationMenu.objects.get_or_create(slug="footer", defaults={"name": "Footer"})
        if header.items.exists() and not self.force:
            self.log("  navigation kept")
            return
        header.items.all().delete()
        footer.items.all().delete()

        def item(menu, label, order, parent=None, **kwargs):
            return NavigationItem.objects.create(menu=menu, label=label, order=order, parent=parent, **kwargs)

        collections_item = item(header, "Collections", 0, link_type="none")
        seating = item(header, "Soft Seating", 0, collections_item, link_type="category", category=categories["soft-seating"])
        item(header, "Cove Series", 0, seating, link_type="collection", collection=collections["cove"])
        item(header, "Pebble Series", 1, seating, link_type="collection", collection=collections["pebble"])
        item(header, "Grove Series", 2, seating, link_type="collection", collection=collections["grove"])
        item(header, "Orbit Series", 3, seating, link_type="collection", collection=collections["orbit"])

        acoustics = item(header, "Acoustics", 1, collections_item, link_type="none")
        item(header, "Acoustic Lights", 0, acoustics, link_type="category", category=categories["acoustic-lights"])
        item(header, "Acoustic Ceilings & Baffles", 1, acoustics, link_type="category", category=categories["acoustic-ceilings"])
        item(header, "Acoustic Wall Panels", 2, acoustics, link_type="external", external_url="/contact/?collection=acoustic-wall-panels")
        item(header, "Acoustic Accessories", 3, acoustics, link_type="external", external_url="/contact/?collection=acoustic-accessories")

        storage = item(header, "Storage", 2, collections_item, link_type="none")
        for n in range(1, 5):
            item(header, f"Storage 0{n}", n, storage, link_type="external", external_url="/contact/?collection=storage")

        booth = item(header, "Phone Booth", 3, collections_item, link_type="none")
        for n in range(1, 4):
            item(header, f"Phone Booth 0{n}", n, booth, link_type="category", category=categories["phone-booth"])

        accessories = item(header, "Accessories", 4, collections_item, link_type="none")
        for n in range(1, 5):
            item(header, f"Accessories 0{n}", n, accessories, link_type="external", external_url="/contact/?collection=accessories")

        item(header, "About", 1, link_type="internal", internal_page="website:about")
        item(header, "Communications", 2, link_type="internal", internal_page="website:about", url_suffix="#sustainability")
        item(header, "Catalogues", 3, link_type="category", category=categories["soft-seating"], css_class="nav-spacer")
        item(header, "Contact", 4, link_type="internal", internal_page="website:contact")

        item(footer, "Collections", 0, link_type="internal", internal_page="website:home", url_suffix="#our-products")
        item(footer, "About", 1, link_type="internal", internal_page="website:about")
        item(footer, "Communications", 2, link_type="internal", internal_page="website:about", url_suffix="#sustainability")
        item(footer, "Catalogues", 3, link_type="category", category=categories["soft-seating"])
        item(footer, "Contact", 4, link_type="internal", internal_page="website:contact")
        self.log("  navigation seeded")

    def seed_home(self, products):
        page = HomePage.load()
        defaults = {
            "hero_heading": "Furniture for the way people actually work",
            "intro_heading": "We help create spaces that people",
            "intro_heading_highlight": "want to work in.",
            "statement_heading": "We design spaces that work better. We build solutions that last. We create comfort that matters.",
            "statement_description": "You bring the vision. We bring expertise and design to make it work.",
            "statement_cta_text": "About us",
            "statement_cta_url": "/about/",
            "featured_heading": "Featured products",
            "featured_cta_text": "View products",
            "why_heading": "What makes COFUR different",
            "why_image_alt": "Timber focus booth with a beige acoustic tile wall, copper wall light and two stools",
            "seo_title": "Cofur — Furniture for the way people work",
            "meta_description": "Cofur designs considered furniture for offices, coworking spaces and commercial interiors.",
            "og_title": "Cofur Furniture",
            "og_description": "Furniture for the way people actually work.",
        }
        fresh = not page.seo_title
        if fresh or self.force:
            for key, value in defaults.items():
                setattr(page, key, value)
        self.set_image(page, "why_image", "why-cofur-v2-d960.webp", "home")
        page.save()

        slides = [
                ("hero-1-d1440.webp", "hero-1-m564.webp", "Reception lounge with cream armchairs and planting beneath a curved timber ceiling"),
                ("hero-2-d1440.webp", "hero-2-m564.webp", "Office reception with a terracotta honeycomb acoustic ceiling above a circular welcome desk"),
                ("hero-3-d1440.webp", "hero-3-m768.webp", "Colleagues meeting at a long table on herringbone flooring beside timber slat walls"),
                ("hero-4-d1440.webp", "hero-4-m598.webp", "Breakout lounge with rust swivel chairs against a blue and white acoustic panel wall"),
                ("hero-5-d1440.webp", "hero-5-m768.webp", "Office kitchen and social stair with acoustic baffles above a shared dining table"),
        ]
        if not page.hero_slides.exists() or self.force:
            page.hero_slides.all().delete()
            for order, (desktop, mobile, alt) in enumerate(slides):
                slide = HomeHeroSlide(page=page, alt_text=alt, order=order)
                self.set_image(slide, "image", desktop, "home/hero")
                self.set_image(slide, "mobile_image", mobile, "home/hero")
                if slide.image:
                    slide.save()
        else:
            for order, (desktop, mobile, alt) in enumerate(slides):
                slide = page.hero_slides.filter(order=order).first()
                if slide and not slide.mobile_image:
                    self.set_image(slide, "mobile_image", mobile, "home/hero")
                    slide.save(update_fields=["mobile_image"])

        lines = [
                ("We design", "spaces that work better.", "statement-1-d1440.webp", "statement-1-m387.webp", "Pale green lounge chairs and a navy banquette in a quiet breakout area"),
                ("We build", "solutions that last.", "statement-2-d1440.webp", "statement-2-m768.webp", "Green disc acoustic pendants above a circular planted seating island"),
                ("We create", "comfort that matters.", "statement-3-d1440.webp", "statement-3-m768.webp", "Magenta ribbon acoustic ceiling rafts above a workplace cafe"),
        ]
        if not page.statement_lines.exists() or self.force:
            page.statement_lines.all().delete()
            for order, (verb, text, desktop, mobile, alt) in enumerate(lines):
                line = HomeStatementLine(page=page, verb=verb, text=text, alt_text=alt, order=order)
                self.set_image(line, "image", desktop, "home/statement")
                line.save()

        if not page.differentiators.exists() or self.force:
            page.differentiators.all().delete()
            for order, heading in enumerate(["Design with purpose", "Performance you can live with", "Flexibility built in"]):
                Differentiator.objects.create(page=page, heading=heading, order=order)

        self.log("  home page seeded")

    def seed_about(self):
        page = AboutPage.load()
        defaults = {
            "hero_heading": "DESIGNED FOR SPACE. BUILT FOR COMFORT",
            "hero_image_alt": "Sage green lounge armchair with a magazine pocket beside a planted courtyard window",
            "intro_heading": "We design spaces where work actually happens.",
            "intro_text": (
                "COFUR exists because India's commercial spaces deserve better. We make furniture for architects, interior "
                "designers, and forward-thinking organizations who understand that how a space feels directly impacts how work happens."
            ),
            "what_we_make_heading": "What We Make",
            "what_we_make_content": (
                "Our collection spans acoustic privacy pods, modular collaborative seating, acoustic ceiling systems and bespoke "
                "furniture solutions. Each piece is designed to solve a real problem: focus in open offices. Spontaneous collaboration. "
                "Acoustic comfort. Flexibility as teams grow and shift.\n\n"
                "We're not a traditional furniture retailer. We're specification-ready. Our products come with architectural details, "
                "product codes, and spatial language because your space matters as much as ours does."
            ),
            "how_we_work_heading": "How We Work",
            "how_we_work_content": (
                "Everything is designed and developed in India. We combine thoughtful aesthetics with practical affordability, no import "
                "taxes, no middlemen, just skilled craftsmanship embedded in how you actually work. Quality is non-negotiable. "
                "Customization is expected."
            ),
            "philosophy_heading": "Our Philosophy",
            "philosophy_content": (
                "Modern design shouldn't be a luxury. Acoustic comfort shouldn't be rare. Collaborative spaces shouldn't feel corporate. "
                "We believe in designing for reality: spaces that are beautiful, functional, and affordable. Furniture that lasts. "
                "Spaces that feel like places people want to be."
            ),
            "mission_heading": "Our Mission",
            "mission_content": "Designing space with purpose. Creating comfort by design",
            "team_heading": "Our Team",
            "find_us_heading": "Where to find us",
            "find_us_company": "COFUR Pvt. Ltd.",
            "find_us_address": "3rd Floor, Odessa Boutique Offices, Road Number 9, Wagle Industrial Estate, Thane West, Maharashtra 400604",
            "find_us_map_url": "https://maps.google.com/maps?q=Odessa%20Boutique%20Offices%2C%20Road%20Number%209%2C%20Wagle%20Industrial%20Estate%2C%20Thane%20West%2C%20Maharashtra%20400604&z=17&output=embed",
            "sustainability_heading": "Sustainability - Our responsibility",
            "sustainability_content": '"We believe responsibility starts with materials"',
            "sustainability_image_alt": "Cupped hands holding a young sapling in dark soil — a tree planted with every Cofur order",
            "recycled_heading": "Recycled materials",
            "recycled_content": (
                "Our acoustic collection, ceiling systems, wall panels, and acoustic lights are built from PET boards, made entirely from "
                "recycled plastic waste. Rather than ending up in landfills, that plastic is transformed into a material that absorbs sound, "
                "reduces noise, and creates calmer, more focused work environments.\n\n"
                "It's a simple equation: repurposed material solving a real problem. No marketing, no compromise on performance."
            ),
            "tree_heading": "With every order, we plant a tree.",
            "tree_description": (
                "When you choose COFUR, you're not just transforming your workspace, you're contributing to India's green future. For each "
                "order that leaves our studio, a tree is planted in your name. Small action. Real impact.\n\n"
                "Every acoustic panel we make, every piece of furniture we craft, is a choice to design thoughtfully for the spaces we build "
                "and the world we build them in. Because changing how India works means changing how we make what we use."
            ),
            "india_text": (
                "We believe great workplace design should understand the people it is designed for. That is why COFUR designs and "
                "manufactures in India, creating solutions that reflect the way Indian workplaces evolve, collaborate, and grow. Contemporary "
                "in design and practical in purpose, our products bring together local craftsmanship, flexibility, and thoughtful engineering "
                "to create spaces made for how India works today."
            ),
            "seo_title": "About Cofur — Thoughtful Furniture",
            "meta_description": "Meet Cofur and learn about our philosophy, team, sustainability and made-in-India approach.",
        }
        if not page.intro_text or self.force:
            for key, value in defaults.items():
                setattr(page, key, value)
        self.set_image(page, "hero_image", "banner-about-v2-d1440.webp", "about")
        self.set_image(page, "hero_mobile_image", "banner-about-v2-m768.webp", "about")
        self.set_image(page, "sustainability_image", "sustainability.jpg", "about")
        self.set_image(page, "india_image", "make-in-india.png", "about")
        page.save()
        self.log("  about page seeded")

    def seed_contact(self):
        page = ContactPage.load()
        defaults = {
            "page_title": "Contact us",
            "banner_alt": "Contact Us — a navy telephone handset on a pale studio background",
            "eyebrow": "Contact",
            "heading": "Tell us about your space",
            "intro_text": (
                "Have a project in mind, or need help choosing the right solution? Share a few details and our design team "
                "will come back to you within two working days."
            ),
            "visit_heading": "Visit us",
            "address": "COFUR Pvt. Ltd.\n3rd Floor, Odessa Boutique Offices, Road Number 9, Wagle Industrial Estate, Thane West, Maharashtra 400604, India",
            "mail_heading": "Mail us",
            "email": "info@cofur.in",
            "hours_heading": "Working hours",
            "working_hours": "Monday–Saturday\n10:00 – 19:00 IST",
            "form_heading": "Feel free to reach out",
            "form_button_text": "Send Message",
            "success_message": "Thank you. Your message has been recorded and our team will be in touch.",
            "seo_title": "Contact — Cofur",
            "meta_description": "Talk to Cofur about your workplace furniture project — acoustics, soft seating and bespoke solutions.",
        }
        if not page.intro_text or self.force:
            for key, value in defaults.items():
                setattr(page, key, value)
        self.set_image(page, "banner_image", "banner-contact-d1440.webp", "contact")
        self.set_image(page, "banner_mobile_image", "banner-contact-m768.webp", "contact")
        page.save()
        self.log("  contact page seeded")

    def seed_team(self):
        members = [
            {
                "name": "J Sidheshwar",
                "designation": "Chairman Gubbi civil engineers LTD",
                "image": "j-sidheshwar.jpeg",
                "biography": (
                    "With more than three decades of experience in the civil engineering industry, he has built and led Gubbi Civil "
                    "Engineers Limited into an established engineering organization specialising in structural repairs, rehabilitation, "
                    "retrofitting and strengthening of complex industrial, commercial and infrastructure assets.\n\n"
                    "Over its 33+ year journey, Gubbi Civil Engineers has successfully executed more than 1,000 projects and worked with "
                    "over 150 clients across India, including leading organizations from the manufacturing, infrastructure, energy, "
                    "petrochemical, banking and corporate sectors.\n\n"
                    "As Chairman and Mentor to COFUR, he brings this depth of industry knowledge and entrepreneurial experience to the next "
                    "generation of the Group. His guidance helps COFUR build on the same principles of reliability, quality, technical "
                    "understanding and long-term client relationships while creating a new-age Indian brand for commercial furniture and "
                    "workplace solutions.\n\n"
                    "His role at COFUR represents the bridge between decades of proven engineering experience and a new generation of "
                    "design-led workplace innovation."
                ),
            },
            {
                "name": "J Gururaj",
                "designation": "Founder & CEO",
                "image": "gururaj.jpg",
                "biography": (
                    "I started COFUR with a simple observation: the way we work had evolved, but the spaces around us had not.\n\n"
                    "Modern workplaces need to support different moments—quiet concentration, private conversations, spontaneous "
                    "collaboration and meaningful interaction. Yet many commercial spaces in India are still designed primarily around "
                    "appearance and capacity, with little attention given to how people actually experience them.\n\n"
                    "COFUR was created to bridge this gap.\n\n"
                    "We design acoustic pods, modular seating and collaborative furniture that respond to real workplace needs. Every "
                    "product is guided by a clear purpose: to reduce distraction, improve comfort, encourage connection and help spaces "
                    "adapt to the people using them.\n\n"
                    "Our approach brings together thoughtful design, practical functionality and a clear understanding of the Indian "
                    "workplace. We believe furniture should do more than complete an interior—it should contribute to productivity, "
                    "well-being and the culture of an organisation.\n\n"
                    "Our mission is to transform India’s commercial spaces by making purposeful design an essential part of every "
                    "workplace, not a luxury.\n\n"
                    "Because when a space is designed around how people actually work, everything works better."
                ),
            },
            {
                "name": "Kunal J",
                "designation": "Design executive",
                "image": "kunal.jpg",
                "quote": (
                    "“I measure a successful design not by how appealing it looks, but how it holds up after years of daily use: "
                    "still functional, still preferred & still admired”."
                ),
                "biography": (
                    "Kunal Jagany heads the design department at COFUR, playing a vital role in shaping the creative direction of the "
                    "brand. With a deep understanding of design nuances and project management, his work is characterised by an acutely "
                    "developed aesthetic eye, and a distinct grasp of colour, materials, and texture. His knack for finding function and "
                    "purpose in every design, and his active involvement in the entire design process, is what enables COFUR to take a "
                    "raw idea from concept to a developed product of the utmost quality for our clients."
                ),
            },
            {
                "name": "Vedangi P",
                "designation": "BD Executive",
                "image": "vedangi.jpg",
                "quote": (
                    "As a Business Development Executive at COFUR, Vedangi is focused on expanding the brand’s reach and creating "
                    "meaningful opportunities across the commercial and workplace design ecosystem. She engages with architects, PMCs, "
                    "businesses and other industry stakeholders to understand their requirements and introduce solutions that address "
                    "real spatial and acoustic challenges."
                ),
                "biography": (
                    "Her work spans market research, lead generation, client outreach, relationship building and developing new business "
                    "opportunities for the company. At COFUR, she works towards building a brand that people recognise, trust and want to "
                    "work with."
                ),
            },
        ]
        for order, member in enumerate(members):
            image = member.pop("image")
            member["order"] = order
            self.upsert(TeamMember, {"name": member["name"]}, member, {"image": image}, "team")
