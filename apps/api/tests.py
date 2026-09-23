from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from apps.catalog.models import Product
from apps.enquiries.models import Enquiry


class APITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_cofur", skip_images=True, verbosity=0)

    def setUp(self):
        cache.clear()

    def get(self, url):
        return self.client.get(url, HTTP_ACCEPT="application/json")

    def test_products_list_and_filters(self):
        data = self.get("/api/products/").json()
        self.assertEqual(data["count"], Product.objects.published().count())
        slugs = {p["slug"] for p in self.get("/api/products/?collection=cove").json()["results"]}
        self.assertIn("cove-social", slugs)
        self.assertNotIn("grove-trio", slugs)
        featured = self.get("/api/products/?featured=1").json()["results"]
        self.assertEqual([p["slug"] for p in featured], ["grove-trio"])
        self.assertEqual(self.get("/api/products/?search=social").json()["count"], 1)

    def test_product_detail(self):
        data = self.get("/api/products/cove-social/").json()
        self.assertEqual(data["name"], "Cove Social")
        self.assertEqual(len(data["specifications"]), 4)
        self.assertEqual(len(data["colors"]), 3)
        self.assertEqual(data["dimensions"][0], {"label": "Width", "value": "160", "unit": "cm"})
        self.assertEqual(len(data["related_products"]), 4)
        self.assertEqual(data["seo"]["title"], "Cove Social — Cofur")
        for key in ("main_mobile_image", "hover_mobile_image", "finish_mobile_image"):
            self.assertNotIn(key, data)

    def test_draft_products_hidden(self):
        Product.objects.filter(slug="cove-solo").update(status="draft")
        self.assertEqual(self.get("/api/products/cove-solo/").status_code, 404)

    def test_collections_categories_team(self):
        self.assertEqual(self.get("/api/collections/").json()["count"], 4)
        detail = self.get("/api/collections/cove/").json()
        self.assertEqual(len(detail["products"]), 6)
        self.assertEqual(self.get("/api/collections/?category=soft-seating").json()["count"], 4)
        self.assertEqual(self.get("/api/categories/").json()["count"], 4)
        self.assertEqual(self.get("/api/team/").json()["count"], 4)

    def test_pages_and_settings(self):
        home = self.get("/api/pages/home/").json()
        self.assertEqual(home["hero_heading"], "Furniture for the way people actually work")
        self.assertEqual(len(home["statement_lines"]), 3)
        from apps.core.tests import make_image
        from apps.pages.models import HomeHeroSlide, HomePage

        HomeHeroSlide.objects.create(page=HomePage.load(), image=make_image("s.png"), alt_text="Slide")
        home = self.get("/api/pages/home/").json()
        self.assertIn("mobile_image", home["hero_slides"][0])
        self.assertIn("mobile_alt", home["hero_slides"][0])
        self.assertEqual(len(home["categories"]), 4)
        about = self.get("/api/pages/about/").json()
        self.assertEqual(len(about["team"]), 4)
        contact = self.get("/api/pages/contact/").json()
        self.assertEqual(contact["email"], "info@cofur.in")
        settings = self.get("/api/settings/").json()
        self.assertEqual(settings["site_name"], "COFUR")
        nav = self.get("/api/navigation/").json()
        self.assertIn("header", nav)
        self.assertEqual(nav["header"][0]["label"], "Collections")
        self.assertTrue(nav["header"][0]["children"])

    def test_create_enquiry(self):
        payload = {"name": "API User", "email": "api@example.com", "phone": "9876543210", "message": "Please quote 10 Cove Social units.", "product": "cove-social"}
        response = self.client.post("/api/enquiries/", payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        enquiry = Enquiry.objects.get()
        self.assertEqual(enquiry.product.slug, "cove-social")
        self.assertEqual(enquiry.source, "api")

    def test_create_enquiry_validation_and_honeypot(self):
        response = self.client.post("/api/enquiries/", {"name": "x", "email": "bad", "message": "hi", "website": "spam"}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())
        self.assertIn("website", response.json())
        self.assertEqual(Enquiry.objects.count(), 0)

    def test_enquiries_are_write_only(self):
        self.assertEqual(self.get("/api/enquiries/").status_code, 405)
