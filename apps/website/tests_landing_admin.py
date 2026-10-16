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
