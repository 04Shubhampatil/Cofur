"""Campaign landing pages.

Two standalone marketing pages:

    /acoustic-wall-panels-for-offices/
    /acoustic-ceilings-for-offices/

These are fixed pages, not CMS pages. Their copy, photographs and links are
written into this module and the two templates, so nothing on them is edited
from the dashboard and nothing on them depends on catalogue records.

They are intentionally unreachable from the website — no navigation entry, no
header, no footer — so the only route onward is the enquiry form. That form is
the real COFUR one (same EnquiryForm, same spam checks, same dashboard inbox);
it posts back to the landing page instead of /enquire/ so a visitor who has
just converted stays on the campaign page and sees the success message there.
"""
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.views.decorators.http import require_http_methods

from apps.enquiries.forms import EnquiryForm
from apps.enquiries.services import is_rate_limited, save_enquiry
from apps.pages.landing_content import WALL_PAGE
from apps.pages.landing_content_ceilings import CEILING_PAGE
from apps.pages.models import LandingText

from .views import _enquiry_form_kwargs, _page_seo

WALL_PRODUCT_OPTIONS = [
    ("grooved-wall-panels", "Grooved Wall Panels"),
    ("printed-wall-panels", "Printed Wall Panels"),
    ("fluted-wood-wall-panels", "Fluted Wall Panels"),
]

SUCCESS_MESSAGE = "Thank you. Our team will be in touch about your project shortly."

WALL_PANELS = [
    {
        "title": "Grooved Wall Panels",
        "url": "/products/grooved-wall-panels/",
        "photo": "images/cofur/wall-grooved.webp",
        "copy": "Grooved wall panel design for corporate, institutional and hospitality "
                "interiors. Discuss available options for your space.",
    },
    {
        "title": "Printed Wall Panels",
        "url": "/products/printed-wall-panels/",
        "photo": "images/cofur/wall-printed.webp",
        "copy": "Printed wall panel design for corporate, institutional and hospitality "
                "spaces. Enquire about options for your interior project.",
    },
    {
        "title": "Fluted Wall Panels",
        "url": "/products/fluted-wood-wall-panels/",
        "photo": "images/cofur/wall-fluted.webp",
        "copy": "Vertical fluted wall panel design for corporate, institutional and "
                "hospitality interiors. Share your requirements with COFUR.",
    },
]

# Each design's "View product details" goes to that design's own product page.
# The collection page is the fallback if a design ever loses its product. Both
# destinations are editable per design in the admin panel
# (Landing pages > Ceilings > Products and designs).
CEILING_DETAILS_URL = "/collections/acoustic-ceilings/"

CEILING_DESIGNS = [
    {"title": "Wave", "photo": "images/cofur/ceiling-wave.webp", "url": "/products/wave/",
     "copy": "A flowing acoustic ceiling design for contemporary workplace interiors."},
    {"title": "Petal", "photo": "images/cofur/ceiling-petal.webp", "url": "/products/petal/",
     "copy": "An organic-inspired ceiling form for visually refined commercial spaces."},
    {"title": "Blade", "photo": "images/cofur/ceiling-blade.webp", "url": "/products/blade/",
     "copy": "A linear design direction suitable for modern commercial workplace interiors."},
    {"title": "Planks", "photo": "images/cofur/ceiling-planks.webp", "url": "/products/planks/",
     "copy": "A layered linear ceiling concept for contemporary workplace environments."},
    {"title": "Grid", "photo": "images/cofur/ceiling-grid.webp", "url": "/products/grid/",
     "copy": "A structured ceiling design for modern commercial interiors."},
    {"title": "Waffle", "photo": "images/cofur/ceiling-waffle.webp", "url": "/products/waffle/",
     "copy": "An architectural ceiling pattern for distinctive workplace environments."},
    {"title": "Hive", "photo": "images/cofur/ceiling-hive.webp", "url": "/products/hive/",
     "copy": "A geometric ceiling design inspired by honeycomb forms."},
]

# The enquiry form offers the seven designs shown on the page and nothing else.
# They are not catalogue products, so the choice is recorded as the enquiry's
# interest rather than linked to a product record.
CEILING_PRODUCT_OPTIONS = [
    (design["title"].lower(), design["title"]) for design in CEILING_DESIGNS
]


def _landing_content(page):
    """Text and photo URLs for a landing page, read from the LandingText table.

    Returns (text, images): text maps key -> string, images maps key -> URL.
    An uploaded photo wins over the static default.
    """
    text, images = {}, {}
    for row in LandingText.objects.filter(page=page):
        text[row.key] = row.value
        if row.image:
            images[row.key] = row.image.url
        elif row.default_image:
            images[row.key] = static(row.default_image)
    return text, images


