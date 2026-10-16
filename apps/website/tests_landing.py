"""Tests for the two campaign landing pages.

What matters about these pages is as much what they do *not* have — site
chrome, and any link pointing at them — as what they render.
"""
import re
import time

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import Product
from apps.enquiries.models import Enquiry
from apps.pages.models import LandingText

LANDING_PATHS = [
    "/acoustic-wall-panels-for-offices/",
    "/acoustic-ceilings-for-offices/",
]


def enquiry_payload(**overrides):
    data = {
        "name": "Asha Mehta",
        "email": "asha@studio.example",
        "phone": "+91 98200 11223",
        "company": "Mehta Design Studio",
        "city": "Pune",
        "message": "Looking at panels for a 4,000 sq ft office fit-out in March.",
        # The form rejects anything submitted within two seconds of loading.
        "form_started": str(time.time() - 30),
        "website": "",
        "product_slug": "",
    }
    data.update(overrides)
    return data


class LandingPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_cofur", skip_images=True, verbosity=0)

    def setUp(self):
        # The enquiry rate limiter counts per IP in the cache, which outlives a
        # test's transaction. Without this, whoever ran first spends the quota.
        cache.clear()

    def test_both_pages_render_their_own_copy(self):
        wall = self.client.get(LANDING_PATHS[0])
        self.assertEqual(wall.status_code, 200)
        self.assertContains(wall, "Acoustic Wall Panels for Commercial Offices")
        self.assertContains(wall, "Enquire About Acoustic Wall Panels")
        self.assertContains(wall, "Grooved Wall Panels")

        ceiling = self.client.get(LANDING_PATHS[1])
        self.assertEqual(ceiling.status_code, 200)
        self.assertContains(ceiling, "Acoustic Ceilings for Commercial Offices")
        self.assertContains(ceiling, "Discuss Your Acoustic Ceiling Project")
        for design in ["Wave", "Petal", "Blade", "Planks", "Grid", "Waffle", "Hive"]:
            self.assertContains(ceiling, design)

    def test_pages_carry_the_site_theme_but_no_header_or_footer(self):
        for path in LANDING_PATHS:
            with self.subTest(path=path):
                body = self.client.get(path).content.decode()
                # The brand: the site's own stylesheet, so fonts, tokens and
                # the enquiry form look exactly like the rest of COFUR.
                self.assertIn("css/style.css", body)
                self.assertIn("css/landing.css", body)
                # No chrome.
                self.assertNotIn("site-header", body)
                self.assertNotIn("mega-menu", body)
                self.assertNotIn("site-footer", body)
                self.assertNotIn("All rights reserved", body)

    def test_nothing_on_the_website_links_to_them(self):
        reachable = ["website:home", "website:about", "website:contact", "website:projects", "website:catalogues"]
        for name in reachable:
            body = self.client.get(reverse(name)).content.decode()
            for path in LANDING_PATHS:
                with self.subTest(page=name, target=path):
                    self.assertNotIn(path, body)

    def test_the_form_is_the_real_cofur_enquiry_form(self):
        body = self.client.get(LANDING_PATHS[0]).content.decode()
        self.assertIn("csrfmiddlewaretoken", body)
        self.assertIn('name="collection" value="Acoustic Wall Panels (campaign page)"', body)
        self.assertIn('name="website"', body)  # honeypot
        self.assertIn('name="form_started"', body)
        for field in ["name", "email", "phone", "company", "city", "message"]:
            self.assertIn(f'name="{field}"', body)
        # The wall panels page offers only its three products, under product_slug.
        self.assertIn('name="product_slug"', body)
        for name in ["Grooved Wall Panels", "Printed Wall Panels", "Fluted Wall Panels"]:
            self.assertIn(f">{name}</option>", body)

    def test_a_submission_lands_in_the_enquiry_inbox_and_stays_on_the_page(self):
        response = self.client.post(LANDING_PATHS[1], enquiry_payload())
        self.assertRedirects(response, f"{LANDING_PATHS[1]}?sent=1#enquiry", fetch_redirect_response=False)

        enquiry = Enquiry.objects.get()
        self.assertEqual(enquiry.name, "Asha Mehta")
        self.assertEqual(enquiry.city, "Pune")
        # The campaign page the lead came from, visible in the dashboard.
        self.assertEqual(enquiry.collection_ref, "Acoustic Ceilings (campaign page)")

        # Following the redirect shows the success message, on the landing page.
        landed = self.client.get(f"{LANDING_PATHS[1]}?sent=1")
        self.assertContains(landed, "form-message show")

    def test_a_bad_submission_comes_back_on_the_landing_page_with_errors(self):
        response = self.client.post(LANDING_PATHS[0], enquiry_payload(email="not-an-email", message="no"))
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Enquire About Acoustic Wall Panels", status_code=400)
        self.assertContains(response, "field-error", status_code=400)
        self.assertFalse(Enquiry.objects.exists())

    def test_the_honeypot_still_rejects_bots(self):
        response = self.client.post(LANDING_PATHS[0], enquiry_payload(website="http://spam.example"))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Enquiry.objects.exists())

    def test_the_ceilings_form_offers_only_the_designs_on_the_page(self):
        body = self.client.get(LANDING_PATHS[1]).content.decode()
        dropdown = re.search(r'<select[^>]*name="product[^"]*"[^>]*>.*?</select>', body, re.S).group(0)
        self.assertEqual(
            re.findall(r"<option[^>]*>(.*?)</option>", dropdown),
            ["Select a product (optional)", "Wave", "Petal", "Blade", "Planks", "Grid", "Waffle", "Hive"],
        )
        # Nothing from the rest of the catalogue may appear here.
        for product in Product.objects.published():
            self.assertNotIn(product.name, dropdown)

    def test_the_chosen_ceiling_design_reaches_the_enquiry_inbox(self):
        response = self.client.post(LANDING_PATHS[1], enquiry_payload(product_slug="wave"))
        self.assertEqual(response.status_code, 302)
        enquiry = Enquiry.objects.get()
        self.assertEqual(enquiry.collection_ref, "Acoustic Ceilings (campaign page) · Wave")
        # The designs are not catalogue products, so none is linked.
        self.assertIsNone(enquiry.product)

    def test_every_ceiling_design_offers_a_link_to_its_product_page(self):
        response = self.client.get(LANDING_PATHS[1])
        body = response.content.decode()
        # Seven designs, each with a details link beside its enquire button.
        self.assertEqual(body.count("View product details"), 7)
        # Until the designs have product pages of their own, every card points
        # at the Acoustic Ceilings category page, which has to exist.
        self.assertEqual(body.count('href="/categories/acoustic-ceilings/"'), 14)  # photo + link per card
        self.assertEqual(self.client.get("/categories/acoustic-ceilings/").status_code, 200)

    def test_a_design_can_be_pointed_at_its_own_product_page(self):
        row = LandingText.objects.get(page="ceilings", key="design_1_url")
        row.value = "/products/grooved-wall-panels/"
        row.save()
        body = self.client.get(LANDING_PATHS[1]).content.decode()
        self.assertIn('href="/products/grooved-wall-panels/"', body)
        # Only the design that was changed moves; the other six stay put.
        self.assertEqual(body.count('href="/categories/acoustic-ceilings/"'), 12)
