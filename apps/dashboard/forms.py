from django import forms
from django.forms import inlineformset_factory

from apps.catalog.models import (
    Category,
    Collection,
    Product,
    ProductColor,
    ProductFeature,
    ProductImage,
    ProductSpecification,
)
from apps.core.models import NavigationItem, SiteSettings
from apps.enquiries.models import Enquiry
from apps.pages.models import (
    AboutPage,
    ContactPage,
    Differentiator,
    HomeHeroSlide,
    HomePage,
    HomeStatementLine,
)
from apps.team.models import TeamMember

from .fields import CMSImageField, cms_formfield_callback

SEO_FIELDS = ["seo_title", "meta_description", "meta_keywords", "og_title", "og_description", "og_image", "canonical_url", "robots"]


class CMSModelForm(forms.ModelForm):
    """Base form: consistent widgets/classes and image validation."""

    class Meta:
        formfield_callback = cms_formfield_callback

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            css = widget.attrs.get("class", "")
            if isinstance(widget, (forms.CheckboxInput,)):
                widget.attrs["class"] = f"{css} form-check".strip()
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = f"{css} form-select".strip()
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = f"{css} form-textarea".strip()
                widget.attrs.setdefault("rows", 4)
            elif isinstance(widget, forms.FileInput):
                pass
            else:
                widget.attrs["class"] = f"{css} form-input".strip()


