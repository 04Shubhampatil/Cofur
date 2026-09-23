from rest_framework import serializers

from apps.catalog.models import Category, Collection, Product, ProductColor, ProductFeature, ProductImage, ProductSpecification
from apps.core.models import NavigationItem, SiteSettings
from apps.enquiries.models import Enquiry
from apps.pages.models import AboutPage, ContactPage, Differentiator, HomeHeroSlide, HomePage, HomeStatementLine
from apps.team.models import TeamMember


class ImageField(serializers.ImageField):
    """Absolute URL or null."""

    def to_representation(self, value):
        if not value:
            return None
        return super().to_representation(value)


class SEOSerializerMixin(serializers.Serializer):
    seo = serializers.SerializerMethodField()

    def get_seo(self, obj):
        return {
            "title": obj.seo_title,
            "description": obj.meta_description,
            "keywords": obj.meta_keywords,
            "og_title": obj.og_title,
            "og_description": obj.og_description,
            "og_image": self._abs(obj.og_image),
            "canonical_url": obj.canonical_url,
            "robots": obj.robots,
        }

    def _abs(self, image):
        if not image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(image.url) if request else image.url


class CategorySerializer(SEOSerializerMixin, serializers.ModelSerializer):
    thumbnail_image = ImageField(read_only=True)
    banner_image = ImageField(read_only=True)
    url = serializers.CharField(source="get_absolute_url", read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "subtitle", "description", "thumbnail_image", "banner_image", "link_override", "url", "order", "is_active", "show_on_home", "seo"]


class CollectionListSerializer(SEOSerializerMixin, serializers.ModelSerializer):
    image = ImageField(read_only=True)
    banner_image = ImageField(read_only=True)
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    url = serializers.CharField(source="get_absolute_url", read_only=True)
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Collection
        fields = ["id", "name", "slug", "category", "tagline", "description", "image", "banner_image", "link_override", "url", "order", "is_active", "product_count", "seo"]


class ProductImageSerializer(serializers.ModelSerializer):
    image = ImageField(read_only=True)
    video_file = serializers.FileField(read_only=True)
    embed_url = serializers.CharField(read_only=True)
    thumbnail = ImageField(read_only=True)

    class Meta:
        model = ProductImage
        fields = ["id", "image", "video_file", "video_url", "embed_url", "thumbnail", "alt_text", "caption", "kind", "width", "height", "order"]


class ProductSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSpecification
        fields = ["label", "value", "order"]


class ProductFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFeature
        fields = ["text", "kind", "order"]


class ProductColorSerializer(serializers.ModelSerializer):
    swatch_image = ImageField(read_only=True)
    finish_image = ImageField(read_only=True)

    class Meta:
        model = ProductColor
        fields = ["name", "hex_code", "swatch_image", "finish_image", "order"]


class ProductListSerializer(serializers.ModelSerializer):
    main_image = ImageField(read_only=True)
    thumbnail = ImageField(read_only=True)
    hover_image = ImageField(read_only=True)
    collection = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    category = serializers.SlugRelatedField(slug_field="slug", read_only=True)
    url = serializers.CharField(source="get_absolute_url", read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "slug", "sku", "collection", "category", "tagline", "short_description", "main_image", "thumbnail", "hover_image", "status", "is_featured", "order", "url", "updated_at"]


class ProductDetailSerializer(SEOSerializerMixin, ProductListSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)
    features = ProductFeatureSerializer(source="feature_items", many=True, read_only=True)
    colors = ProductColorSerializer(many=True, read_only=True)
    finish_image = ImageField(read_only=True)
    related_products = ProductListSerializer(source="get_related_products", many=True, read_only=True)
    dimensions = serializers.SerializerMethodField()
    areas = serializers.SerializerMethodField()
    materials = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            "description", "main_image_alt", "finish_image", "seating_capacity", "areas", "materials", "fabric_intro",
            "dimensions", "images", "specifications", "features", "colors", "related_products",
            "cta_text", "cta_url", "enquiry_title", "enquiry_text", "created_at", "seo",
        ]

    def get_dimensions(self, obj):
        return [{"label": label, "value": value, "unit": unit} for label, value, unit in obj.dimension_rows()]

    def get_areas(self, obj):
        return [line.strip() for line in obj.areas.splitlines() if line.strip()]

    def get_materials(self, obj):
        return [line.strip() for line in obj.materials.splitlines() if line.strip()]


class CollectionDetailSerializer(CollectionListSerializer):
    products = serializers.SerializerMethodField()
    banner_mobile_image = ImageField(read_only=True)

    class Meta(CollectionListSerializer.Meta):
        fields = CollectionListSerializer.Meta.fields + ["heading", "banner_mobile_image", "banner_mobile_alt", "banner_alt", "products"]

    def get_products(self, obj):
        return ProductListSerializer(obj.published_products(), many=True, context=self.context).data


