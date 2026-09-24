import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import Category, Collection, Product, ProductImage
from apps.core.models import NavigationItem, NavigationMenu, SiteSettings
from apps.core.roles import ensure_roles
from apps.core.tests import make_image
from apps.enquiries.models import Enquiry
from apps.pages.models import AboutPage, ContactPage, HomePage
from apps.team.models import TeamMember

User = get_user_model()


def mgmt(prefix, total=0, initial=0):
    return {f"{prefix}-TOTAL_FORMS": total, f"{prefix}-INITIAL_FORMS": initial, f"{prefix}-MIN_NUM_FORMS": 0, f"{prefix}-MAX_NUM_FORMS": 1000}


def product_payload(**extra):
    data = {
        "name": "New Product", "status": "published", "order": 1, "robots": "index, follow", "dimension_unit": "cm", "weight_unit": "kg",
        "cta_text": "Enquire now", "enquiry_title": "Enquire", "enquiry_text": "Tell us", "fabric_intro": "Choose",
        "details_heading": "Product details", "specs_heading": "Specifications", "gallery_heading": "Gallery", "related_heading": "Related",
        "fabric_heading": "Fabric", "features_heading": "Features", "dimensions_heading": "Dimensions", "care_heading": "Care",
    }
    for prefix in ("specs", "features", "care", "colors", "detail_images", "dimension_images", "gallery_images"):
        data.update(mgmt(prefix))
    data.update(extra)
    return data


class DashboardTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.groups = ensure_roles()
        cls.superuser = User.objects.create_superuser("admin", "admin@example.com", "Admin-Pass-123!")
        cls.editor = User.objects.create_user("editor", password="Editor-Pass-123!", is_staff=True)
        cls.editor.groups.add(cls.groups["Editor"])
        cls.staffer = User.objects.create_user("staffer", password="Staff-Pass-123!", is_staff=True)
        cls.staffer.groups.add(cls.groups["Staff"])
        cls.customer = User.objects.create_user("customer", password="Cust-Pass-123!", is_staff=False)
        cls.category = Category.objects.create(name="Soft Seating")
        cls.collection = Collection.objects.create(name="Cove", category=cls.category)
        cls.product = Product.objects.create(name="Cove Social", collection=cls.collection, status="published")


