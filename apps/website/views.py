from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.catalog.models import Category, Collection, Product
from apps.core.models import SiteSettings
from apps.enquiries.forms import EnquiryForm
from apps.enquiries.services import is_rate_limited, save_enquiry
from apps.pages.models import AboutPage, ContactPage, HomePage
from apps.team.models import TeamMember


def _seo(request, obj, title, description="", image=None):
    site = SiteSettings.load()
    return obj.seo_context(
        request,
        fallback_title=title or site.default_meta_title,
        fallback_description=description or site.default_meta_description,
        fallback_image=image or site.default_og_image,
    )


def home(request):
    page = HomePage.load()
    categories = Category.objects.filter(is_active=True, show_on_home=True)
    context = {
        "page": page,
        "hero_slides": page.hero_slides.filter(is_active=True),
        "statement_lines": page.statement_lines.filter(is_active=True),
        "categories": categories,
        "featured_products": page.featured_products(),
        "differentiators": page.differentiators.filter(is_active=True),
        "seo": _seo(request, page, "Cofur — Furniture for the way people work"),
        "body_page": "home",
    }
    return render(request, "pages/home.html", context)


def about(request):
    page = AboutPage.load()
    context = {
        "page": page,
        "team_members": TeamMember.objects.filter(is_active=True),
        "seo": _seo(request, page, f"About {SiteSettings.load().site_name}", page.intro_text[:160], page.hero_image),
        "body_page": "about",
    }
    return render(request, "pages/about.html", context)


def collection_list(request):
    """All active collections, presented with the soft-seating grid design."""
    collections = Collection.objects.filter(is_active=True).select_related("category")
    primary = Category.objects.filter(is_active=True, slug="soft-seating").first() or Category.objects.filter(is_active=True).first()
    context = {
        "category": primary,
        "collections": collections,
        "heading": "Collections",
        "seo": SiteSettings.load() and {
            "title": "Collections — Cofur",
            "description": "Explore Cofur collections for focused, flexible and social workplaces.",
            "canonical": request.build_absolute_uri(request.path),
            "robots": "index, follow",
        },
        "body_page": "soft-seating",
    }
    return render(request, "pages/collections.html", context)


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    context = {
        "category": category,
        "collections": category.active_collections(),
        "heading": category.name,
        "seo": _seo(request, category, f"{category.name} — Cofur", category.description[:160], category.banner_image),
        "body_page": "soft-seating",
    }
    return render(request, "pages/collections.html", context)


def collection_detail(request, slug):
    collection = get_object_or_404(Collection.objects.select_related("category"), slug=slug, is_active=True)
    products = collection.published_products()
    context = {
        "collection": collection,
        "products": products,
        "seo": _seo(request, collection, f"{collection.name} Collection — Cofur", collection.description[:160], collection.banner_image),
        "body_page": "cove-collection",
    }
    return render(request, "pages/collection-detail.html", context)


def product_detail(request, slug):
    qs = Product.objects.select_related("collection", "category").prefetch_related(
        "images", "specifications", "feature_items", "colors"
    )
    if request.user.is_staff:
        product = get_object_or_404(qs, slug=slug)
    else:
        product = get_object_or_404(qs.published(), slug=slug)
    form = EnquiryForm(initial={"product_slug": product.slug, "form_started": timezone.now().timestamp()})
    context = {
        "product": product,
        "colors": product.colors.all(),
        "detail_images": product.detail_images(),
        "dimension_images": product.dimension_images(),
        "gallery_images": product.gallery_images(),
        "features": product.features(),
        "care_items": product.care_items(),
        "specifications": product.specifications.all(),
        "related_products": product.get_related_products(),
        "enquiry_form": form,
        "seo": _seo(request, product, f"{product.name} — Cofur", product.short_description[:160], product.main_image),
        "body_page": "cove-social",
    }
    return render(request, "pages/product-detail.html", context)


def _enquiry_form_kwargs(request):
    return {"initial": {"form_started": timezone.now().timestamp(), "collection": request.GET.get("collection", "")[:120]}}


@require_http_methods(["GET", "POST"])
def contact(request):
    page = ContactPage.load()
    if request.method == "POST":
        return enquire(request)
    # Legacy "?collection=<slug>" links: send visitors to that item's own page when it exists.
    ref = request.GET.get("collection", "").strip()
    if ref:
        target = Collection.objects.filter(slug=ref, is_active=True).first() or Category.objects.filter(slug=ref, is_active=True).first()
        if target:
            return redirect(target.get_absolute_url())
    form = EnquiryForm(**_enquiry_form_kwargs(request))
    context = {
        "page": page,
        "form": form,
        "seo": _seo(request, page, f"{page.page_title} — Cofur", page.intro_text[:160], page.banner_image),
        "body_page": "enquiry",
        "collection_ref": request.GET.get("collection", ""),
    }
    return render(request, "pages/contact.html", context)


def _wants_json(request):
    accept = request.headers.get("Accept", "")
    return request.headers.get("X-Requested-With") == "XMLHttpRequest" or "application/json" in accept


@require_http_methods(["GET", "POST"])
def enquire(request):
    """Enquiry endpoint used by the contact form and the product enquiry popup.

    GET renders the contact page; POST accepts either a normal form submission or
    an AJAX submission (returns JSON).
    """
    page = ContactPage.load()
    if request.method == "GET":
        return contact(request)

    if is_rate_limited(request):
        if _wants_json(request):
            return JsonResponse({"ok": False, "errors": {"__all__": ["Too many enquiries. Please try again later."]}}, status=429)
        messages.error(request, "Too many enquiries from your connection. Please try again later.")
        return redirect("website:contact")

    form = EnquiryForm(request.POST)
    if form.is_valid():
        enquiry = form.save(commit=False)
        source = "product" if enquiry.product_id else "contact"
        save_enquiry(enquiry, request, source=source, collection_ref=form.cleaned_data.get("collection", ""))
        if _wants_json(request):
            return JsonResponse({"ok": True, "message": page.success_message})
        messages.success(request, page.success_message)
        return redirect(f"{request.path}?sent=1#enquiry-form" if request.path.endswith("/contact/") else "/contact/?sent=1#enquiry-form")

    if _wants_json(request):
        return JsonResponse({"ok": False, "errors": form.errors}, status=400)
    context = {
        "page": page,
        "form": form,
        "seo": _seo(request, page, f"{page.page_title} — Cofur", page.intro_text[:160], page.banner_image),
        "body_page": "enquiry",
        "collection_ref": request.POST.get("collection", ""),
    }
    return render(request, "pages/contact.html", context, status=400)


def legacy_redirect(target_name, **kwargs):
    def view(request):
        return redirect(target_name, permanent=True, **kwargs)

    return view