def _landing_seo(request, extra, title, description):
    """The page's search listing, as edited in the admin panel.

    Each field falls back the way an editor would expect: an empty search
    listing uses the wording in this module, an empty social title or
    description reuses the search listing, no share image leaves the
    site-wide one from Settings in place, empty robots follows the site
    setting, and an empty canonical address means the page's own address.
    """
    text = extra.get("L", {})
    images = extra.get("IMG", {})
    seo = _page_seo(request, text.get("seo_title") or title, text.get("seo_description") or description)
    for row_key, seo_key in (
        ("seo_keywords", "keywords"),
        ("seo_og_title", "og_title"),
        ("seo_og_description", "og_description"),
    ):
        if text.get(row_key):
            seo[seo_key] = text[row_key]
    if images.get("img_seo_share"):
        seo["og_image"] = request.build_absolute_uri(images["img_seo_share"])
    if text.get("seo_robots"):
        seo["robots"] = text["seo_robots"]
    if text.get("seo_canonical"):
        # og:url is built from this too, so a path has to become a full address.
        seo["canonical"] = request.build_absolute_uri(text["seo_canonical"])
    return seo


def _render(request, *, template, interest, title, description, extra=None):
    """Shared GET/POST handling for a landing page.

    ``interest`` is stored on the enquiry as its free-text interest, so the
    dashboard shows which campaign page a lead arrived from.
    """
    status = 200

    if request.method == "POST":
        form = EnquiryForm(request.POST)
        limited = is_rate_limited(request)
        if form.is_valid() and not limited:
            enquiry = form.save(commit=False)
            # A fixed product list (wall panels page) is not a catalogue lookup, so
            # the chosen product is recorded in the interest field instead.
            options = dict((extra or {}).get("product_options", []))
            chosen = request.POST.get("product_slug", "")
            interest_text = f"{interest} · {options[chosen]}" if chosen in options else interest
            save_enquiry(
                enquiry,
                request,
                source="product" if enquiry.product_id else "contact",
                collection_ref=interest_text,
            )
            return redirect(f"{request.path}?sent=1#enquiry")
        if limited:
            # These pages carry no site chrome, so there is nowhere for a
            # Django message to appear: the reason has to go on the form.
            form.add_error(None, "Too many enquiries from your connection. Please try again later.")
            status = 429
        else:
            status = 400
    else:
        form = EnquiryForm(**_enquiry_form_kwargs(request))

    context = {
        "form": form,
        "interest": interest,
        "success_message": SUCCESS_MESSAGE,
        "seo": _landing_seo(request, extra or {}, title, description),
        "body_page": "landing",
    }
    context.update(extra or {})
    return render(request, template, context, status=status)


@require_http_methods(["GET", "POST"])
def acoustic_wall_panels(request):
    text, images = _landing_content(WALL_PAGE)
    return _render(
        request,
        template="pages/landing/acoustic-wall-panels.html",
        interest="Acoustic Wall Panels (campaign page)",
        title="Acoustic Wall Panels for Offices | COFUR India",
        description=(
            "Explore COFUR acoustic wall panel designs for commercial offices, meeting rooms "
            "and workplace interiors. Enquire about grooved, printed and fluted wall panels "
            "for your project."
        ),
        extra={
            "panels": [
                dict(entry, copy=text[f"product_{i}_copy"], photo_url=images[f"img_product_{i}"])
                for i, entry in enumerate(WALL_PANELS, start=1)
            ],
            "product_options": WALL_PRODUCT_OPTIONS,
            "L": text,
            "IMG": images,
            "success_message": text.get("form_success", SUCCESS_MESSAGE),
        },
    )


@require_http_methods(["GET", "POST"])
def acoustic_ceilings(request):
    text, images = _landing_content(CEILING_PAGE)
    return _render(
        request,
        template="pages/landing/acoustic-ceilings.html",
        interest="Acoustic Ceilings (campaign page)",
        title="Acoustic Ceilings for Commercial Offices | COFUR",
        description=(
            "Acoustic ceilings for commercial offices, corporate workplaces and modern "
            "interiors. Explore Wave, Petal, Blade, Planks, Grid, Waffle and Hive acoustic "
            "ceiling designs by COFUR."
        ),
        extra={
            "designs": [
                dict(
                    entry,
                    copy=text[f"design_{i}_copy"],
                    photo_url=images[f"img_design_{i}"],
                    url=text.get(f"design_{i}_url") or entry.get("url") or CEILING_DETAILS_URL,
                )
                for i, entry in enumerate(CEILING_DESIGNS, start=1)
            ],
            "product_options": CEILING_PRODUCT_OPTIONS,
            "L": text,
            "IMG": images,
            "success_message": text.get("form_success", SUCCESS_MESSAGE),
        },
    )
