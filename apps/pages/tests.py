from django.test import TestCase

from apps.catalog.models import Collection, Product

from .models import AboutPage, ContactPage, Differentiator, HomePage


class PageSingletonTests(TestCase):
    def test_singletons(self):
        for model in (HomePage, AboutPage, ContactPage):
            first = model.load()
            second = model.load()
            self.assertEqual(first.pk, second.pk)
            self.assertEqual(model.objects.count(), 1)

    def test_featured_products_only_published_in_order(self):
        page = HomePage.load()
        collection = Collection.objects.create(name="Grove")
        live = Product.objects.create(name="Grove Trio", collection=collection, status="published", is_featured=True, order=2)
        first = Product.objects.create(name="Cove Duo", collection=collection, status="published", is_featured=True, order=1)
        Product.objects.create(name="Draft", collection=collection, is_featured=True)
        Product.objects.create(name="Not featured", collection=collection, status="published")
        self.assertEqual(page.featured_products(), [first, live])

    def test_about_value_sections(self):
        page = AboutPage.load()
        page.what_we_make_content = "text"
        page.save()
        sections = page.value_sections()
        self.assertEqual(len(sections), 3)
        self.assertEqual(sections[0]["heading"], "What We Make")

    def test_differentiators_ordering(self):
        page = HomePage.load()
        Differentiator.objects.create(page=page, heading="B", order=2)
        Differentiator.objects.create(page=page, heading="A", order=1)
        self.assertEqual([d.heading for d in page.differentiators.all()], ["A", "B"])
