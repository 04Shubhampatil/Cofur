import time

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.catalog.models import Collection, Product

from .forms import EnquiryForm
from .models import Enquiry
from .services import RATE_LIMIT


def valid_data(**extra):
    data = {
        "name": "Asha Rao",
        "email": "asha@example.com",
        "phone": "+91 98765 43210",
        "company": "Studio A",
        "message": "We need seating for a 40-person office in Thane.",
        "form_started": str(time.time() - 10),
        "website": "",
    }
    data.update(extra)
    return data


class EnquiryFormTests(TestCase):
    def test_valid(self):
        form = EnquiryForm(valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_honeypot(self):
        form = EnquiryForm(valid_data(website="http://spam"))
        self.assertFalse(form.is_valid())
        self.assertIn("website", form.errors)

    def test_too_fast(self):
        form = EnquiryForm(valid_data(form_started=str(time.time())))
        self.assertFalse(form.is_valid())
        self.assertIn("form_started", form.errors)

    def test_phone_and_message_validation(self):
        self.assertIn("phone", EnquiryForm(valid_data(phone="abc")).errors)
        self.assertIn("message", EnquiryForm(valid_data(message="hi")).errors)
        self.assertIn("email", EnquiryForm(valid_data(email="nope")).errors)

    def test_product_from_slug(self):
        product = Product.objects.create(name="Cove Social", collection=Collection.objects.create(name="Cove"), status="published")
        form = EnquiryForm(valid_data(product_slug="cove-social"))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["product"], product)


@override_settings(ENQUIRY_NOTIFICATION_EMAIL="leads@example.com", EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EnquiryViewTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_contact_form_post_creates_enquiry_and_redirects(self):
        response = self.client.post(reverse("website:enquire"), valid_data(collection="pebble"))
        self.assertEqual(response.status_code, 302)
        enquiry = Enquiry.objects.get()
        self.assertEqual(enquiry.name, "Asha Rao")
        self.assertEqual(enquiry.collection_ref, "pebble")
        self.assertEqual(enquiry.status, Enquiry.STATUS_NEW)
        self.assertEqual(enquiry.source, "contact")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Asha Rao", mail.outbox[0].subject)

    def test_contact_page_post_alias(self):
        response = self.client.post(reverse("website:contact"), valid_data())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Enquiry.objects.count(), 1)

    def test_ajax_post_returns_json(self):
        response = self.client.post(reverse("website:enquire"), valid_data(), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_ajax_invalid_returns_errors(self):
        response = self.client.post(reverse("website:enquire"), valid_data(email="bad"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json()["errors"])
        self.assertEqual(Enquiry.objects.count(), 0)

    def test_invalid_html_post_rerenders_form(self):
        response = self.client.post(reverse("website:enquire"), valid_data(message="x"))
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "little more about your requirement", status_code=400)

    def test_product_enquiry_source(self):
        product = Product.objects.create(name="Cove Social", collection=Collection.objects.create(name="Cove"), status="published")
        response = self.client.post(reverse("website:enquire"), valid_data(product=product.pk), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Enquiry.objects.get().source, "product")

    def test_rate_limit(self):
        for _ in range(RATE_LIMIT):
            self.client.post(reverse("website:enquire"), valid_data(), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        response = self.client.post(reverse("website:enquire"), valid_data(), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 429)


class EnquiryModelTests(TestCase):
    def test_pending(self):
        enquiry = Enquiry.objects.create(name="A", email="a@example.com", message="hello there")
        self.assertTrue(enquiry.is_pending)
        enquiry.status = Enquiry.STATUS_CLOSED
        self.assertFalse(enquiry.is_pending)
        self.assertEqual(str(enquiry), "A (a@example.com)")
