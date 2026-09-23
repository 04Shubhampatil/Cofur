from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "website"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("enquire/", views.enquire, name="enquire"),
    path("collections/", views.collection_list, name="collection_list"),
    path("collections/<slug:slug>/", views.collection_detail, name="collection_detail"),
    path("categories/<slug:slug>/", views.category_detail, name="category_detail"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),
    # Legacy static-site URLs -> permanent redirects
    path("index.html", RedirectView.as_view(pattern_name="website:home", permanent=True)),
    path("about.html", RedirectView.as_view(pattern_name="website:about", permanent=True)),
    path("contact.html", RedirectView.as_view(pattern_name="website:contact", permanent=True, query_string=True)),
    path("enquiry.html", RedirectView.as_view(pattern_name="website:contact", permanent=True, query_string=True)),
    path("soft-seating.html", RedirectView.as_view(url="/categories/soft-seating/", permanent=True)),
    path("soft-seating-main-category.html", RedirectView.as_view(url="/categories/soft-seating/", permanent=True)),
    path("collection.html", RedirectView.as_view(url="/collections/cove/", permanent=True)),
    path("cove-collection-sub-cateogry.html", RedirectView.as_view(url="/collections/cove/", permanent=True)),
    path("cove-social.html", RedirectView.as_view(url="/products/cove-social/", permanent=True)),
    path("product-detailes.html", RedirectView.as_view(url="/products/cove-social/", permanent=True)),
]
