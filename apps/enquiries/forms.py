import re
import time

from django import forms
from django.core.exceptions import ValidationError

from apps.catalog.models import Product

from .models import Enquiry

PHONE_RE = re.compile(r"^[0-9 +()\-]{7,20}$")
URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)


class EnquiryForm(forms.ModelForm):
    """Public enquiry form with basic spam protection (honeypot + minimum fill time)."""

    website = forms.CharField(required=False, widget=forms.HiddenInput, label="Leave empty")  # honeypot
    form_started = forms.CharField(required=False, widget=forms.HiddenInput)
    product_slug = forms.CharField(required=False, widget=forms.HiddenInput)
    collection = forms.CharField(required=False, max_length=120, widget=forms.HiddenInput)

    class Meta:
        model = Enquiry
        fields = ["name", "email", "phone", "company", "city", "product", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].required = False
        self.fields["product"].queryset = Product.objects.published().order_by("name")
        self.fields["product"].empty_label = "Select a product (optional)"
        self.fields["name"].widget.attrs.update({"autocomplete": "name", "maxlength": 150})
        self.fields["email"].widget.attrs.update({"autocomplete": "email"})
        self.fields["phone"].widget.attrs.update({"autocomplete": "tel", "type": "tel"})
        self.fields["company"].widget.attrs.update({"autocomplete": "organization"})
        self.fields["city"].widget.attrs.update({"autocomplete": "address-level2"})
        self.fields["message"].required = True

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise ValidationError("Spam detected.")
        return ""

    def clean_form_started(self):
        value = self.cleaned_data.get("form_started")
        if value:
            try:
                started = float(value)
            except ValueError:
                return value
            if time.time() - started < 2:
                raise ValidationError("The form was submitted too quickly. Please try again.")
        return value

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if phone and not PHONE_RE.match(phone):
            raise ValidationError("Enter a valid phone number.")
        return phone

    def clean_message(self):
        message = (self.cleaned_data.get("message") or "").strip()
        if len(message) < 5:
            raise ValidationError("Please tell us a little more about your requirement.")
        if len(URL_RE.findall(message)) > 3:
            raise ValidationError("Too many links in the message.")
        return message

    def clean(self):
        cleaned = super().clean()
        slug = cleaned.get("product_slug")
        if slug and not cleaned.get("product"):
            cleaned["product"] = Product.objects.filter(slug=slug).first()
        return cleaned
