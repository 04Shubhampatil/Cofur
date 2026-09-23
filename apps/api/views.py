from rest_framework import mixins, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from apps.catalog.models import Category, Collection, Product
from apps.core.models import NavigationMenu, SiteSettings
from apps.enquiries.services import is_rate_limited, save_enquiry
from apps.pages.models import AboutPage, ContactPage, HomePage
from apps.team.models import TeamMember

from . import serializers


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """Published products. Filter with ?collection=<slug>, ?category=<slug>, ?featured=1, ?search=<text>."""

    lookup_field = "slug"
    serializer_class = serializers.ProductListSerializer

    def get_queryset(self):
        qs = Product.objects.published().select_related("collection", "category")
        params = self.request.query_params
        if params.get("collection"):
            qs = qs.filter(collection__slug=params["collection"])
        if params.get("category"):
            qs = qs.filter(category__slug=params["category"])
        if params.get("featured") in ("1", "true"):
            qs = qs.filter(is_featured=True)
        if params.get("search"):
            from django.db.models import Q

            term = params["search"]
            qs = qs.filter(Q(name__icontains=term) | Q(short_description__icontains=term) | Q(sku__icontains=term))
        if self.action == "retrieve":
            qs = qs.prefetch_related("images", "specifications", "feature_items", "colors")
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return serializers.ProductDetailSerializer
        return serializers.ProductListSerializer


class CollectionViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "slug"

    def get_queryset(self):
        qs = Collection.objects.filter(is_active=True).select_related("category")
        if self.request.query_params.get("category"):
            qs = qs.filter(category__slug=self.request.query_params["category"])
        return qs

    def get_serializer_class(self):
        return serializers.CollectionDetailSerializer if self.action == "retrieve" else serializers.CollectionListSerializer


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "slug"
    queryset = Category.objects.filter(is_active=True)
    serializer_class = serializers.CategorySerializer


class TeamViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TeamMember.objects.filter(is_active=True)
    serializer_class = serializers.TeamMemberSerializer


class EnquiryThrottle(AnonRateThrottle):
    scope = "enquiry"


class EnquiryViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """POST /api/enquiries/ — create an enquiry (public)."""

    serializer_class = serializers.EnquiryCreateSerializer
    permission_classes = [AllowAny]
    throttle_classes = [EnquiryThrottle]

    def create(self, request, *args, **kwargs):
        if is_rate_limited(request):
            return Response({"detail": "Too many enquiries. Please try again later."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enquiry = serializer.save()
        save_enquiry(enquiry, request, source="api")
        return Response({"ok": True, "id": enquiry.pk, "message": ContactPage.load().success_message}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([AllowAny])
def page_home(request):
    return Response(serializers.HomePageSerializer(HomePage.load(), context={"request": request}).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def page_about(request):
    return Response(serializers.AboutPageSerializer(AboutPage.load(), context={"request": request}).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def page_contact(request):
    return Response(serializers.ContactPageSerializer(ContactPage.load(), context={"request": request}).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def site_settings(request):
    return Response(serializers.SiteSettingsSerializer(SiteSettings.load(), context={"request": request}).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def navigation(request):
    data = {}
    for menu in NavigationMenu.objects.all():
        data[menu.slug] = serializers.NavigationItemSerializer(menu.top_level_items(), many=True).data
    return Response(data)
