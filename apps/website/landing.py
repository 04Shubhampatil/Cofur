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
from django.views.decorators.http import require_http_methods

from apps.enquiries.forms import EnquiryForm
from apps.enquiries.services import is_rate_limited, save_enquiry

from .views import _enquiry_form_kwargs, _page_seo

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

CEILING_DESIGNS = [
    {"title": "Wave", "photo": "images/cofur/ceiling-wave.webp",
     "copy": "A flowing acoustic ceiling design for contemporary workplace interiors."},
    {"title": "Petal", "photo": "images/cofur/ceiling-petal.webp",
     "copy": "An organic-inspired ceiling form for visually refined commercial spaces."},
    {"title": "Blade", "photo": "images/cofur/ceiling-blade.webp",
     "copy": "A linear design direction suitable for modern commercial workplace interiors."},
    {"title": "Planks", "photo": "images/cofur/ceiling-planks.webp",
     "copy": "A layered linear ceiling concept for contemporary workplace environments."},
    {"title": "Grid", "photo": "images/cofur/ceiling-grid.webp",
     "copy": "A structured ceiling design for modern commercial interiors."},
    {"title": "Waffle", "photo": "images/cofur/ceiling-waffle.webp",
     "copy": "An architectural ceiling pattern for distinctive workplace environments."},
    {"title": "Hive", "photo": "images/cofur/ceiling-hive.webp",
     "copy": "A geometric ceiling design inspired by honeycomb forms."},
]


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
            save_enquiry(
                enquiry,
                request,
                source="product" if enquiry.product_id else "contact",
                collection_ref=interest,
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
        "seo": _page_seo(request, title, description),
        "body_page": "landing",
    }
    context.update(extra or {})
    return render(request, template, context, status=status)


@require_http_methods(["GET", "POST"])
def acoustic_wall_panels(request):
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
        extra={"panels": WALL_PANELS},
    )


@require_http_methods(["GET", "POST"])
def acoustic_ceilings(request):
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
        extra={"designs": CEILING_DESIGNS},
    )
