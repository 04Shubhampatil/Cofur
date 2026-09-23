from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "api"

router = DefaultRouter()
router.register("products", views.ProductViewSet, basename="product")
router.register("collections", views.CollectionViewSet, basename="collection")
router.register("categories", views.CategoryViewSet, basename="category")
router.register("team", views.TeamViewSet, basename="team")
router.register("enquiries", views.EnquiryViewSet, basename="enquiry")

urlpatterns = [
    path("pages/home/", views.page_home, name="page_home"),
    path("pages/about/", views.page_about, name="page_about"),
    path("pages/contact/", views.page_contact, name="page_contact"),
    path("settings/", views.site_settings, name="site_settings"),
    path("navigation/", views.navigation, name="navigation"),
    path("", include(router.urls)),
]