class AuthTests(DashboardTestCase):
    def test_login_required_redirects(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("dashboard:login"), response["Location"])

    def test_login_page_renders(self):
        response = self.client.get(reverse("dashboard:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")

    def test_login_success_and_logout(self):
        response = self.client.post(reverse("dashboard:login"), {"username": "admin", "password": "Admin-Pass-123!"})
        self.assertRedirects(response, reverse("dashboard:index"))
        self.assertEqual(self.client.get(reverse("dashboard:index")).status_code, 200)
        response = self.client.post(reverse("dashboard:logout"))
        self.assertRedirects(response, reverse("dashboard:login"))

    def test_non_staff_cannot_login_to_dashboard(self):
        response = self.client.post(reverse("dashboard:login"), {"username": "customer", "password": "Cust-Pass-123!"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "does not have dashboard access")

    def test_wrong_password(self):
        response = self.client.post(reverse("dashboard:login"), {"username": "admin", "password": "nope"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username and password")

    def test_password_change(self):
        self.client.force_login(self.editor)
        response = self.client.post(reverse("dashboard:password_change"), {"old_password": "Editor-Pass-123!", "new_password1": "Another-Pass-456!", "new_password2": "Another-Pass-456!"})
        self.assertRedirects(response, reverse("dashboard:index"))
        self.editor.refresh_from_db()
        self.assertTrue(self.editor.check_password("Another-Pass-456!"))


class PermissionTests(DashboardTestCase):
    def test_staff_role_read_only_catalog(self):
        self.client.force_login(self.staffer)
        self.assertEqual(self.client.get(reverse("dashboard:product_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:product_create")).status_code, 403)
        self.assertEqual(self.client.post(reverse("dashboard:product_delete", args=[self.product.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard:enquiry_list")).status_code, 200)

    def test_editor_can_add_products(self):
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(reverse("dashboard:product_create")).status_code, 200)

    def test_non_staff_user_gets_403(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(reverse("dashboard:index")).status_code, 403)

    def test_sidebar_filtered_by_permissions(self):
        self.client.force_login(self.staffer)
        response = self.client.get(reverse("dashboard:index"))
        self.assertNotContains(response, reverse("dashboard:product_create"))
        self.assertContains(response, reverse("dashboard:enquiry_list"))


class ProductCrudTests(DashboardTestCase):
    def setUp(self):
        self.client.force_login(self.superuser)

    def test_list_search_filter_pagination(self):
        for i in range(25):
            Product.objects.create(name=f"Bulk {i}", collection=self.collection, status="draft")
        response = self.client.get(reverse("dashboard:product_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["rows"]), 24)
        self.assertTrue(response.context["is_paginated"])
        response = self.client.get(reverse("dashboard:product_list") + "?q=Cove")
        self.assertEqual(len(response.context["rows"]), 1)
        response = self.client.get(reverse("dashboard:product_list") + "?status=draft&per_page=10")
        self.assertEqual(len(response.context["rows"]), 10)
        response = self.client.get(reverse("dashboard:product_list") + "?collection=" + str(self.collection.pk) + "&featured=0")
        self.assertEqual(response.context["total_count"], 26)
        response = self.client.get(reverse("dashboard:product_list") + "?q=zzz")
        self.assertContains(response, "No results")

    def test_create_with_children_and_image(self):
        data = product_payload(collection=self.collection.pk, main_image=make_image("main.png", size=(800, 600)), related_products=[self.product.pk])
        data.update(mgmt("specs", 1)); data.update({"specs-0-label": "Frame", "specs-0-value": "Steel", "specs-0-order": 0})
        data.update(mgmt("features", 1)); data.update({"features-0-text": "Great", "features-0-order": 0})
        data.update(mgmt("care", 1)); data.update({"care-0-text": "Wipe clean", "care-0-order": 0})
        data.update(mgmt("colors", 1)); data.update({"colors-0-name": "Red", "colors-0-hex_code": "#ff0000", "colors-0-order": 0})
        response = self.client.post(reverse("dashboard:product_create"), data)
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context["form"].errors)
        product = Product.objects.get(slug="new-product")
        self.assertEqual(product.category, self.category)
        self.assertTrue(product.thumbnail)
        self.assertEqual(product.specifications.count(), 1)
        self.assertEqual(product.feature_items.filter(kind="feature").count(), 1)
        self.assertEqual(product.feature_items.filter(kind="care").count(), 1)
        self.assertEqual(product.colors.count(), 1)
        self.assertEqual(list(product.related_products.all()), [self.product])

    def test_create_invalid_shows_errors(self):
        response = self.client.post(reverse("dashboard:product_create"), product_payload(name=""))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_invalid_image_rejected(self):
        data = product_payload(main_image=SimpleUploadedFile("fake.png", b"not an image"))
        response = self.client.post(reverse("dashboard:product_create"), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("main_image", response.context["form"].errors)

    def test_update(self):
        data = product_payload(name="Renamed", collection=self.collection.pk, hover_image=make_image("hover.png"))
        response = self.client.post(reverse("dashboard:product_update", args=[self.product.pk]), data)
        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Renamed")
        self.assertTrue(self.product.hover_image)

    def test_save_and_continue(self):
        data = product_payload(name="Cove Social", collection=self.collection.pk, _continue="1")
        response = self.client.post(reverse("dashboard:product_update", args=[self.product.pk]), data)
        self.assertRedirects(response, reverse("dashboard:product_update", args=[self.product.pk]))

    def test_delete(self):
        response = self.client.post(reverse("dashboard:product_delete", args=[self.product.pk]))
        self.assertRedirects(response, reverse("dashboard:product_list"))
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_duplicate_toggle_publish_feature(self):
        response = self.client.post(reverse("dashboard:product_duplicate", args=[self.product.pk]))
        clone = Product.objects.get(name="Cove Social (copy)")
        self.assertRedirects(response, reverse("dashboard:product_update", args=[clone.pk]))
        self.client.post(reverse("dashboard:product_toggle_publish", args=[self.product.pk]))
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, "draft")
        response = self.client.post(reverse("dashboard:product_toggle_featured", args=[self.product.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTrue(response.json()["value"])
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_featured)
        self.client.post(reverse("dashboard:product_toggle_publish", args=[self.product.pk]))  # back to published
        home = self.client.get("/").content.decode()
        self.assertIn('id="featured-products"', home)
        self.assertIn("Cove Social", home.split('id="featured-products"')[1])
        self.client.post(reverse("dashboard:product_toggle_featured", args=[self.product.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertNotIn('id="featured-products"', self.client.get("/").content.decode())

    def test_reorder(self):
        other = Product.objects.create(name="Other", collection=self.collection)
        response = self.client.post(reverse("dashboard:product_reorder"), json.dumps({"order": [other.pk, self.product.pk]}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([p.pk for p in Product.objects.order_by("order", "id")], [other.pk, self.product.pk])
        self.assertEqual(self.client.post(reverse("dashboard:product_reorder"), "garbage", content_type="application/json").status_code, 400)

    def test_gallery_upload_reorder_delete(self):
        url = reverse("dashboard:product_gallery_upload", args=[self.product.pk])
        response = self.client.post(url, {"kind": "gallery", "images": [make_image("a.png"), make_image("b.png")]}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        created = response.json()["created"]
        self.assertEqual(len(created), 2)
        self.assertEqual(ProductImage.objects.filter(product=self.product, kind="gallery").count(), 2)
        response = self.client.post(url, {"kind": "gallery", "images": [SimpleUploadedFile("bad.png", b"nope")]}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTrue(response.json()["errors"])
        ids = [c["id"] for c in created]
        self.client.post(reverse("dashboard:product_image_reorder"), json.dumps({"order": list(reversed(ids))}), content_type="application/json")
        self.assertEqual([i.pk for i in self.product.gallery_images()], list(reversed(ids)))
        response = self.client.post(reverse("dashboard:product_image_delete", args=[ids[0]]), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTrue(response.json()["ok"])
        self.assertEqual(self.product.images.count(), 1)


class CollectionCategoryCrudTests(DashboardTestCase):
    def setUp(self):
        self.client.force_login(self.superuser)

    def test_collection_crud(self):
        response = self.client.post(reverse("dashboard:collection_create"), {"name": "Pebble", "category": self.category.pk, "order": 2, "is_active": "on", "robots": "index, follow", "image": make_image("c.png")})
        self.assertEqual(response.status_code, 302)
        pebble = Collection.objects.get(slug="pebble")
        self.assertTrue(pebble.image)
        response = self.client.post(reverse("dashboard:collection_update", args=[pebble.pk]), {"name": "Pebble", "slug": "pebble", "category": self.category.pk, "tagline": "Organic", "order": 2, "robots": "index, follow", "image-clear": "on"})
        self.assertEqual(response.status_code, 302)
        pebble.refresh_from_db()
        self.assertEqual(pebble.tagline, "Organic")
        self.assertFalse(pebble.image)
        self.assertFalse(pebble.is_active)
        self.assertEqual(self.client.get(reverse("dashboard:collection_list") + "?q=peb").context["total_count"], 1)
        self.assertEqual(self.client.post(reverse("dashboard:collection_delete", args=[pebble.pk])).status_code, 302)
        self.assertFalse(Collection.objects.filter(pk=pebble.pk).exists())

    def test_collection_banner_fields_editable(self):
        response = self.client.get(reverse("dashboard:collection_update", args=[self.collection.pk]))
        self.assertEqual(response.status_code, 200)
        for label in ["Banner", "Banner title", "Banner image (desktop)", "Mobile banner image (optional, shown below 768px)", "Banner alt text", "Published"]:
            self.assertContains(response, label)
        self.assertContains(response, 'href="/collections/cove/"')  # preview link
        response = self.client.post(reverse("dashboard:collection_update", args=[self.collection.pk]), {
            "name": "Cove", "slug": "cove", "category": self.category.pk, "order": 0, "is_active": "on", "robots": "index, follow",
            "heading": "Cove\r\ncollection", "banner_alt": "Cove lounge seating", "seo_title": "Cove Collection — Cofur",
            "meta_description": "Explore the Cove collection.", "banner_image": make_image("banner.png"), "banner_mobile_image": make_image("banner-m.png"),
        })
        self.assertEqual(response.status_code, 302)
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.heading, "Cove\ncollection")
        self.assertEqual(self.collection.banner_alt, "Cove lounge seating")
        self.assertTrue(self.collection.banner_image)
        self.assertTrue(self.collection.banner_mobile_image)
        page = self.client.get("/collections/cove/")
        self.assertContains(page, "<h1>Cove<br>collection</h1>")
        self.assertContains(page, "<title>Cove Collection — Cofur</title>")
        self.assertContains(page, 'media="(max-width:767px)"')
        self.assertContains(page, "<em>Cove</em> Social")

    def test_category_crud(self):
        response = self.client.post(reverse("dashboard:category_create"), {"name": "Phone Booth", "order": 3, "is_active": "on", "show_on_home": "on", "robots": "index, follow", "card_link_text": "View items", "link_override": "/contact/?collection=phone-booth"})
        self.assertEqual(response.status_code, 302)
        booth = Category.objects.get(slug="phone-booth")
        self.assertEqual(booth.link, "/contact/?collection=phone-booth")
        response = self.client.post(reverse("dashboard:category_update", args=[booth.pk]), {"name": "Phone Booths", "slug": "phone-booth", "order": 3, "is_active": "on", "robots": "index, follow", "card_link_text": "View"})
        self.assertEqual(response.status_code, 302)
        booth.refresh_from_db()
        self.assertEqual(booth.name, "Phone Booths")
        self.assertEqual(self.client.post(reverse("dashboard:category_delete", args=[booth.pk])).status_code, 302)
        self.assertFalse(Category.objects.filter(pk=booth.pk).exists())

    def test_category_reorder(self):
        other = Category.objects.create(name="Acoustics")
        self.client.post(reverse("dashboard:category_reorder"), json.dumps({"order": [other.pk, self.category.pk]}), content_type="application/json")
        self.assertEqual(list(Category.objects.values_list("pk", flat=True)), [other.pk, self.category.pk])


class TeamCrudTests(DashboardTestCase):
    def setUp(self):
        self.client.force_login(self.editor)

    def test_team_crud(self):
        response = self.client.post(reverse("dashboard:team_create"), {"name": "Vedangi P", "designation": "BD Executive", "biography": "Bio", "order": 1, "is_active": "on", "image": make_image("v.jpg", fmt="JPEG")})
        self.assertEqual(response.status_code, 302)
        member = TeamMember.objects.get(name="Vedangi P")
        self.assertTrue(member.thumbnail)
        response = self.client.post(reverse("dashboard:team_update", args=[member.pk]), {"name": "Vedangi P", "designation": "Head of BD", "order": 1, "is_active": "on"})
        member.refresh_from_db()
        self.assertEqual(member.designation, "Head of BD")
        self.client.post(reverse("dashboard:team_toggle_active", args=[member.pk]))
        member.refresh_from_db()
        self.assertFalse(member.is_active)
        self.assertEqual(self.client.post(reverse("dashboard:team_delete", args=[member.pk])).status_code, 302)
        self.assertFalse(TeamMember.objects.filter(pk=member.pk).exists())


class EnquiryManagementTests(DashboardTestCase):
    def setUp(self):
        self.client.force_login(self.staffer)
        self.enquiry = Enquiry.objects.create(name="Lead", email="lead@example.com", message="Need chairs", product=self.product)

    def test_list_stats_and_filters(self):
        response = self.client.get(reverse("dashboard:enquiry_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["enquiry_stats"]["new"], 1)
        self.assertEqual(self.client.get(reverse("dashboard:enquiry_list") + "?status=closed").context["total_count"], 0)
        self.assertEqual(self.client.get(reverse("dashboard:enquiry_list") + "?q=chairs").context["total_count"], 1)

    def test_detail_update_status_notes(self):
        response = self.client.get(reverse("dashboard:enquiry_detail", args=[self.enquiry.pk]))
        self.assertContains(response, "lead@example.com")
        response = self.client.post(reverse("dashboard:enquiry_detail", args=[self.enquiry.pk]), {"status": "in_progress", "admin_notes": "Called"})
        self.assertEqual(response.status_code, 302)
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.status, "in_progress")
        self.assertEqual(self.enquiry.admin_notes, "Called")
        self.client.post(reverse("dashboard:enquiry_status", args=[self.enquiry.pk]), {"status": "converted"})
        self.enquiry.refresh_from_db()
        self.assertEqual(self.enquiry.status, "converted")

    def test_staff_cannot_delete_but_admin_can(self):
        self.assertEqual(self.client.post(reverse("dashboard:enquiry_delete", args=[self.enquiry.pk])).status_code, 403)
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.post(reverse("dashboard:enquiry_delete", args=[self.enquiry.pk])).status_code, 302)
        self.assertFalse(Enquiry.objects.filter(pk=self.enquiry.pk).exists())


class PagesSettingsTests(DashboardTestCase):
    def setUp(self):
        self.client.force_login(self.editor)

    def test_home_page_edit_with_formsets(self):
        data = {
            "hero_heading": "Edited hero", "intro_heading": "Intro", "intro_heading_highlight": "x", "robots": "index, follow",
            "hero_visible": "on", "intro_visible": "on", "category_section_visible": "on", "statement_visible": "on", "featured_visible": "on", "why_visible": "on",
            "featured_heading": "Featured", "featured_cta_text": "View", "why_heading": "Why", "statement_heading": "s", "statement_description": "d",
            "statement_cta_text": "About us", "statement_cta_url": "/about/",
        }
        for prefix in ("slides", "lines"):
            data.update(mgmt(prefix))
        data.update(mgmt("differentiators", 1)); data.update({"differentiators-0-heading": "Design with purpose", "differentiators-0-order": 0, "differentiators-0-is_active": "on"})
        response = self.client.post(reverse("dashboard:page_home"), data)
        self.assertRedirects(response, reverse("dashboard:page_home"))
        page = HomePage.load()
        self.assertEqual(page.hero_heading, "Edited hero")
        self.assertEqual(page.differentiators.count(), 1)
        self.assertContains(self.client.get("/"), "Edited hero")

    def test_about_and_contact_pages(self):
        response = self.client.post(reverse("dashboard:page_about"), {"hero_heading": "About us", "intro_text": "Hello", "what_we_make_heading": "Make", "how_we_work_heading": "Work", "philosophy_heading": "Phil", "mission_heading": "Mission", "team_heading": "Team", "find_us_heading": "Find", "sustainability_heading": "Sus", "recycled_heading": "Rec", "tree_heading": "Tree", "robots": "index, follow", "team_visible": "on", "find_us_visible": "on", "india_visible": "on"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(AboutPage.load().intro_text, "Hello")
        response = self.client.post(reverse("dashboard:page_contact"), {"page_title": "Contact", "heading": "Talk", "visit_heading": "Visit", "mail_heading": "Mail", "hours_heading": "Hours", "form_heading": "Form", "form_button_text": "Send", "success_message": "Thanks!", "email": "hello@cofur.in", "robots": "index, follow"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ContactPage.load().success_message, "Thanks!")
        self.assertContains(self.client.get("/contact/"), "hello@cofur.in")

    def test_site_and_footer_settings(self):
        response = self.client.post(reverse("dashboard:site_settings"), {"site_name": "COFUR", "tagline": "Change the way you work", "contact_email": "info@cofur.in", "whatsapp_number": "919320461618", "whatsapp_message": "Hi", "address": "Thane", "instagram_url": "https://instagram.com/cofur"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SiteSettings.load().whatsapp_number, "919320461618")
        self.assertContains(self.client.get("/"), "https://instagram.com/cofur")
        response = self.client.post(reverse("dashboard:footer_settings"), {"copyright_text": "(c) {year} COFUR", "footer_title": "Title", "footer_primary_cta_text": "Contact", "footer_primary_cta_url": "/contact/", "footer_secondary_cta_text": "", "address": "Thane", "contact_email": "info@cofur.in"})
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get("/"), "COFUR")


class DashboardIndexTests(DashboardTestCase):
    def test_stats_and_recent(self):
        self.client.force_login(self.superuser)
        Enquiry.objects.create(name="A", email="a@example.com", message="hi there")
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, 200)
        labels = {s["label"]: s["value"] for s in response.context["stats"]}
        self.assertEqual(labels["Total products"], 1)
        self.assertEqual(labels["Total enquiries"], 1)
        self.assertEqual(response.context["enquiry_stats"]["new"], 1)
        self.assertContains(response, "Add product")
        self.assertContains(response, "Edit home page")


class QuickCatalogTests(DashboardTestCase):
    def setUp(self):
        self.client.force_login(self.superuser)

    def test_category_inline_add_and_toggle(self):
        response = self.client.get(reverse("dashboard:category_list"))
        self.assertContains(response, "Add Category")
        response = self.client.post(reverse("dashboard:category_list"), {"_quick_add": "1", "name": "Acoustic Lights", "thumbnail_image": make_image("cat.png")})
        self.assertRedirects(response, reverse("dashboard:category_list"))
        cat = Category.objects.get(slug="acoustic-lights")
        self.assertTrue(cat.thumbnail_image)
        response = self.client.post(reverse("dashboard:category_toggle_active", args=[cat.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertFalse(response.json()["value"])
        cat.refresh_from_db()
        self.assertFalse(cat.is_active)
        response = self.client.post(reverse("dashboard:category_list"), {"_quick_add": "1", "name": ""})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")

    def test_sub_category_inline_add_requires_category(self):
        response = self.client.get(reverse("dashboard:collection_list"))
        self.assertContains(response, "Add Sub-Category")
        self.assertContains(response, "Select category")
        response = self.client.post(reverse("dashboard:collection_list"), {"_quick_add": "1", "name": "Pebble"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Collection.objects.filter(slug="pebble").exists())
        response = self.client.post(reverse("dashboard:collection_list"), {"_quick_add": "1", "name": "Pebble", "category": self.category.pk, "image": make_image("p.png")})
        self.assertRedirects(response, reverse("dashboard:collection_list"))
        pebble = Collection.objects.get(slug="pebble")
        self.assertEqual(pebble.category, self.category)
        response = self.client.post(reverse("dashboard:collection_toggle_active", args=[pebble.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertFalse(response.json()["value"])

    def test_sub_category_filter_by_category(self):
        other = Category.objects.create(name="Workstations")
        Collection.objects.create(name="Desk Pods", category=other)
        response = self.client.get(reverse("dashboard:collection_list") + f"?category={other.pk}")
        names = [row["obj"].name for row in response.context["rows"]]
        self.assertEqual(names, ["Desk Pods"])
        self.assertContains(response, "---All Category---")
        response = self.client.get(reverse("dashboard:collection_list") + f"?category={self.category.pk}")
        self.assertEqual([row["obj"].name for row in response.context["rows"]], ["Cove"])
        self.assertEqual(self.client.get(reverse("dashboard:collection_list")).context["total_count"], 2)

    def test_staff_cannot_inline_add(self):
        self.client.force_login(self.staffer)
        self.assertEqual(self.client.get(reverse("dashboard:category_list")).status_code, 200)
        self.assertEqual(self.client.post(reverse("dashboard:category_list"), {"_quick_add": "1", "name": "X"}).status_code, 403)

    def test_product_grid_and_bulk_actions(self):
        other = Product.objects.create(name="Other", collection=self.collection, status="draft")
        response = self.client.get(reverse("dashboard:product_list"))
        self.assertContains(response, 'class="product-grid"')
        self.assertContains(response, "Select All")
        response = self.client.post(reverse("dashboard:product_bulk"), {"action": "publish", "ids": [other.pk, self.product.pk]})
        self.assertEqual(response.status_code, 302)
        other.refresh_from_db()
        self.assertEqual(other.status, "published")
        self.client.post(reverse("dashboard:product_bulk"), {"action": "feature", "ids": [other.pk]})
        other.refresh_from_db()
        self.assertTrue(other.is_featured)
        self.client.post(reverse("dashboard:product_bulk"), {"action": "delete", "ids": [other.pk]})
        self.assertFalse(Product.objects.filter(pk=other.pk).exists())
        self.client.force_login(self.editor)
        self.assertEqual(self.client.post(reverse("dashboard:product_bulk"), {"action": "unpublish", "ids": [self.product.pk]}).status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, "draft")


class MosaicVideoAdminTests(DashboardTestCase):
    def setUp(self):
        self.client.force_login(self.superuser)

    def _row(self, **extra):
        data = product_payload(name="Cove Social", collection=self.collection.pk)
        data.update(mgmt("detail_images", 1))
        data.update({"detail_images-0-order": 0, "detail_images-0-alt_text": "Video"})
        data.update({f"detail_images-0-{k}": v for k, v in extra.items()})
        return data

    def test_video_link_saved_on_mosaic_row(self):
        response = self.client.post(reverse("dashboard:product_update", args=[self.product.pk]), self._row(video_url="https://youtu.be/abc123XYZ"))
        self.assertEqual(response.status_code, 302)
        row = self.product.images.get()
        self.assertEqual(row.embed_url, "https://www.youtube-nocookie.com/embed/abc123XYZ")
        self.assertFalse(row.image)

    def test_video_file_saved_and_validated(self):
        response = self.client.post(reverse("dashboard:product_update", args=[self.product.pk]), self._row(video_file=SimpleUploadedFile("clip.mp4", b"\x00\x00\x00\x18ftypmp42", content_type="video/mp4")))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.product.images.get().video_file)
        response = self.client.post(reverse("dashboard:product_update", args=[self.product.pk]), self._row(video_file=SimpleUploadedFile("clip.exe", b"MZ", content_type="application/octet-stream")))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload an MP4, WebM, M4V or MOV file.")

    def test_video_only_allowed_in_mosaic_and_row_needs_media(self):
        # gallery rows have no video fields at all
        html = self.client.get(reverse("dashboard:product_update", args=[self.product.pk])).content.decode()
        self.assertNotIn("gallery_images-__prefix__-video_file", html)
        response = self.client.post(reverse("dashboard:product_update", args=[self.product.pk]), self._row())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add an image, or a video for a mosaic tile.")
        response = self.client.post(reverse("dashboard:product_update", args=[self.product.pk]), self._row(video_url="https://example.com/x"))
        self.assertContains(response, "Enter a YouTube or Vimeo page link")


class BannerMobileAdminTests(DashboardTestCase):
    def setUp(self):
        self.client.force_login(self.superuser)

    def test_fields_shown_under_desktop_banner_only(self):
        response = self.client.get(reverse("dashboard:collection_update", args=[self.collection.pk]))
        html = response.content.decode()
        self.assertContains(response, "Mobile banner image (optional, shown below 768px)")
        self.assertContains(response, "minimum 800px wide")
        self.assertLess(html.index('name="banner_image"'), html.index('name="banner_mobile_image"'))
        self.assertLess(html.index('name="banner_mobile_image"'), html.index('name="banner_mobile_alt"'))
        product_html = self.client.get(reverse("dashboard:product_update", args=[self.product.pk])).content.decode()
        self.assertNotIn("mobile_image", product_html)
        self.assertNotIn("Mobile banner image", product_html)

    def test_save_and_remove_collection_mobile_banner(self):
        base = {"name": "Cove", "slug": "cove", "category": self.category.pk, "order": 1, "is_active": "on", "robots": "index, follow"}
        data = dict(base, banner_image=make_image("d.png", size=(1600, 900)), banner_mobile_image=make_image("m.png", size=(3000, 4000)), banner_mobile_alt="Mobile crop")
        response = self.client.post(reverse("dashboard:collection_update", args=[self.collection.pk]), data)
        self.assertEqual(response.status_code, 302)
        self.collection.refresh_from_db()
        self.assertTrue(self.collection.banner_mobile_image)
        self.assertEqual(self.collection.banner_mobile_alt, "Mobile crop")
        from apps.core.images import image_dimensions

        self.assertLessEqual(max(image_dimensions(self.collection.banner_mobile_image)), 2400)
        data = dict(base)
        data["banner_mobile_image-clear"] = "on"
        response = self.client.post(reverse("dashboard:collection_update", args=[self.collection.pk]), data)
        self.assertEqual(response.status_code, 302)
        self.collection.refresh_from_db()
        self.assertFalse(self.collection.banner_mobile_image)
        self.assertTrue(self.collection.banner_image)

    def test_invalid_mobile_banner_rejected(self):
        data = {"name": "Cove", "slug": "cove", "category": self.category.pk, "order": 1, "robots": "index, follow", "banner_mobile_image": SimpleUploadedFile("bad.png", b"nope")}
        response = self.client.post(reverse("dashboard:collection_update", args=[self.collection.pk]), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("banner_mobile_image", response.context["form"].errors)

    def test_contact_and_hero_slide_mobile_banner(self):
        response = self.client.post(reverse("dashboard:page_contact"), {"page_title": "Contact", "heading": "Talk", "visit_heading": "Visit", "mail_heading": "Mail", "hours_heading": "Hours", "form_heading": "Form", "form_button_text": "Send", "success_message": "Thanks!", "robots": "index, follow", "banner_image": make_image("b.png"), "banner_mobile_image": make_image("bm.png"), "banner_mobile_alt": "Contact mobile"})
        self.assertEqual(response.status_code, 302)
        page = ContactPage.load()
        self.assertTrue(page.banner_mobile_image)
        self.assertContains(self.client.get("/contact/"), 'data-mobile-alt="Contact mobile"')
        html = self.client.get(reverse("dashboard:page_home")).content.decode()
        self.assertIn('name="slides-__prefix__-mobile_image"', html)
        self.assertIn('name="slides-__prefix__-mobile_alt"', html)


class AdminSecurityTests(DashboardTestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def test_login_lockout_after_repeated_failures(self):
        from django.conf import settings

        for _ in range(settings.ADMIN_LOGIN_MAX_ATTEMPTS):
            response = self.client.post(reverse("dashboard:login"), {"username": "admin", "password": "wrong"})
            self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse("dashboard:login"), {"username": "admin", "password": "Admin-Pass-123!"})
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "Too many failed sign-in attempts", status_code=429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_success_resets_counter(self):
        self.client.post(reverse("dashboard:login"), {"username": "admin", "password": "wrong"})
        response = self.client.post(reverse("dashboard:login"), {"username": "admin", "password": "Admin-Pass-123!"})
        self.assertRedirects(response, reverse("dashboard:index"))
        from apps.dashboard.security import lockout_seconds

        self.assertEqual(lockout_seconds("127.0.0.1", "admin"), 0)

    def test_ip_allowlist_blocks_other_addresses(self):
        from django.test import override_settings

        self.client.force_login(self.superuser)
        with override_settings(ADMIN_ALLOWED_IPS=["203.0.113.0/24"]):
            self.assertEqual(self.client.get(reverse("dashboard:index")).status_code, 403)
            self.assertEqual(self.client.get(reverse("dashboard:index"), REMOTE_ADDR="203.0.113.7").status_code, 200)
            self.assertEqual(self.client.get("/").status_code, 200)  # public site unaffected

    def test_inactivity_logout(self):
        import time

        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get(reverse("dashboard:index")).status_code, 200)
        session = self.client.session
        session["admin_last_activity"] = time.time() - 60 * 60 * 3
        session.save()
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("dashboard:login"), response["Location"])
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_admin_responses_are_not_cached_or_indexed(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("dashboard:index"))
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow, noarchive")
        self.assertEqual(response["X-Frame-Options"], "DENY")
        from django.test import Client

        login_page = Client().get(reverse("dashboard:login"))
        self.assertEqual(login_page.status_code, 200)
        self.assertIn("no-store", login_page["Cache-Control"])

    def test_robots_hides_admin(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Disallow: /admin/")

    def test_weak_password_rejected_on_change(self):
        self.client.force_login(self.superuser)
        response = self.client.post(reverse("dashboard:password_change"), {"old_password": "Admin-Pass-123!", "new_password1": "short1", "new_password2": "short1"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "at least 12 characters")


class MegaMenuTests(DashboardTestCase):
    """The Collections dropdown: category columns, their sub-category links, and ordering."""

    def setUp(self):
        self.client.force_login(self.superuser)
        self.menu = NavigationMenu.objects.create(name="Header", slug="header")
        self.root = NavigationItem.objects.create(menu=self.menu, label="Collections", link_type="none", order=0)
        self.about = NavigationItem.objects.create(menu=self.menu, label="About", link_type="internal", internal_page="website:about", order=1)
        self.column = NavigationItem.objects.create(menu=self.menu, label="Soft Seating", parent=self.root, link_type="category", category=self.category, order=0)
        self.link = NavigationItem.objects.create(menu=self.menu, label="Cove Series", parent=self.column, link_type="collection", collection=self.collection, order=0)

    def payload(self, **extra):
        data = {"label": "New row", "link_type": "none", "is_active": "on"}
        data.update(extra)
        return data

    def test_page_lists_columns_with_their_links_only(self):
        response = self.client.get(reverse("dashboard:mega_menu"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["obj"] for row in response.context["rows"]], [self.column, self.link])
        self.assertEqual([row["depth"] for row in response.context["rows"]], [0, 1])
        self.assertEqual(response.context["column_count"], 1)
        self.assertNotContains(response, 'data-id="%d"' % self.about.pk)  # other bar items stay out of this screen

    def test_add_column(self):
        response = self.client.post(reverse("dashboard:mega_menu_item_create"), self.payload(label="Storage", link_type="none"))
        self.assertRedirects(response, reverse("dashboard:mega_menu"))
        storage = NavigationItem.objects.get(label="Storage")
        self.assertEqual(storage.parent, self.root)
        self.assertEqual(storage.menu, self.menu)
        self.assertEqual(storage.order, 1)  # appended after the existing column

    def test_add_link_inside_a_column(self):
        response = self.client.post(
            reverse("dashboard:mega_menu_item_create"),
            self.payload(label="Pebble Series", parent=self.column.pk, link_type="collection", collection=self.collection.pk),
        )
        self.assertRedirects(response, reverse("dashboard:mega_menu"))
        item = NavigationItem.objects.get(label="Pebble Series")
        self.assertEqual(item.parent, self.column)
        self.assertEqual(item.get_url(), self.collection.get_absolute_url())

    def test_add_form_prefills_the_column_from_the_query_string(self):
        response = self.client.get(reverse("dashboard:mega_menu_item_create") + f"?column={self.column.pk}")
        self.assertEqual(response.context["form"].initial["parent"], self.column.pk)
        self.assertContains(response, "Add link")

    def test_destination_is_required_for_the_chosen_type(self):
        response = self.client.post(reverse("dashboard:mega_menu_item_create"), self.payload(link_type="category"))
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "category", "Choose a category.")

    def test_unused_destinations_are_cleared_on_save(self):
        response = self.client.post(
            reverse("dashboard:mega_menu_item_update", args=[self.link.pk]),
            self.payload(label="Cove Series", parent=self.column.pk, link_type="external", external_url="/contact/?collection=cove"),
        )
        self.assertEqual(response.status_code, 302)
        self.link.refresh_from_db()
        self.assertIsNone(self.link.collection)
        self.assertEqual(self.link.get_url(), "/contact/?collection=cove")

    def test_a_column_holding_links_cannot_become_a_link(self):
        response = self.client.post(
            reverse("dashboard:mega_menu_item_update", args=[self.column.pk]),
            self.payload(label="Soft Seating", parent=self.column.pk, link_type="category", category=self.category.pk),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors["parent"])

    def test_items_outside_the_collections_menu_are_not_editable_here(self):
        for name in ("mega_menu_item_update", "mega_menu_item_delete"):
            self.assertEqual(self.client.get(reverse(f"dashboard:{name}", args=[self.about.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("dashboard:mega_menu_item_toggle_active", args=[self.about.pk])).status_code, 404)

    def test_reorder_columns_and_links(self):
        storage = NavigationItem.objects.create(menu=self.menu, label="Storage", parent=self.root, link_type="none", order=1)
        pebble = NavigationItem.objects.create(menu=self.menu, label="Pebble Series", parent=self.column, link_type="none", order=1)
        self.client.post(
            reverse("dashboard:mega_menu_item_reorder"),
            json.dumps({"order": [storage.pk, self.column.pk, pebble.pk, self.link.pk]}),
            content_type="application/json",
        )
        self.assertEqual([item.label for item in self.root.active_children()], ["Storage", "Soft Seating"])
        self.assertEqual([item.label for item in self.column.active_children()], ["Pebble Series", "Cove Series"])

    def test_reorder_ignores_items_outside_the_menu(self):
        self.client.post(
            reverse("dashboard:mega_menu_item_reorder"),
            json.dumps({"order": [self.about.pk, self.column.pk]}),
            content_type="application/json",
        )
        self.about.refresh_from_db()
        self.assertEqual(self.about.order, 1)

    def test_toggle_hides_the_row_from_the_menu(self):
        self.client.post(reverse("dashboard:mega_menu_item_toggle_active", args=[self.link.pk]))
        self.link.refresh_from_db()
        self.assertFalse(self.link.is_active)
        self.assertEqual(list(self.column.active_children()), [])

    def test_delete_column_removes_its_links(self):
        response = self.client.post(reverse("dashboard:mega_menu_item_delete", args=[self.column.pk]))
        self.assertRedirects(response, reverse("dashboard:mega_menu"))
        self.assertFalse(NavigationItem.objects.filter(pk__in=[self.column.pk, self.link.pk]).exists())

    def test_editor_can_edit_but_not_delete(self):
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(reverse("dashboard:mega_menu")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:mega_menu_item_update", args=[self.link.pk])).status_code, 200)
        self.assertEqual(self.client.post(reverse("dashboard:mega_menu_item_delete", args=[self.link.pk])).status_code, 403)

    def test_staff_is_read_only(self):
        self.client.force_login(self.staffer)
        self.assertEqual(self.client.get(reverse("dashboard:mega_menu")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:mega_menu_item_create")).status_code, 403)

    def test_move_column_up_and_down(self):
        storage = NavigationItem.objects.create(menu=self.menu, label="Storage", parent=self.root, link_type="none", order=1)
        booth = NavigationItem.objects.create(menu=self.menu, label="Phone Booth", parent=self.root, link_type="none", order=2)
        self.client.post(reverse("dashboard:mega_menu_item_move", args=[booth.pk, "up"]))
        self.assertEqual([i.label for i in self.root.active_children()], ["Soft Seating", "Phone Booth", "Storage"])
        self.client.post(reverse("dashboard:mega_menu_item_move", args=[self.column.pk, "down"]))
        self.assertEqual([i.label for i in self.root.active_children()], ["Phone Booth", "Soft Seating", "Storage"])

    def test_move_link_inside_its_column(self):
        pebble = NavigationItem.objects.create(menu=self.menu, label="Pebble Series", parent=self.column, link_type="none", order=1)
        self.client.post(reverse("dashboard:mega_menu_item_move", args=[pebble.pk, "up"]))
        self.assertEqual([i.label for i in self.column.active_children()], ["Pebble Series", "Cove Series"])

    def test_move_at_the_end_of_the_list_does_nothing(self):
        self.client.post(reverse("dashboard:mega_menu_item_move", args=[self.column.pk, "up"]))
        self.assertEqual([i.label for i in self.root.active_children()], ["Soft Seating"])

    def test_move_buttons_are_disabled_at_the_ends(self):
        NavigationItem.objects.create(menu=self.menu, label="Storage", parent=self.root, link_type="none", order=1)
        rows = self.client.get(reverse("dashboard:mega_menu")).context["rows"]
        columns = [row for row in rows if row["depth"] == 0]
        self.assertEqual([(row["is_first"], row["is_last"]) for row in columns], [(True, False), (False, True)])

    def test_move_rejects_items_outside_the_collections_menu(self):
        self.assertEqual(self.client.post(reverse("dashboard:mega_menu_item_move", args=[self.about.pk, "up"])).status_code, 404)

    def test_staff_cannot_move_rows(self):
        self.client.force_login(self.staffer)
        self.assertEqual(self.client.post(reverse("dashboard:mega_menu_item_move", args=[self.column.pk, "down"])).status_code, 403)
