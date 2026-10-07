from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_http_methods

from apps.catalog.models import Catalogue, Category, Collection, Product
from apps.core.models import SiteSettings
from apps.enquiries.forms import EnquiryForm
from apps.enquiries.services import is_rate_limited, save_enquiry
from apps.pages.models import AboutPage, CataloguePage, ContactPage, HomePage, ProjectsPage
from apps.projects.models import Project
from apps.stories.models import Story
from apps.team.models import TeamMember


def _page_seo(request, title, description=""):
    """SEO for a listing with no model behind it — same keys as seo_context()."""
    site = SiteSettings.load()
    image_url = ""
    if site.default_og_image:
        try:
            image_url = request.build_absolute_uri(site.default_og_image.url)
        except ValueError:
            image_url = ""
    return {
        "title": title or site.default_meta_title,
        "description": description or site.default_meta_description,
        "keywords": site.default_meta_keywords,
        "og_title": title or site.default_meta_title,
        "og_description": description or site.default_meta_description,
        "og_image": image_url,
        "canonical": request.build_absolute_uri(request.path),
        "robots": site.default_robots,
    }


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


def stories(request):
    """Our Story: every published post, filterable by category and searchable."""
    posts = Story.objects.published()

    # Checkbox filters. Nothing ticked means everything, which is what a visitor
    # expects from a filter row that starts all-on.
    kinds = [k for k in request.GET.getlist("kind") if k in dict(Story.KIND_CHOICES)]
    if kinds:
        posts = posts.filter(kind__in=kinds)

    query = request.GET.get("q", "").strip()
    if query:
        posts = posts.filter(Q(title__icontains=query) | Q(excerpt__icontains=query) | Q(body__icontains=query))

    paginator = Paginator(posts, 9)
    page = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page,
        "posts": page.object_list,
        "total": paginator.count,
        "kinds": [{"value": value, "label": label, "checked": not kinds or value in kinds} for value, label in Story.KIND_CHOICES],
        "query": query,
        "recent_posts": Story.objects.published()[:5],
        "seo": _page_seo(request, f"Our Story — {SiteSettings.load().site_name}", "News, announcements and writing from COFUR."),
        "body_page": "stories",
    }
    return render(request, "pages/stories.html", context)


def story_detail(request, slug):
    post = get_object_or_404(Story.objects.published(), slug=slug)
    context = {
        "post": post,
        "recent_posts": Story.objects.published().exclude(pk=post.pk)[:5],
        "seo": _seo(request, post, post.title, post.summary, post.cover_image),
        "body_page": "story",
    }
    return render(request, "pages/story-detail.html", context)


def projects(request):
    """Every published project as a card, on an editable page."""
    page = ProjectsPage.load()
    context = {
        "page": page,
        "projects": Project.objects.published().prefetch_related("images"),
        "seo": _seo(
            request,
            page,
            f"{page.page_title} — {SiteSettings.load().site_name}",
            page.heading[:160],
            page.banner_image,
        ),
        "body_page": "projects",
    }
    return render(request, "pages/projects.html", context)


def project_detail(request, slug):
    project = get_object_or_404(Project.objects.published().prefetch_related("facts", "images"), slug=slug)
    context = {
        "project": project,
        "carousel": list(project.carousel_images()),
        "gallery": list(project.gallery_images()),
        "facts": list(project.facts.all()),
        "seo": _seo(request, project, project.title, project.meta_description, project.lead_image),
        "body_page": "project",
    }
    return render(request, "pages/project-detail.html", context)


@xframe_options_sameorigin
def catalogue_preview(request, slug):
    """Serve a catalogue PDF so it can be framed by our own pages.

    The site sends X-Frame-Options: DENY everywhere, which is why the PDF came
    up blank inside the preview panel — the browser refused to render a framed
    document. Rather than relax that site-wide, this one response opts in to
    same-origin framing. Everything else stays DENY.
    """
    catalogue = get_object_or_404(Catalogue, slug=slug, is_active=True)
    if not catalogue.pdf:
        raise Http404("No PDF for this catalogue")
    response = FileResponse(catalogue.pdf.open("rb"), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{catalogue.slug}-catalogue.pdf"'
    return response


def catalogues(request):
    """Every range in one place, each card offering its catalogue download."""
    page = CataloguePage.load()
    context = {
        "page": page,
        "catalogues": Catalogue.objects.filter(is_active=True).select_related("category").order_by("order", "pk"),
        "seo": _seo(request, page, f"Catalogues — {SiteSettings.load().site_name}", page.heading[:160], page.banner_image),
        "body_page": "catalogues",
    }
    return render(request, "pages/catalogues.html", context)


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
