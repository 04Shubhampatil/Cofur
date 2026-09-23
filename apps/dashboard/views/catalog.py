from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View

from apps.catalog.models import Category, Collection, Product, ProductImage
from apps.core.images import validate_image_upload

from ..forms import (
    CategoryForm,
    CollectionForm,
    QuickCategoryForm,
    QuickCollectionForm,
    ProductColorFormSet,
    ProductFeatureFormSet,
    ProductForm,
    ProductImageFormSet,
    ProductSpecificationFormSet,
)
from ..mixins import DashboardPermissionMixin
from .base import (
    DashboardCreateView,
    DashboardDeleteView,
    DashboardListView,
    DashboardUpdateView,
    ReorderView,
    ToggleFieldView,
    _redirect_back,
)

CATALOG_CRUMB = {"label": "Catalog"}


# ------------------------------------------------------------------ quick lists (categories / sub-categories)
class QuickListView(DashboardListView):
    """List with an inline 'add' form at the top, styled after the reference admin."""

    template_name = "dashboard/catalog/quick_list.html"
    quick_form_class = None
    toggle_url_name = None
    parent_field = None
    parent_label = ""
    singular = ""
    image_attr = "image"
    allow_page_size = False

    def get_quick_form(self, data=None, files=None):
        return self.quick_form_class(data, files)

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm(self.add_perm()):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        form = self.get_quick_form(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"{self.singular} '{obj.name}' added.")
            return redirect(request.path)
        messages.error(request, "Please fix the errors below.")
        self.object_list = self.get_queryset()
        return self.render_to_response(self.get_context_data(quick_form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for row in context["rows"]:
            obj = row["obj"]
            row["image"] = getattr(obj, self.image_attr, None)
            row["parent"] = getattr(obj, self.parent_field) if self.parent_field else None
            row["toggle_url"] = reverse(self.toggle_url_name, args=[obj.pk])
            row["edit_url"] = reverse(self.update_url_name, args=[obj.pk])
            row["delete_url"] = reverse(self.delete_url_name, args=[obj.pk])
        context.update({
            "quick_form": kwargs.get("quick_form") or self.get_quick_form(),
            "singular": self.singular,
            "show_parent": bool(self.parent_field),
            "parent_label": self.parent_label,
            "can_add": self.request.user.has_perm(self.add_perm()),
            "can_change": self.request.user.has_perm(self.change_perm()),
            "can_delete": self.request.user.has_perm(self.delete_perm()),
        })
        return context


# ------------------------------------------------------------------ categories
class CategoryListView(QuickListView):
    model = Category
    permission_required = "catalog.view_category"
    page_title = "Categories"
    singular = "Category"
    quick_form_class = QuickCategoryForm
    image_attr = "card_image"
    search_fields = ["name", "slug", "subtitle"]
    filters = [{"name": "is_active", "label": "Status", "type": "bool", "true_label": "Active", "false_label": "Inactive"}]
    update_url_name = "dashboard:category_update"
    delete_url_name = "dashboard:category_delete"
    reorder_url_name = "dashboard:category_reorder"
    toggle_url_name = "dashboard:category_toggle_active"
    breadcrumbs = [CATALOG_CRUMB, {"label": "Categories"}]

    def get_base_queryset(self):
        return Category.objects.prefetch_related("collections")


class CategoryToggleActiveView(ToggleFieldView):
    model = Category
    field = "is_active"
    permission_required = "catalog.change_category"


CATEGORY_FIELDSETS = [
    ("Basic information", ["name", "slug", "subtitle", "description", "card_link_text", "link_override", "show_on_home", "order", "is_active"]),
    ("Images", ["thumbnail_image", "banner_image", "banner_mobile_image", "banner_mobile_alt", "lifestyle_image"]),
    ("SEO", ["seo_title", "meta_description", "meta_keywords", "og_title", "og_description", "og_image", "canonical_url", "robots"]),
]


class CategoryCreateView(DashboardCreateView):
    model = Category
    form_class = CategoryForm
    permission_required = "catalog.add_category"
    page_title = "Add category"
    list_url_name = "dashboard:category_list"
    update_url_name = "dashboard:category_update"
    fieldsets = CATEGORY_FIELDSETS
    success_message = "Category created."
    breadcrumbs = [CATALOG_CRUMB, {"label": "Categories", "url": "dashboard:category_list"}, {"label": "Add"}]


class CategoryUpdateView(DashboardUpdateView):
    model = Category
    form_class = CategoryForm
    permission_required = "catalog.change_category"
    list_url_name = "dashboard:category_list"
    update_url_name = "dashboard:category_update"
    fieldsets = CATEGORY_FIELDSETS
    success_message = "Category updated."
    breadcrumbs = [CATALOG_CRUMB, {"label": "Categories", "url": "dashboard:category_list"}, {"label": "Edit"}]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit category: {self.object.name}"
        context["preview_url"] = self.object.get_absolute_url()
        return context


class CategoryDeleteView(DashboardDeleteView):
    model = Category
    permission_required = "catalog.delete_category"
    list_url_name = "dashboard:category_list"
    success_message = "Category deleted."


class CategoryReorderView(ReorderView):
    model = Category
    permission_required = "catalog.change_category"


# ------------------------------------------------------------------ sub-categories (Collection model)
class CollectionListView(QuickListView):
    model = Collection
    permission_required = "catalog.view_collection"
    page_title = "Sub-Categories"
    singular = "Sub-Category"
    quick_form_class = QuickCollectionForm
    parent_field = "category"
    parent_label = "Category"
    search_fields = ["name", "slug", "tagline"]
    filters = [
        {"name": "category", "label": "Category", "queryset": lambda: Category.objects.all(), "lookup": "category_id"},
        {"name": "is_active", "label": "Status", "type": "bool", "true_label": "Active", "false_label": "Inactive"},
    ]
    update_url_name = "dashboard:collection_update"
    delete_url_name = "dashboard:collection_delete"
    reorder_url_name = "dashboard:collection_reorder"
    toggle_url_name = "dashboard:collection_toggle_active"
    breadcrumbs = [CATALOG_CRUMB, {"label": "Sub-Categories"}]

    def get_base_queryset(self):
        return Collection.objects.select_related("category")


class CollectionToggleActiveView(ToggleFieldView):
    model = Collection
    field = "is_active"
    permission_required = "catalog.change_collection"


COLLECTION_FIELDSETS = [
    ("Basic information", ["name", "slug", "category", "tagline", "description", "order", "is_active"]),
    ("Banner", ["heading", "banner_image", "banner_alt", "banner_mobile_image", "banner_mobile_alt"]),
    ("Card", ["image", "card_style", "link_override"]),
    ("SEO", ["seo_title", "meta_description", "meta_keywords", "og_title", "og_description", "og_image", "canonical_url", "robots"]),
]


class CollectionCreateView(DashboardCreateView):
    model = Collection
    form_class = CollectionForm
    permission_required = "catalog.add_collection"
    page_title = "Add sub-category"
    list_url_name = "dashboard:collection_list"
    update_url_name = "dashboard:collection_update"
    fieldsets = COLLECTION_FIELDSETS
    success_message = "Sub-category created."
    breadcrumbs = [CATALOG_CRUMB, {"label": "Sub-Categories", "url": "dashboard:collection_list"}, {"label": "Add"}]


class CollectionUpdateView(DashboardUpdateView):
    model = Collection
    form_class = CollectionForm
    permission_required = "catalog.change_collection"
    list_url_name = "dashboard:collection_list"
    update_url_name = "dashboard:collection_update"
    fieldsets = COLLECTION_FIELDSETS
    success_message = "Sub-category updated."
    breadcrumbs = [CATALOG_CRUMB, {"label": "Sub-Categories", "url": "dashboard:collection_list"}, {"label": "Edit"}]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit sub-category: {self.object.name}"
        context["preview_url"] = self.object.get_absolute_url()
        context["assigned_products"] = self.object.products.all()
        return context


class CollectionDeleteView(DashboardDeleteView):
    model = Collection
    permission_required = "catalog.delete_collection"
    list_url_name = "dashboard:collection_list"
    success_message = "Sub-category deleted."


class CollectionReorderView(ReorderView):
    model = Collection
    permission_required = "catalog.change_collection"


# ------------------------------------------------------------------ products
class ProductListView(DashboardListView):
    model = Product
    permission_required = "catalog.view_product"
    page_title = "Products"
    template_name = "dashboard/products/list.html"
    columns = [
        {"label": "Image", "field": "thumbnail", "type": "image"},
        {"label": "Product", "field": "name", "type": "title", "sortable": True},
        {"label": "Sub-Category", "field": "collection"},
        {"label": "Category", "field": "category"},
        {"label": "Status", "field": "status", "type": "status"},
        {"label": "Featured", "field": "is_featured", "type": "featured"},
        {"label": "Updated", "field": "updated_at", "type": "date", "sortable": True},
    ]
    search_fields = ["name", "slug", "sku", "tagline"]
    filters = [
        {"name": "category", "label": "Category", "queryset": lambda: Category.objects.all(), "lookup": "category_id"},
        {"name": "collection", "label": "Sub-Category", "queryset": lambda: Collection.objects.select_related("category"), "lookup": "collection_id"},
        {"name": "status", "label": "Status", "choices": Product.STATUS_CHOICES},
        {"name": "featured", "label": "Featured", "type": "bool", "lookup": "is_featured", "true_label": "Featured", "false_label": "Not featured"},
    ]
    paginate_by = 24
    default_ordering = "order"
    create_url_name = "dashboard:product_create"
    update_url_name = "dashboard:product_update"
    delete_url_name = "dashboard:product_delete"
    reorder_url_name = "dashboard:product_reorder"
    breadcrumbs = [CATALOG_CRUMB, {"label": "Products"}]

    def get_base_queryset(self):
        return Product.objects.select_related("collection", "category")


# Sections follow the order of the public product page so editors can see where each image lands.
PRODUCT_TABS = [
    ("basic", "Basic information", ["name", "slug", "sku", "collection", "category", "name_prefix", "tagline", "short_description", "seating_capacity", "areas", "order"]),
    ("overview", "Overview image & card images", ["main_image", "main_image_alt", "description", "materials", "card_image", "hover_image"]),
    ("details", "Product details images", ["details_heading"]),
    ("specs_image", "Specifications image", ["specs_heading", "finish_image"]),
    ("fabric", "Fabric options", ["fabric_heading", "fabric_intro"]),
    ("features", "Features", ["features_heading"]),
    ("dimensions", "Dimensions", ["dimensions_heading", "dimension_width", "dimension_depth", "dimension_height", "dimension_seat_height", "dimension_weight", "dimension_unit", "weight_unit"]),
    ("care", "Material care", ["care_heading"]),
    ("gallery", "Gallery", ["gallery_heading"]),
    ("related", "Related products", ["related_heading", "related_products"]),
    ("publishing", "Publishing", ["status", "is_featured", "cta_text", "cta_url", "enquiry_title", "enquiry_text"]),
    ("seo", "SEO", ["seo_title", "meta_description", "meta_keywords", "og_title", "og_description", "og_image", "canonical_url", "robots"]),
]


class ProductFormMixin:
    model = Product
    form_class = ProductForm
    template_name = "dashboard/products/form.html"
    list_url_name = "dashboard:product_list"
    update_url_name = "dashboard:product_update"

    def get_formsets(self, instance=None):
        data = self.request.POST if self.request.method == "POST" else None
        files = self.request.FILES if self.request.method == "POST" else None
        def images(kind, prefix):
            queryset = ProductImage.objects.filter(kind=kind) if instance else ProductImage.objects.none()
            return ProductImageFormSet(data, files, prefix=prefix, instance=instance, queryset=queryset, form_kwargs={"fixed_kind": kind})

        def features(kind, prefix):
            from apps.catalog.models import ProductFeature

            queryset = ProductFeature.objects.filter(kind=kind) if instance else ProductFeature.objects.none()
            return ProductFeatureFormSet(data, prefix=prefix, instance=instance, queryset=queryset, form_kwargs={"fixed_kind": kind})

        return {
            "detail_images": images(ProductImage.KIND_DETAIL, "detail_images"),
            "colors": ProductColorFormSet(data, files, prefix="colors", instance=instance),
            "features": features("feature", "features"),
            "specs": ProductSpecificationFormSet(data, prefix="specs", instance=instance),
            "dimension_images": images(ProductImage.KIND_DIMENSION, "dimension_images"),
            "care": features("care", "care"),
            "gallery_images": images(ProductImage.KIND_GALLERY, "gallery_images"),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = getattr(self, "object", None)
        if "formsets" not in context:
            context["formsets"] = self.get_formsets(instance if instance and instance.pk else None)
        context["tabs"] = PRODUCT_TABS
        if instance and instance.pk:
            # After an invalid POST the bound form may have blanked the slug; use the stored one.
            saved = Product.objects.filter(pk=instance.pk).only("slug").first()
            context["preview_url"] = saved.get_absolute_url() if saved and saved.slug else ""
            context["gallery_upload_url"] = reverse("dashboard:product_gallery_upload", args=[instance.pk])
        return context

    def form_valid(self, form):
        instance = self.object if getattr(self, "object", None) and self.object.pk else None
        formsets = self.get_formsets(instance)
        # For a new product the formsets have no instance yet; bind after save.
        with transaction.atomic():
            self.object = form.save()
            all_valid = True
            for key, formset in formsets.items():
                formset.instance = self.object
                if not formset.is_valid():
                    all_valid = False
            if not all_valid:
                transaction.set_rollback(True)
        if not all_valid:
            if instance is None:
                self.object = Product(**{f.name: getattr(form.instance, f.name) for f in Product._meta.concrete_fields if f.name != "id"})
            messages.error(self.request, "Please fix the errors in the highlighted rows.")
            return self.render_to_response(self.get_context_data(form=form, formsets=formsets))
        with transaction.atomic():
            for formset in formsets.values():
                formset.save()
        messages.success(self.request, self.success_message)
        return redirect(self.get_success_url())


class ProductCreateView(ProductFormMixin, DashboardCreateView):
    permission_required = "catalog.add_product"
    page_title = "Add product"
    success_message = "Product created."
    breadcrumbs = [CATALOG_CRUMB, {"label": "Products", "url": "dashboard:product_list"}, {"label": "Add"}]


class ProductUpdateView(ProductFormMixin, DashboardUpdateView):
    permission_required = "catalog.change_product"
    success_message = "Product updated."
    breadcrumbs = [CATALOG_CRUMB, {"label": "Products", "url": "dashboard:product_list"}, {"label": "Edit"}]

    def get_queryset(self):
        return Product.objects.prefetch_related("images", "specifications", "feature_items", "colors")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Edit product: {self.object.name}"
        return context


class ProductDeleteView(DashboardDeleteView):
    model = Product
    permission_required = "catalog.delete_product"
    list_url_name = "dashboard:product_list"
    success_message = "Product deleted."


class ProductReorderView(ReorderView):
    model = Product
    permission_required = "catalog.change_product"


class ProductToggleFeaturedView(ToggleFieldView):
    model = Product
    field = "is_featured"
    permission_required = "catalog.change_product"


class ProductTogglePublishView(DashboardPermissionMixin, View):
    permission_required = "catalog.change_product"
    http_method_names = ["post"]

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.status = Product.STATUS_DRAFT if product.is_published else Product.STATUS_PUBLISHED
        product.save(update_fields=["status", "updated_at"])
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True, "status": product.status})
        messages.success(request, f"{product.name} is now {product.get_status_display().lower()}.")
        return _redirect_back(request, "dashboard:product_list")


class ProductDuplicateView(DashboardPermissionMixin, View):
    permission_required = "catalog.add_product"
    http_method_names = ["post"]

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        clone = product.duplicate()
        messages.success(request, f"Duplicated as '{clone.name}'. It is saved as a draft.")
        return redirect("dashboard:product_update", pk=clone.pk)


class ProductGalleryUploadView(DashboardPermissionMixin, View):
    """AJAX multi-upload for product images (drag & drop)."""

    permission_required = "catalog.change_product"
    http_method_names = ["post"]

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        kind = request.POST.get("kind", ProductImage.KIND_GALLERY)
        if kind not in dict(ProductImage.KIND_CHOICES):
            kind = ProductImage.KIND_GALLERY
        files = request.FILES.getlist("images")
        if not files:
            return JsonResponse({"ok": False, "error": "No files received."}, status=400)
        created = []
        errors = []
        start = product.images.filter(kind=kind).count()
        for index, upload in enumerate(files):
            try:
                validate_image_upload(upload)
            except Exception as exc:
                errors.append(f"{upload.name}: {'; '.join(getattr(exc, 'messages', [str(exc)]))}")
                continue
            image = ProductImage(product=product, image=upload, kind=kind, order=start + index, alt_text=product.name)
            image.save()
            created.append({
                "id": image.pk,
                "url": image.image.url,
                "thumb": image.thumbnail.url if image.thumbnail else image.image.url,
                "kind": image.kind,
                "width": image.width,
                "height": image.height,
            })
        return JsonResponse({"ok": not errors or bool(created), "created": created, "errors": errors})


class ProductImageDeleteView(DashboardPermissionMixin, View):
    permission_required = "catalog.change_product"
    http_method_names = ["post"]

    def post(self, request, pk):
        image = get_object_or_404(ProductImage, pk=pk)
        image.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        messages.success(request, "Image removed.")
        return _redirect_back(request, "dashboard:product_list")


class ProductImageReorderView(ReorderView):
    model = ProductImage
    permission_required = "catalog.change_product"


class ProductBulkActionView(DashboardPermissionMixin, View):
    permission_required = "catalog.change_product"
    http_method_names = ["post"]

    def post(self, request):
        ids = [int(i) for i in request.POST.getlist("ids") if str(i).isdigit()]
        action = request.POST.get("action")
        qs = Product.objects.filter(pk__in=ids)
        count = qs.count()
        if not count:
            messages.error(request, "No products selected.")
            return _redirect_back(request, "dashboard:product_list")
        if action == "publish":
            qs.update(status=Product.STATUS_PUBLISHED)
        elif action == "unpublish":
            qs.update(status=Product.STATUS_DRAFT)
        elif action == "feature":
            qs.update(is_featured=True)
        elif action == "unfeature":
            qs.update(is_featured=False)
        elif action == "delete":
            if not request.user.has_perm("catalog.delete_product"):
                from django.core.exceptions import PermissionDenied

                raise PermissionDenied
            for product in qs:
                product.delete()
        else:
            messages.error(request, "Unknown action.")
            return _redirect_back(request, "dashboard:product_list")
        plural = "s" if count != 1 else ""
        messages.success(request, f"{count} product{plural} updated.")
        return _redirect_back(request, "dashboard:product_list")
