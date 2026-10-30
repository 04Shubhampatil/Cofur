"""Google's tags — verification and Tag Manager — come from the CMS.

Nothing about them is written into a template any more: Site settings holds the
site-wide pair, and a campaign landing page may name its own Tag Manager
container instead.
"""
import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.core.models import SiteSettings
from apps.dashboard.forms import clean_gtm_id, clean_verification_code
from apps.pages.models import LandingText

HOME = "/"
WALL = "/acoustic-wall-panels-for-offices/"
CEILINGS = "/acoustic-ceilings-for-offices/"

User = get_user_model()


def containers(body):
    return sorted(set(re.findall(r"GTM-[A-Z0-9]+", body)))


def verification(body):
    found = re.search(r'name="google-site-verification" content="([^"]*)"', body)
    return found.group(1) if found else None


class GoogleTagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_cofur", skip_images=True, verbosity=0)

    def page(self, path):
        return self.client.get(path).content.decode()

    def test_the_verification_tag_appears_once_the_code_is_saved(self):
        self.assertIsNone(verification(self.page(HOME)))

        site = SiteSettings.load()
        site.google_site_verification = "token-from-search-console"
        site.save()

        # Search Console checks the home page, but the tag is harmless anywhere
        # and campaign pages share the same head.
        for path in [HOME, WALL, CEILINGS]:
            with self.subTest(path=path):
                self.assertEqual(verification(self.page(path)), "token-from-search-console")

    def test_the_tag_manager_container_comes_from_site_settings(self):
        site = SiteSettings.load()
        site.gtm_container_id = "GTM-SITE999"
        site.save()
        for path in [HOME, WALL, CEILINGS]:
            with self.subTest(path=path):
                self.assertEqual(containers(self.page(path)), ["GTM-SITE999"])

    def test_emptying_the_container_removes_tag_manager_altogether(self):
        site = SiteSettings.load()
        site.gtm_container_id = ""
        site.save()
        for path in [HOME, WALL, CEILINGS]:
            with self.subTest(path=path):
                body = self.page(path)
                self.assertEqual(containers(body), [])
                self.assertNotIn("googletagmanager.com", body)

    def test_a_landing_page_can_use_its_own_container(self):
        site = SiteSettings.load()
        site.gtm_container_id = "GTM-SITE999"
        site.save()
        row = LandingText.objects.get(page="wall", key="gtm_id")
        row.value = "GTM-LAND777"
        row.save()

        # Only that campaign page moves; the site and the other page do not.
        self.assertEqual(containers(self.page(WALL)), ["GTM-LAND777"])
        self.assertEqual(containers(self.page(HOME)), ["GTM-SITE999"])
        self.assertEqual(containers(self.page(CEILINGS)), ["GTM-SITE999"])


class GoogleFieldCleaningTests(TestCase):
    def test_the_whole_meta_tag_can_be_pasted_for_verification(self):
        pasted = '<meta name="google-site-verification" content="XyZ-123_token" />'
        self.assertEqual(clean_verification_code(pasted), "XyZ-123_token")
        self.assertEqual(clean_verification_code("  XyZ-123_token  "), "XyZ-123_token")
        self.assertEqual(clean_verification_code(""), "")

    def test_rubbish_in_the_verification_box_is_refused(self):
        with self.assertRaises(ValidationError):
            clean_verification_code("this is not a code")

    def test_a_container_id_is_tidied_up_or_refused(self):
        self.assertEqual(clean_gtm_id("gtm-abc1234"), "GTM-ABC1234")
        self.assertEqual(clean_gtm_id(" GTM-ABC1234 "), "GTM-ABC1234")
        self.assertEqual(clean_gtm_id(""), "")
        for bad in ["UA-12345", "G-ABCD1234", "rubbish", "GTM-"]:
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                clean_gtm_id(bad)


class GoogleAdminScreenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_cofur", skip_images=True, verbosity=0)
        cls.admin = User.objects.create_superuser("google-editor", "g@cofur.test", "pw-for-tests-only")

    def setUp(self):
        self.client.force_login(self.admin)

    def test_site_settings_offers_the_google_fields(self):
        response = self.client.get(reverse("dashboard:site_settings"))
        self.assertContains(response, "Google site verification")
        self.assertContains(response, "Google Tag Manager ID")

    def test_the_landing_editors_offer_their_own_container(self):
        for url_name in ["dashboard:landing_wall", "dashboard:landing_ceilings"]:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertContains(response, "Tracking")
                self.assertContains(response, "Google Tag Manager ID")

    def test_the_home_about_and_contact_editors_now_have_an_seo_tab(self):
        for url_name in ["dashboard:page_home", "dashboard:page_about", "dashboard:page_contact"]:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                for label in ["SEO title", "Meta description", "Canonical url", "Robots"]:
                    self.assertContains(response, label)

    def test_a_saved_home_page_seo_title_reaches_the_page(self):
        from apps.pages.models import HomePage

        page = HomePage.load()
        page.seo_title = "COFUR — office furniture that works"
        page.save()
        self.client.logout()
        self.assertContains(self.client.get(HOME), "<title>COFUR — office furniture that works</title>")
