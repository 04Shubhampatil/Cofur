from django.test import TestCase

from apps.core.tests import make_image

from .models import Category, Collection, Product, ProductFeature, ProductImage, ProductSpecification


class CategoryCollectionTests(TestCase):
    def test_slug_generation_and_uniqueness(self):
        a = Category.objects.create(name="Soft Seating")
        b = Category.objects.create(name="Soft Seating")
        self.assertEqual(a.slug, "soft-seating")
        self.assertEqual(b.slug, "soft-seating-2")

    def test_links_and_override(self):
        cat = Category.objects.create(name="Acoustic Lights", link_override="/contact/?collection=acoustic-lights")
        self.assertEqual(cat.link, "/contact/?collection=acoustic-lights")
        col = Collection.objects.create(name="Cove", category=cat)
        self.assertEqual(col.link, "/collections/cove/")
        self.assertEqual(col.display_heading, "Cove\ncollection")
        self.assertEqual(cat.get_absolute_url(), "/categories/acoustic-lights/")

    def test_active_collections(self):
        cat = Category.objects.create(name="Seating")
        Collection.objects.create(name="A", category=cat)
        Collection.objects.create(name="B", category=cat, is_active=False)
        self.assertEqual([c.name for c in cat.active_collections()], ["A"])


class ProductTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Soft Seating")
        self.collection = Collection.objects.create(name="Cove", category=self.category)

    def test_category_inherited_from_collection(self):
        product = Product.objects.create(name="Cove Solo", collection=self.collection)
        self.assertEqual(product.category, self.category)
        self.assertEqual(product.slug, "cove-solo")
        self.assertEqual(product.get_absolute_url(), "/products/cove-solo/")

    def test_published_manager(self):
        Product.objects.create(name="Draft", collection=self.collection)
        Product.objects.create(name="Live", collection=self.collection, status=Product.STATUS_PUBLISHED, is_featured=True)
        self.assertEqual([p.name for p in Product.objects.published()], ["Live"])
        self.assertEqual(Product.objects.featured().count(), 1)

    def test_thumbnail_generated_and_large_image_shrunk(self):
        product = Product(name="Big", collection=self.collection)
        product.main_image = make_image("big.jpg", size=(3000, 1500), fmt="JPEG")
        product.save()
        product.refresh_from_db()
        self.assertTrue(product.thumbnail)
        from apps.core.images import image_dimensions

        self.assertLessEqual(max(image_dimensions(product.main_image)), 2400)
        self.assertLessEqual(max(image_dimensions(product.thumbnail)), 600)

    def test_display_name_suffix(self):
        product = Product.objects.create(name="Cove Solo Lounge", name_prefix="Cove", collection=self.collection)
        self.assertEqual(product.display_name_suffix, "Solo Lounge")

    def test_related_products_fallback_to_collection(self):
        a = Product.objects.create(name="A", collection=self.collection, status="published")
        b = Product.objects.create(name="B", collection=self.collection, status="published")
        Product.objects.create(name="C", collection=self.collection)  # draft, excluded
        self.assertEqual([p.name for p in a.get_related_products()], ["B"])
        a.related_products.add(b)
        self.assertEqual([p.name for p in a.get_related_products()], ["B"])

    def test_duplicate_copies_children_as_draft(self):
        product = Product.objects.create(name="Cove Social", collection=self.collection, status="published", is_featured=True)
        ProductSpecification.objects.create(product=product, label="Frame", value="Steel")
        ProductFeature.objects.create(product=product, text="Nice")
        ProductImage.objects.create(product=product, image=make_image("g.png"))
        clone = product.duplicate()
        self.assertEqual(clone.name, "Cove Social (copy)")
        self.assertEqual(clone.status, Product.STATUS_DRAFT)
        self.assertFalse(clone.is_featured)
        self.assertNotEqual(clone.slug, product.slug)
        self.assertEqual(clone.specifications.count(), 1)
        self.assertEqual(clone.feature_items.count(), 1)
        self.assertEqual(clone.images.count(), 1)

    def test_card_title_parts(self):
        product = Product.objects.create(name="Cove Solo Lounge", collection=self.collection)
        self.assertEqual(product.card_title_parts(), ("Cove", "Solo Lounge"))
        product = Product.objects.create(name="cove Duo", collection=self.collection)
        self.assertEqual(product.card_title_parts(), ("cove", "Duo"))
        product = Product.objects.create(name="Grove Trio", collection=self.collection, name_prefix="Grove")
        self.assertEqual(product.card_title_parts(), ("Grove", "Trio"))
        product = Product.objects.create(name="Orbit Hub", collection=self.collection)
        self.assertEqual(product.card_title_parts(), ("", "Orbit Hub"))
        product = Product.objects.create(name="Cove", collection=self.collection)
        self.assertEqual(product.card_title_parts(), ("", "Cove"))

    def test_collection_display_heading(self):
        self.assertEqual(self.collection.display_heading, "Cove\ncollection")
        self.collection.heading = "The Cove\r\nseries"
        self.collection.save()
        self.assertEqual(self.collection.heading, "The Cove\nseries")
        self.assertEqual(self.collection.display_heading, "The Cove\nseries")

    def test_dimension_rows(self):
        product = Product.objects.create(name="Dims", collection=self.collection, dimension_width="160", dimension_weight="90")
        self.assertTrue(product.has_dimensions)
        self.assertEqual(product.dimension_rows(), [("Width", "160", "cm"), ("Weight", "90", "kg")])

    def test_product_image_kinds(self):
        product = Product.objects.create(name="Img", collection=self.collection)
        ProductImage.objects.create(product=product, image=make_image("a.png"), kind=ProductImage.KIND_GALLERY)
        ProductImage.objects.create(product=product, image=make_image("b.png"), kind=ProductImage.KIND_DETAIL)
        self.assertEqual(product.gallery_images().count(), 1)
        self.assertEqual(product.detail_images().count(), 1)
        self.assertTrue(product.gallery_images().first().thumbnail)


class WebPConversionTests(TestCase):
    def test_uploads_are_stored_as_webp(self):
        from django.test import override_settings

        category = Category.objects.create(name="Soft Seating")
        collection = Collection.objects.create(name="Cove", category=category)
        product = Product(name="Png", collection=collection)
        product.main_image = make_image("photo.png", size=(500, 400))
        product.hover_image = make_image("hover.jpg", size=(500, 400), fmt="JPEG")
        product.save()
        product.refresh_from_db()
        self.assertTrue(product.main_image.name.endswith(".webp"), product.main_image.name)
        self.assertTrue(product.hover_image.name.endswith(".webp"))
        self.assertTrue(product.thumbnail.name.endswith(".webp"))
        from PIL import Image as PILImage

        with product.main_image.open("rb") as fh:
            self.assertEqual(PILImage.open(fh).format, "WEBP")
        self.assertFalse(product.main_image.storage.exists("products/photo.png"))
        with override_settings(IMAGE_CONVERT_WEBP=False):
            member_like = ProductImage.objects.create(product=product, image=make_image("keep.png"))
            self.assertTrue(member_like.image.name.endswith(".png"))

    def test_svg_and_gif_untouched(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        category = Category.objects.create(name="Lights")
        category.thumbnail_image = SimpleUploadedFile("icon.svg", b"<svg xmlns='http://www.w3.org/2000/svg'></svg>")
        category.save()
        category.refresh_from_db()
        self.assertTrue(category.thumbnail_image.name.endswith(".svg"))