# ---------------------------------------------------------------- catalog
class CategoryForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = Category
        labels = {"banner_image": "Banner image (desktop)", "thumbnail_image": "Card image (home page rail)", "lifestyle_image": "Lifestyle image"}
        help_texts = {
            "banner_image": "Full-width photo at the top of this category page. Recommended 1440px wide or more.",
            "lifestyle_image": "Tall photo shown in the sub-category grid after the second card (or after the last card when there is only one).",
        }
        fields = [
            "name", "slug", "subtitle", "description", "thumbnail_image", "banner_image", "banner_mobile_image", "banner_mobile_alt",
            "lifestyle_image", "link_override", "card_link_text", "show_on_home",
            "order", "is_active", *SEO_FIELDS,
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False


class CollectionForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = Collection
        fields = [
            "name", "slug", "category", "tagline", "description", "heading", "image", "banner_image",
            "banner_alt", "banner_mobile_image", "banner_mobile_alt", "link_override", "card_style", "order", "is_active", *SEO_FIELDS,
        ]
        widgets = {
            "heading": forms.Textarea(attrs={"rows": 2, "placeholder": "Cove\ncollection"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False
        self.fields["category"].queryset = Category.objects.all()
        self.fields["is_active"].label = "Published (visible on the website)"


class QuickCategoryForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = Category
        fields = ["name", "thumbnail_image"]
        labels = {"name": "Title", "thumbnail_image": "Image"}
        widgets = {"thumbnail_image": forms.ClearableFileInput()}


class QuickCollectionForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = Collection
        fields = ["category", "name", "image"]
        labels = {"name": "Title", "image": "Image"}
        widgets = {"image": forms.ClearableFileInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.all()
        self.fields["category"].empty_label = "Select category"
        self.fields["category"].required = True


class ProductForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = Product
        fields = [
            "name", "slug", "sku", "collection", "category", "name_prefix", "tagline", "short_description", "description",
            "main_image", "main_image_alt", "card_image", "hover_image", "finish_image",
            "seating_capacity", "areas", "materials", "fabric_intro",
            "dimension_width", "dimension_depth", "dimension_height", "dimension_seat_height", "dimension_weight",
            "dimension_unit", "weight_unit",
            "details_heading", "specs_heading", "gallery_heading", "related_heading", "fabric_heading",
            "features_heading", "dimensions_heading", "care_heading",
            "cta_text", "cta_url", "enquiry_title", "enquiry_text", "related_products",
            "status", "is_featured", "order", *SEO_FIELDS,
        ]
        widgets = {
            "related_products": forms.SelectMultiple(attrs={"size": 8}),
            "short_description": forms.Textarea(attrs={"rows": 3}),
            "description": forms.Textarea(attrs={"rows": 8}),
            "areas": forms.Textarea(attrs={"rows": 3}),
            "materials": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False
        qs = Product.objects.all().order_by("name")
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        self.fields["related_products"].queryset = qs
        self.fields["collection"].queryset = Collection.objects.select_related("category")
        self.fields["collection"].label = "Sub-category"


class ProductImageForm(CMSModelForm):
    """Row of one product-media formset. ``fixed_kind`` pins the row to a page section."""

    class Meta(CMSModelForm.Meta):
        model = ProductImage
        fields = ["image", "video_file", "video_url", "alt_text", "caption", "kind", "order"]
        widgets = {"video_file": forms.ClearableFileInput(attrs={"accept": "video/mp4,video/webm,.mp4,.webm,.m4v,.mov"}), "kind": forms.HiddenInput()}

    def __init__(self, *args, fixed_kind=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fixed_kind = fixed_kind
        if fixed_kind:
            self.fields["kind"].initial = fixed_kind
            self.fields["kind"].required = False
            if fixed_kind != ProductImage.KIND_DETAIL:
                del self.fields["video_file"]
                del self.fields["video_url"]

    def clean_kind(self):
        return self.fixed_kind or self.cleaned_data.get("kind")

    def clean_video_file(self):
        from django.conf import settings

        upload = self.cleaned_data.get("video_file")
        if upload and hasattr(upload, "size") and getattr(upload, "content_type", None) is not None:
            ext = upload.name.rsplit(".", 1)[-1].lower() if "." in upload.name else ""
            if ext not in settings.ALLOWED_VIDEO_EXTENSIONS:
                raise forms.ValidationError("Upload an MP4, WebM, M4V or MOV file.")
            if upload.size > settings.MAX_VIDEO_UPLOAD_MB * 1024 * 1024:
                raise forms.ValidationError(f"Video is too large (max {settings.MAX_VIDEO_UPLOAD_MB} MB).")
        return upload

    def clean_video_url(self):
        url = (self.cleaned_data.get("video_url") or "").strip()
        if url:
            probe = ProductImage(video_url=url)
            if not probe.embed_url:
                raise forms.ValidationError("Enter a YouTube or Vimeo page link, e.g. https://youtu.be/abc123.")
        return url

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("DELETE"):
            return cleaned
        has_video = bool(cleaned.get("video_file") or cleaned.get("video_url"))
        if has_video and (self.fixed_kind or cleaned.get("kind")) != ProductImage.KIND_DETAIL:
            self.add_error("kind", "Videos can only be used in the product details mosaic.")
        if not cleaned.get("image") and not has_video:
            self.add_error("image", "Add an image, or a video for a mosaic tile.")
        return cleaned


ProductImageFormSet = inlineformset_factory(Product, ProductImage, form=ProductImageForm, extra=0, can_delete=True)


class ProductSpecificationForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = ProductSpecification
        fields = ["label", "value", "order"]


ProductSpecificationFormSet = inlineformset_factory(Product, ProductSpecification, form=ProductSpecificationForm, extra=0, can_delete=True)


class ProductFeatureForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = ProductFeature
        fields = ["text", "kind", "order"]
        widgets = {"kind": forms.HiddenInput()}

    def __init__(self, *args, fixed_kind=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fixed_kind = fixed_kind
        if fixed_kind:
            self.fields["kind"].initial = fixed_kind
            self.fields["kind"].required = False

    def clean_kind(self):
        return self.fixed_kind or self.cleaned_data.get("kind")


ProductFeatureFormSet = inlineformset_factory(Product, ProductFeature, form=ProductFeatureForm, extra=0, can_delete=True)


class ProductColorForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = ProductColor
        fields = ["name", "hex_code", "swatch_image", "finish_image", "order"]


ProductColorFormSet = inlineformset_factory(Product, ProductColor, form=ProductColorForm, extra=0, can_delete=True)


class GalleryUploadForm(forms.Form):
    """Multi-image upload used by the product images tab (AJAX)."""

    kind = forms.ChoiceField(choices=ProductImage.KIND_CHOICES, initial=ProductImage.KIND_GALLERY)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["images"] = CMSImageField(widget=forms.ClearableFileInput(attrs={"multiple": True}), required=False)

    def clean_images(self):
        files = self.files.getlist("images")
        for upload in files:
            from apps.core.images import validate_image_upload

            validate_image_upload(upload)
        return files


# ---------------------------------------------------------------- pages
class HomePageForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = HomePage
        fields = [
            "hero_heading", "hero_visible",
            "intro_heading", "intro_heading_highlight", "intro_visible", "category_section_visible",
            "statement_heading", "statement_description", "statement_cta_text", "statement_cta_url", "statement_visible",
            "featured_heading", "featured_cta_text", "featured_visible",
            "why_heading", "why_image", "why_image_alt", "why_visible",
        ]


class HeroSlideForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = HomeHeroSlide
        fields = ["image", "alt_text", "mobile_image", "mobile_alt", "order", "is_active"]


HeroSlideFormSet = inlineformset_factory(HomePage, HomeHeroSlide, form=HeroSlideForm, extra=0, can_delete=True)


class StatementLineForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = HomeStatementLine
        fields = ["verb", "text", "image", "alt_text", "order", "is_active"]


StatementLineFormSet = inlineformset_factory(HomePage, HomeStatementLine, form=StatementLineForm, extra=0, can_delete=True)


class DifferentiatorForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = Differentiator
        fields = ["heading", "order", "is_active"]


DifferentiatorFormSet = inlineformset_factory(HomePage, Differentiator, form=DifferentiatorForm, extra=0, can_delete=True)


class AboutPageForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = AboutPage
        fields = [
            "hero_heading", "hero_image", "hero_image_alt", "hero_mobile_image", "hero_mobile_alt",
            "intro_heading", "intro_text",
            "what_we_make_heading", "what_we_make_content",
            "how_we_work_heading", "how_we_work_content",
            "philosophy_heading", "philosophy_content",
            "mission_heading", "mission_content",
            "team_heading", "team_visible",
            "find_us_heading", "find_us_company", "find_us_address", "find_us_map_url", "find_us_visible",
            "sustainability_heading", "sustainability_content", "sustainability_image", "sustainability_image_alt",
            "recycled_heading", "recycled_content",
            "tree_heading", "tree_description",
            "india_image", "india_text", "india_visible",
        ]


class ContactPageForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = ContactPage
        fields = [
            "page_title", "banner_image", "banner_alt", "banner_mobile_image", "banner_mobile_alt", "eyebrow", "heading", "intro_text",
            "visit_heading", "address", "mail_heading", "email", "hours_heading", "working_hours",
            "form_heading", "form_button_text", "success_message",
        ]


# ---------------------------------------------------------------- team / enquiries
class TeamMemberForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = TeamMember
        fields = ["name", "designation", "quote", "biography", "image", "linkedin_url", "email", "order", "is_active"]
        widgets = {"biography": forms.Textarea(attrs={"rows": 8}), "quote": forms.Textarea(attrs={"rows": 3})}


class EnquiryUpdateForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = Enquiry
        fields = ["status", "admin_notes"]
        widgets = {"admin_notes": forms.Textarea(attrs={"rows": 6})}


# ---------------------------------------------------------------- media / settings
class SiteSettingsForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = SiteSettings
        fields = [
            "site_name", "tagline", "logo", "logo_light", "favicon", "contact_email", "whatsapp_number",
            "whatsapp_message", "address", "google_maps_url", "linkedin_url", "instagram_url", "twitter_url",
        ]


class FooterSettingsForm(CMSModelForm):
    class Meta(CMSModelForm.Meta):
        model = SiteSettings
        fields = [
            "logo_light", "footer_eyebrow", "footer_title", "footer_primary_cta_text",
            "footer_primary_cta_url", "footer_secondary_cta_text", "footer_secondary_cta_url",
            "copyright_text", "address", "google_maps_url", "contact_email", "linkedin_url", "instagram_url", "twitter_url",
        ]


# ---------------------------------------------------------------- collections mega menu
class MegaMenuItemForm(CMSModelForm):
    """One column heading, or one link inside a column, of the Collections mega menu."""

    LINK_TYPES = [
        ("category", "Category page"),
        ("collection", "Sub-category page"),
        ("external", "Custom URL / path"),
        ("none", "No link (heading only)"),
    ]

    class Meta(CMSModelForm.Meta):
        model = NavigationItem
        fields = ["parent", "label", "link_type", "category", "collection", "external_url", "url_suffix", "open_in_new_tab", "is_active"]
        labels = {
            "parent": "Column",
            "link_type": "Opens",
            "collection": "Sub-category",
            "category": "Category",
            "external_url": "Custom URL / path",
            "is_active": "Visible in the menu",
        }
        help_texts = {
            "label": "The text visitors see, e.g. 'Phone Booth 01'.",
            "url_suffix": "Optional anchor or query added to the link, e.g. #sustainability.",
        }

    def __init__(self, *args, root=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.root = root
        columns = NavigationItem.objects.filter(parent=root).order_by("order", "id")
        if self.instance.pk:
            columns = columns.exclude(pk=self.instance.pk)
        self.fields["parent"].queryset = columns
        self.fields["parent"].required = False
        self.fields["parent"].empty_label = "— None: this is a column of its own —"
        self.fields["parent"].help_text = "Leave empty to add another column to the menu."
        # Keep any link type the existing row already uses, even if it is not offered for new rows.
        choices = list(self.LINK_TYPES)
        current = self.instance.link_type if self.instance.pk else None
        if current and current not in {value for value, _ in choices}:
            choices.append((current, dict(NavigationItem.LINK_TYPES)[current]))
        self.fields["link_type"].choices = choices
        self.fields["category"].queryset = Category.objects.all()
        self.fields["collection"].queryset = Collection.objects.select_related("category")
        for name in ("category", "collection"):
            self.fields[name].required = False

    def clean(self):
        cleaned = super().clean()
        link_type = cleaned.get("link_type")
        required_for = {
            "category": ("category", "Choose a category."),
            "collection": ("collection", "Choose a sub-category."),
            "external": ("external_url", "Enter a URL or a path such as /contact/?collection=storage."),
        }
        if link_type in required_for:
            field, message = required_for[link_type]
            if not cleaned.get(field):
                self.add_error(field, message)
        if cleaned.get("parent") and self.instance.pk and self.instance.children.exists():
            self.add_error("parent", "This column holds links, so it has to stay a column. Move or delete its links first.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.menu = self.root.menu
        # No column chosen means the row belongs directly under 'Collections' as a column.
        obj.parent = self.cleaned_data.get("parent") or self.root
        if obj.link_type != "category":
            obj.category = None
        if obj.link_type != "collection":
            obj.collection = None
        if obj.link_type != "external":
            obj.external_url = ""
        if obj.pk is None:
            siblings = NavigationItem.objects.filter(parent=obj.parent).order_by("-order").first()
            obj.order = (siblings.order + 1) if siblings else 0
        if commit:
            obj.save()
        return obj