class TeamMemberSerializer(serializers.ModelSerializer):
    image = ImageField(read_only=True)
    thumbnail = ImageField(read_only=True)

    class Meta:
        model = TeamMember
        fields = ["id", "name", "designation", "quote", "biography", "image", "thumbnail", "linkedin_url", "order"]


class HeroSlideSerializer(serializers.ModelSerializer):
    image = ImageField(read_only=True)
    mobile_image = ImageField(read_only=True)

    class Meta:
        model = HomeHeroSlide
        fields = ["image", "mobile_image", "mobile_alt", "alt_text", "order"]


class StatementLineSerializer(serializers.ModelSerializer):
    image = ImageField(read_only=True)

    class Meta:
        model = HomeStatementLine
        fields = ["verb", "text", "image", "alt_text", "order"]


class DifferentiatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Differentiator
        fields = ["heading", "order"]


class HomePageSerializer(SEOSerializerMixin, serializers.ModelSerializer):
    hero_slides = serializers.SerializerMethodField()
    statement_lines = serializers.SerializerMethodField()
    featured_products = serializers.SerializerMethodField()
    differentiators = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    why_image = ImageField(read_only=True)

    class Meta:
        model = HomePage
        exclude = ["seo_title", "meta_description", "meta_keywords", "og_title", "og_description", "og_image", "canonical_url", "robots"]

    def get_hero_slides(self, obj):
        return HeroSlideSerializer(obj.hero_slides.filter(is_active=True), many=True, context=self.context).data

    def get_statement_lines(self, obj):
        return StatementLineSerializer(obj.statement_lines.filter(is_active=True), many=True, context=self.context).data

    def get_featured_products(self, obj):
        return ProductListSerializer(obj.featured_products(), many=True, context=self.context).data

    def get_differentiators(self, obj):
        return DifferentiatorSerializer(obj.differentiators.filter(is_active=True), many=True, context=self.context).data

    def get_categories(self, obj):
        return CategorySerializer(Category.objects.filter(is_active=True, show_on_home=True), many=True, context=self.context).data


class AboutPageSerializer(SEOSerializerMixin, serializers.ModelSerializer):
    team = serializers.SerializerMethodField()
    hero_image = ImageField(read_only=True)
    hero_mobile_image = ImageField(read_only=True)
    sustainability_image = ImageField(read_only=True)
    india_image = ImageField(read_only=True)

    class Meta:
        model = AboutPage
        exclude = ["seo_title", "meta_description", "meta_keywords", "og_title", "og_description", "og_image", "canonical_url", "robots"]

    def get_team(self, obj):
        return TeamMemberSerializer(TeamMember.objects.filter(is_active=True), many=True, context=self.context).data


class ContactPageSerializer(SEOSerializerMixin, serializers.ModelSerializer):
    banner_image = ImageField(read_only=True)
    banner_mobile_image = ImageField(read_only=True)

    class Meta:
        model = ContactPage
        exclude = ["seo_title", "meta_description", "meta_keywords", "og_title", "og_description", "og_image", "canonical_url", "robots"]


class NavigationItemSerializer(serializers.ModelSerializer):
    url = serializers.CharField(source="get_url", read_only=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = NavigationItem
        fields = ["label", "url", "link_type", "open_in_new_tab", "css_class", "order", "children"]

    def get_children(self, obj):
        return NavigationItemSerializer(obj.active_children(), many=True).data


class SiteSettingsSerializer(serializers.ModelSerializer):
    logo = ImageField(read_only=True)
    logo_light = ImageField(read_only=True)
    favicon = ImageField(read_only=True)

    class Meta:
        model = SiteSettings
        fields = [
            "site_name", "tagline", "logo", "logo_light", "favicon", "contact_email", "whatsapp_number", "address",
            "google_maps_url", "footer_eyebrow", "footer_title", "footer_primary_cta_text",
            "footer_primary_cta_url", "footer_secondary_cta_text", "footer_secondary_cta_url", "copyright_text",
            "linkedin_url", "instagram_url", "twitter_url",
        ]


class EnquiryCreateSerializer(serializers.ModelSerializer):
    product = serializers.SlugRelatedField(slug_field="slug", queryset=Product.objects.published(), required=False, allow_null=True)
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)  # honeypot

    class Meta:
        model = Enquiry
        fields = ["id", "name", "email", "phone", "company", "city", "product", "collection_ref", "message", "website", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_website(self, value):
        if value:
            raise serializers.ValidationError("Spam detected.")
        return value

    def validate_message(self, value):
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError("Please tell us a little more about your requirement.")
        return value

    def create(self, validated_data):
        validated_data.pop("website", None)
        return super().create(validated_data)
