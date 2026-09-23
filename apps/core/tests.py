import io

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from apps.catalog.models import Category, Collection, Product
from apps.core.images import validate_image_upload
from apps.core.models import NavigationItem, NavigationMenu, SiteSettings
from apps.core.roles import ensure_roles


def make_image(name="test.png", size=(200, 150), fmt="PNG", color=(200, 100, 50)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f"image/{fmt.lower()}")


class SiteSettingsTests(TestCase):
    def test_singleton_load_and_pk(self):
        site = SiteSettings.load()
        self.assertEqual(site.pk, 1)
        site.site_name = "COFUR Test"
        site.save()
        again = SiteSettings.load()
        self.assertEqual(again.pk, 1)
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(again.site_name, "COFUR Test")

    def test_copyright_year_substitution(self):
        site = SiteSettings.load()
        site.copyright_text = "© {year} COFUR"
        from django.utils import timezone

        self.assertIn(str(timezone.now().year), site.copyright_rendered())

    def test_singleton_cannot_be_deleted(self):
        with self.assertRaises(ValueError):
            SiteSettings.load().delete()


class NavigationTests(TestCase):
    def setUp(self):
        self.menu = NavigationMenu.objects.create(name="Header", slug="header")
        self.category = Category.objects.create(name="Soft Seating")
        self.collection = Collection.objects.create(name="Cove", category=self.category)
        self.product = Product.objects.create(name="Cove Social", collection=self.collection, status="published")

    def test_internal_and_suffix(self):
        item = NavigationItem.objects.create(menu=self.menu, label="About", link_type="internal", internal_page="website:about", url_suffix="#sustainability")
        self.assertEqual(item.get_url(), "/about/#sustainability")

    def test_collection_category_product_links(self):
        self.assertEqual(NavigationItem.objects.create(menu=self.menu, label="c", link_type="collection", collection=self.collection).get_url(), "/collections/cove/")
        self.assertEqual(NavigationItem.objects.create(menu=self.menu, label="k", link_type="category", category=self.category).get_url(), "/categories/soft-seating/")
        self.assertEqual(NavigationItem.objects.create(menu=self.menu, label="p", link_type="product", product=self.product).get_url(), "/products/cove-social/")

    def test_external_and_none(self):
        self.assertEqual(NavigationItem.objects.create(menu=self.menu, label="x", link_type="external", external_url="https://example.com").get_url(), "https://example.com")
        self.assertEqual(NavigationItem.objects.create(menu=self.menu, label="n", link_type="none").get_url(), "#")

    def test_nested_children_and_inactive_hidden(self):
        parent = NavigationItem.objects.create(menu=self.menu, label="Collections", link_type="none")
        NavigationItem.objects.create(menu=self.menu, label="Child", parent=parent, link_type="external", external_url="/x/")
        NavigationItem.objects.create(menu=self.menu, label="Hidden", parent=parent, link_type="external", external_url="/y/", is_active=False)
        self.assertEqual([i.label for i in self.menu.top_level_items()], ["Collections"])
        self.assertEqual([i.label for i in parent.active_children()], ["Child"])


class ImageValidationTests(TestCase):
    def test_valid_image_passes(self):
        self.assertEqual(validate_image_upload(make_image(size=(100, 80))), (100, 80))

    def test_invalid_extension_rejected(self):
        with self.assertRaises(ValidationError):
            validate_image_upload(SimpleUploadedFile("evil.exe", b"MZ..."))

    def test_corrupt_image_rejected(self):
        with self.assertRaises(ValidationError):
            validate_image_upload(SimpleUploadedFile("broken.png", b"not really a png"))

    @override_settings(MAX_UPLOAD_SIZE_MB=0)
    def test_size_limit(self):
        with self.assertRaises(ValidationError):
            validate_image_upload(make_image())

    @override_settings(MAX_IMAGE_DIMENSION=100)
    def test_dimension_limit(self):
        with self.assertRaises(ValidationError):
            validate_image_upload(make_image(size=(400, 400)))

    def test_svg_with_script_rejected(self):
        with self.assertRaises(ValidationError):
            validate_image_upload(SimpleUploadedFile("x.svg", b"<svg><script>alert(1)</script></svg>"))
        self.assertEqual(validate_image_upload(SimpleUploadedFile("ok.svg", b"<svg xmlns='http://www.w3.org/2000/svg'></svg>")), (0, 0))


class RolesTests(TestCase):
    def test_roles_created_with_expected_permissions(self):
        groups = ensure_roles()
        self.assertEqual(set(groups), {"Admin", "Editor", "Staff"})
        admin_perms = set(groups["Admin"].permissions.values_list("codename", flat=True))
        self.assertIn("delete_product", admin_perms)
        editor_perms = set(groups["Editor"].permissions.values_list("codename", flat=True))
        self.assertIn("change_product", editor_perms)
        self.assertNotIn("delete_enquiry", editor_perms)
        staff_perms = set(groups["Staff"].permissions.values_list("codename", flat=True))
        self.assertIn("change_enquiry", staff_perms)
        self.assertNotIn("add_product", staff_perms)
        # idempotent
        ensure_roles()
        self.assertEqual(groups["Admin"].permissions.count(), len(admin_perms))


class SeedCommandTests(TestCase):
    def test_seed_is_idempotent(self):
        call_command("seed_cofur", skip_images=True, admin_password="Seed-Pass-123!", verbosity=0)
        counts = (Product.objects.count(), Collection.objects.count(), Category.objects.count(), NavigationItem.objects.count())
        call_command("seed_cofur", skip_images=True, admin_password="Seed-Pass-123!", verbosity=0)
        self.assertEqual(counts, (Product.objects.count(), Collection.objects.count(), Category.objects.count(), NavigationItem.objects.count()))
        self.assertTrue(Product.objects.filter(slug="cove-social").exists())
        self.assertEqual(Product.objects.get(slug="cove-social").specifications.count(), 4)
        self.assertTrue(get_user_model().objects.filter(username="admin", is_superuser=True).exists())
        from apps.team.models import TeamMember

        self.assertEqual(TeamMember.objects.count(), 4)
