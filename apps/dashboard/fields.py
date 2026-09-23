"""Form fields/widgets used by the dashboard."""
from django import forms

from apps.core.images import validate_image_upload


class ImagePickerWidget(forms.ClearableFileInput):
    """File input with preview and clear checkbox."""

    template_name = "dashboard/widgets/image_picker.html"

    def value_from_datadict(self, data, files, name):
        return super().value_from_datadict(data, files, name)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        try:
            context["widget"]["preview_url"] = value.url if value and hasattr(value, "url") else ""
        except ValueError:
            context["widget"]["preview_url"] = ""
        return context


class CMSImageField(forms.ImageField):
    """ImageField that validates type/size/dimensions with Pillow."""

    widget = ImagePickerWidget

    def clean(self, data, initial=None):
        value = super().clean(data, initial)
        if data and hasattr(data, "read"):
            validate_image_upload(data)
        return value


def cms_formfield_callback(db_field, **kwargs):
    from django.db import models as dj_models

    if isinstance(db_field, dj_models.ImageField):
        kwargs["form_class"] = CMSImageField
        kwargs.setdefault("widget", ImagePickerWidget)
    return db_field.formfield(**kwargs)
