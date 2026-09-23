from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import Product
from apps.core.models import SiteSettings


class WebsiteViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_cofur", skip_images=True, verbosity=0)

    def test_home_renders_seeded_content(self):
        response = self.client.get(reverse("website:home"))
        self.assertEqual(response.status_code, 200)
        for text in ["Furniture for the way people actually work", "Soft Seating", "Featured products", "What makes COFUR different", "Grove Trio", "Design with purpose", "We design"]:
            self.assertContains(response, text)
        self.assertContains(response, 'data-page="home"')
        self.assertContains(response, "mega-menu")
        self.assertContains(response, "Cove Series")

    def test_about_renders_team(self):
        response = self.client.get(reverse("website:about"))
        self.assertEqual(response.status_code, 200)
        for name in ["J Sidheshwar", "J Gururaj", "Kunal J", "Vedangi P", "Recycled materials", "Where to find us"]:
            self.assertContains(response, name)

    def test_contact_collection_ref_redirects_to_dynamic_page(self):
        response = self.client.get(reverse("website:contact") + "?collection=pebble")
        self.assertRedirects(response, "/collections/pebble/")
        response = self.client.get(reverse("website:contact") + "?collection=phone-booth")
        self.assertRedirects(response, "/categories/phone-booth/")
        self.assertEqual(self.client.get("/contact.html?collection=pebble", follow=True).redirect_chain[-1][0], "/collections/pebble/")

    def test_contact_page(self):
        response = self.client.get(reverse("website:contact") + "?collection=acoustic-wall-panels")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tell us about your space")
        self.assertContains(response, "info@cofur.in")
        self.assertContains(response, 'name="collection" value="acoustic-wall-panels"')
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_category_and_collection_pages(self):
        response = self.client.get("/categories/soft-seating/")
        self.assertEqual(response.status_code, 200)
        for name in ["Cove collection", "Pebble collection", "Orbit collection", "Grove collection"]:
            self.assertContains(response, name)
        self.assertContains(response, 'href="/collections/pebble/"')
        response = self.client.get("/collections/cove/")
        self.assertEqual(response.status_code, 200)
        for name in ["Solo Lounge", "<em>Cove</em> Duo", "<em>Cove</em> Team", "<em>Cove</em> Connect", "<em>Cove</em> Social"]:
            self.assertContains(response, name)
        self.assertEqual(self.client.get("/collections/").status_code, 200)

    def test_collection_page_matches_legacy_structure(self):
        from apps.catalog.models import Collection
        from apps.core.tests import make_image

        cove = Collection.objects.get(slug="cove")
        cove.banner_image = make_image("banner-cove.png")  # the seed runs with --skip-images in tests
        cove.banner_mobile_image = make_image("banner-cove-m.png")
        cove.save()
        solo = Product.objects.get(slug="cove-solo-lounge")
        solo.card_image = make_image("yellow-front3.png")
        solo.hover_image = make_image("cove-hover-solo-lounge.png")
        solo.save()
        solo.refresh_from_db()
        response = self.client.get("/collections/cove/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertContains(response, 'data-page="cove-collection"')
        self.assertContains(response, '<main class="cove-page">')
        self.assertContains(response, '<picture data-shot="banner-cove">')
        self.assertContains(response, '<h1>Cove<br>collection</h1>')
        self.assertContains(response, 'alt="Cove lounge seating beneath a sculptural ring pendant in an open workspace"')
        self.assertContains(response, "<title>Cove Collection — Cofur</title>")
        self.assertContains(response, 'content="Explore the Cove collection: open comfort, private focus and shared seating."')
        # six published cards, in product order, each linking to its own product page
        self.assertEqual(html.count('class="cove-card"'), 6)
        order = [html.index(f'href="/products/{slug}/"') for slug in ["cove-solo-lounge", "cove-solo", "cove-duo", "cove-team", "cove-connect", "cove-social"]]
        self.assertEqual(order, sorted(order))
        self.assertNotIn("cove-social.html", html)
        self.assertContains(response, '<h3 data-static-title><em>Cove</em> Solo Lounge</h3>')
        self.assertContains(response, '<p class="eyebrow">Open comfort for casual connections.</p>')
        self.assertContains(response, f'<div class="cove-card-media"><img src="{solo.card_image.url}" data-hover-src="{solo.hover_image.url}" alt="Cove Solo Lounge"></div>')
        self.assertContains(response, '<b>View product</b>')
        # inactive collections are not public
        Collection.objects.filter(slug="cove").update(is_active=False)
        self.assertEqual(self.client.get("/collections/cove/").status_code, 404)

    def test_collection_page_hides_drafts_and_shows_empty_message(self):
        Product.objects.filter(slug="cove-duo").update(status=Product.STATUS_DRAFT)
        response = self.client.get("/collections/cove/")
        self.assertNotContains(response, 'href="/products/cove-duo/"')
        self.assertEqual(response.content.decode().count('class="cove-card"'), 5)
        response = self.client.get("/collections/pebble/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Products coming soon")
        self.assertEqual(response.content.decode().count('class="cove-card"'), 0)

    def test_product_detail(self):
        response = self.client.get("/products/cove-social/")
        self.assertEqual(response.status_code, 200)
        for text in ["Comfort better shared", "Powder coated steel", "Sand beige", "Material care", "Related products", "enquire-modal", "Cove Solo Lounge", "160 <small>cm</small>"]:
            self.assertContains(response, text)

    def test_draft_product_hidden_from_public_but_visible_to_staff(self):
        product = Product.objects.get(slug="cove-solo")
        product.status = Product.STATUS_DRAFT
        product.save()
        self.assertEqual(self.client.get("/products/cove-solo/").status_code, 404)
        from django.contrib.auth import get_user_model

        self.client.force_login(get_user_model().objects.create_user("staff", password="x", is_staff=True))
        self.assertEqual(self.client.get("/products/cove-solo/").status_code, 200)

    def test_unknown_slugs_404(self):
        self.assertEqual(self.client.get("/products/nope/").status_code, 404)
        self.assertEqual(self.client.get("/collections/nope/").status_code, 404)
        self.assertEqual(self.client.get("/categories/nope/").status_code, 404)

    def test_legacy_redirects(self):
        for old, new in [
            ("/index.html", "/"),
            ("/about.html", "/about/"),
            ("/contact.html?collection=pebble", "/contact/?collection=pebble"),
            ("/soft-seating-main-category.html", "/categories/soft-seating/"),
            ("/cove-collection-sub-cateogry.html", "/collections/cove/"),
            ("/product-detailes.html", "/products/cove-social/"),
            ("/collection.html", "/collections/cove/"),
        ]:
            response = self.client.get(old)
            self.assertEqual(response.status_code, 301, old)
            self.assertEqual(response["Location"], new, old)

    def test_seo_tags_rendered(self):
        response = self.client.get("/products/cove-social/")
        self.assertContains(response, "<title>Cove Social — Cofur</title>")
        self.assertContains(response, 'property="og:title"')
        self.assertContains(response, 'rel="canonical"')
        self.assertContains(response, 'name="robots" content="index, follow"')
        site = SiteSettings.load()
        site.default_meta_description = "Site default description"
        site.save()
        response = self.client.get("/collections/")
        self.assertContains(response, "Collections — Cofur")

    def test_navigation_and_footer_from_database(self):
        from apps.core.models import NavigationItem

        NavigationItem.objects.filter(label="Communications").update(label="Sustainability news")
        response = self.client.get("/")
        self.assertContains(response, "Sustainability news")
        self.assertContains(response, "COFUR Pvt. Ltd. All rights reserved")
        self.assertContains(response, "Download catalog")


class MosaicVideoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_cofur", skip_images=True, verbosity=0)

    def test_embed_url_parsing(self):
        from apps.catalog.models import ProductImage

        cases = {
            "https://www.youtube.com/watch?v=abc123XYZ": "https://www.youtube-nocookie.com/embed/abc123XYZ",
            "https://youtu.be/abc123XYZ?t=10": "https://www.youtube-nocookie.com/embed/abc123XYZ",
            "https://youtube.com/shorts/abc123XYZ": "https://www.youtube-nocookie.com/embed/abc123XYZ",
            "https://vimeo.com/123456": "https://player.vimeo.com/video/123456",
            "https://example.com/video.mp4": "",
        }
        for url, expected in cases.items():
            self.assertEqual(ProductImage(video_url=url).embed_url, expected, url)

    def test_mosaic_renders_video_file_link_and_image(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from apps.catalog.models import ProductImage
        from apps.core.tests import make_image

        product = Product.objects.get(slug="cove-social")
        product.images.filter(kind="detail").delete()
        ProductImage.objects.create(product=product, kind="detail", video_file=SimpleUploadedFile("clip.mp4", b"\x00\x00\x00\x18ftypmp42"), image=make_image("poster.png"), alt_text="Clip")
        ProductImage.objects.create(product=product, kind="detail", video_url="https://youtu.be/abc123XYZ", caption="Walkthrough")
        ProductImage.objects.create(product=product, kind="detail", image=make_image("still.png"), alt_text="Still")
        html = self.client.get("/products/cove-social/").content.decode()
        self.assertIn('<video class="product-mosaic__video" controls playsinline preload="metadata" poster="', html)
        self.assertIn('<iframe class="product-mosaic__video" src="https://www.youtube-nocookie.com/embed/abc123XYZ"', html)
        self.assertIn('alt="Still"', html)
        self.assertEqual(html.count("product-mosaic__tile--video"), 2)


class BannerMobileImageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_cofur", skip_images=True, verbosity=0)

    def _img(self, name="m.png"):
        from apps.core.tests import make_image

        return make_image(name, size=(300, 400))

    def test_collection_banner_source_only_with_mobile_image(self):
        from apps.catalog.models import Collection

        cove = Collection.objects.get(slug="cove")
        cove.banner_image = self._img("d.png")
        cove.banner_mobile_image = None
        cove.save()
        html = self.client.get("/collections/cove/").content.decode()
        banner = html.split('data-shot="banner-cove"')[1].split("</picture>")[0]
        self.assertNotIn("<source", banner)
        self.assertIn("<img src=", banner)
        cove.banner_mobile_image = self._img("m.png")
        cove.banner_mobile_alt = "Cove lounge, mobile crop"
        cove.save()
        html = self.client.get("/collections/cove/").content.decode()
        banner = html.split('data-shot="banner-cove"')[1].split("</picture>")[0]
        self.assertIn(f'<source media="(max-width:767px)" srcset="{cove.banner_mobile_image.url}"', banner)
        self.assertIn('data-mobile-alt="Cove lounge, mobile crop"', banner)
        self.assertIn('fetchpriority="high"', banner)

    def test_home_about_contact_category_banners(self):
        from apps.catalog.models import Category
        from apps.pages.models import AboutPage, ContactPage, HomeHeroSlide, HomePage

        slide = HomeHeroSlide.objects.create(page=HomePage.load(), image=self._img("s.png"), mobile_image=self._img("sm.png"), alt_text="Slide")
        self.assertIn(f'<source media="(max-width:767px)" srcset="{slide.mobile_image.url}">', self.client.get("/").content.decode())
        about = AboutPage.load(); about.hero_image = self._img("a.png"); about.hero_mobile_image = self._img("am.png"); about.save()
        self.assertIn(f'srcset="{about.hero_mobile_image.url}"', self.client.get("/about/").content.decode())
        contact = ContactPage.load(); contact.banner_image = self._img("c.png"); contact.banner_mobile_image = None; contact.save()
        self.assertNotIn("<source", self.client.get("/contact/").content.decode().split('data-shot="banner-contact"')[1].split("</picture>")[0])
        category = Category.objects.get(slug="soft-seating"); category.banner_image = self._img("k.png"); category.banner_mobile_image = self._img("km.png"); category.save()
        html = self.client.get("/categories/soft-seating/").content.decode()
        self.assertIn(f'<picture><source media="(max-width:767px)" srcset="{category.banner_mobile_image.url}"><img src="{category.banner_image.url}"', html)

    def test_product_page_has_no_mobile_pictures(self):
        html = self.client.get("/products/cove-social/").content.decode()
        self.assertNotIn("<picture", html)
        self.assertNotIn("data-hover-src-mobile", self.client.get("/collections/cove/").content.decode())
