from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.generic import RedirectView


def robots_txt(request):
    body = f"User-agent: *\nDisallow: /{settings.ADMIN_URL}\nDisallow: /api/\nDisallow: /enquire/\n"
    return HttpResponse(body, content_type="text/plain")


urlpatterns = [
    path(settings.ADMIN_URL, include("apps.dashboard.urls", namespace="dashboard")),
    re_path(r"^dashboard/(?P<rest>.*)$", RedirectView.as_view(url=f"/{settings.ADMIN_URL}%(rest)s", permanent=True, query_string=True)),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("api/", include("apps.api.urls", namespace="api")),
    path("", include("apps.website.urls", namespace="website")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
