"""The admin editors for the two landing pages."""
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.pages.models import LandingText

User = get_user_model()

EDITS = {
    "wall": ("hero_title", "Edited wall heading for the test", "/acoustic-wall-panels-for-offices/", "Acoustic Wall Panels for Commercial Offices"),
    "ceilings": ("hero_title", "Edited ceilings heading for the test", "/acoustic-ceilings-for-offices/", "Acoustic Ceilings for Commercial Offices"),
}


class LandingAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_cofur", skip_images=True, verbosity=0)
        cls.admin = User.objects.create_superuser("landing-editor", "editor@cofur.test", "pw-for-tests-only")

    def setUp(self):
        self.client.force_login(self.admin)

    def test_sidebar_links_to_the_landing_pages_list(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertContains(response, "Landing pages")
        self.assertContains(response, reverse("dashboard:landing_index"))

    def test_list_offers_both_pages(self):
        response = self.client.get(reverse("dashboard:landing_index"))
        self.assertContains(response, reverse("dashboard:landing_wall"))
        self.assertContains(response, reverse("dashboard:landing_ceilings"))

    def test_each_editor_lists_every_item_of_its_page(self):
        for page, url_name in [("wall", "dashboard:landing_wall"), ("ceilings", "dashboard:landing_ceilings")]:
            with self.subTest(page=page):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
                total = LandingText.objects.filter(page=page).count()
                self.assertEqual(response.context["formset"].total_form_count(), total)

    def test_saving_a_change_shows_on_each_live_page(self):
        for page, url_name in [("wall", "dashboard:landing_wall"), ("ceilings", "dashboard:landing_ceilings")]:
            with self.subTest(page=page):
                key, new_text, live_path, old_text = EDITS[page]
                rows = list(LandingText.objects.filter(page=page))
                data = {
                    "landing-TOTAL_FORMS": str(len(rows)),
                    "landing-INITIAL_FORMS": str(len(rows)),
                    "landing-MIN_NUM_FORMS": "0",
                    "landing-MAX_NUM_FORMS": "1000",
                }
                for i, row in enumerate(rows):
                    data[f"landing-{i}-id"] = str(row.pk)
                    data[f"landing-{i}-value"] = new_text if row.key == key else row.value
                response = self.client.post(reverse(url_name), data)
                self.assertRedirects(response, reverse("dashboard:landing_index"))
                self.assertEqual(LandingText.objects.get(page=page, key=key).value, new_text)

                live = self.client.get(live_path)
                self.assertContains(live, new_text)
                self.assertNotContains(live, f"<h1>{old_text}</h1>")

    def post_editor(self, url_name, page, changes):
        """Save one page's editor with `changes` (key -> new value) applied."""
        rows = list(LandingText.objects.filter(page=page))
        data = {
            "landing-TOTAL_FORMS": str(len(rows)),
            "landing-INITIAL_FORMS": str(len(rows)),
            "landing-MIN_NUM_FORMS": "0",
            "landing-MAX_NUM_FORMS": "1000",
        }
        for i, row in enumerate(rows):
            data[f"landing-{i}-id"] = str(row.pk)
            data[f"landing-{i}-value"] = changes.get(row.key, row.value)
        return self.client.post(reverse(url_name), data)

    def test_each_editor_has_an_seo_section_with_every_meta_field(self):
        for url_name in ["dashboard:landing_wall", "dashboard:landing_ceilings"]:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertContains(response, "SEO")
                # The same field names the product and category editors use.
                for label in [
                    "SEO title",
                    "Meta description",
                    "Meta keywords",
                    "Open Graph title",
                    "Open Graph description",
                    "Open Graph image",
                    "Canonical url",
                    "Robots",
                ]:
                    self.assertContains(response, label)
                # Indexing is a dropdown, not free text anyone can mistype.
                self.assertContains(response, "Use the site setting")
                self.assertContains(response, "noindex, follow")

    def test_the_seo_section_changes_what_search_engines_are_told(self):
        response = self.post_editor("dashboard:landing_wall", "wall", {
            "seo_title": "Office Acoustic Wall Panels | COFUR",
            "seo_keywords": "acoustic wall panels, office interiors",
            "seo_og_title": "See COFUR wall panels",
            "seo_robots": "noindex, follow",
            "seo_canonical": "https://cofur.in/acoustic-wall-panels-for-offices/",
        })
        self.assertRedirects(response, reverse("dashboard:landing_index"))

        live = self.client.get("/acoustic-wall-panels-for-offices/")
        self.assertContains(live, "<title>Office Acoustic Wall Panels | COFUR</title>")
        self.assertContains(live, "acoustic wall panels, office interiors")
        self.assertContains(live, 'property="og:title" content="See COFUR wall panels"')
        self.assertContains(live, 'name="robots" content="noindex, follow"')
        self.assertContains(live, 'href="https://cofur.in/acoustic-wall-panels-for-offices/"')

    def test_an_empty_seo_section_falls_back_instead_of_emptying_the_page(self):
        blanks = dict.fromkeys(
            ["seo_title", "seo_description", "seo_keywords", "seo_og_title",
             "seo_og_description", "seo_robots", "seo_canonical"], "")
        self.post_editor("dashboard:landing_ceilings", "ceilings", blanks)

        live = self.client.get("/acoustic-ceilings-for-offices/")
        self.assertContains(live, "<title>Acoustic Ceilings for Commercial Offices | COFUR</title>")
        self.assertContains(live, 'name="robots" content="index, follow"')
        self.assertContains(live, 'rel="canonical" href="http://testserver/acoustic-ceilings-for-offices/"')

    def test_a_canonical_address_that_is_not_an_address_is_refused(self):
        response = self.post_editor("dashboard:landing_wall", "wall", {"seo_canonical": "cofur.in/panels"})
        self.assertEqual(response.status_code, 200)  # back on the form, not saved
        self.assertContains(response, "Enter a full web address")
        self.assertEqual(LandingText.objects.get(page="wall", key="seo_canonical").value, "")
