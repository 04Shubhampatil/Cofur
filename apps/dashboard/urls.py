from django.urls import path

from .views import auth, catalog, home, navigation, pages, people, settings

app_name = "dashboard"

urlpatterns = [
    path("", home.DashboardIndexView.as_view(), name="index"),
    path("login/", auth.LoginView.as_view(), name="login"),
    path("logout/", auth.LogoutView.as_view(), name="logout"),
    path("password/", auth.PasswordChangeView.as_view(), name="password_change"),

    # Content
    path("content/home/", pages.HomePageEditView.as_view(), name="page_home"),
    path("content/about/", pages.AboutPageEditView.as_view(), name="page_about"),
    path("content/contact/", pages.ContactPageEditView.as_view(), name="page_contact"),
    path("content/footer/", settings.FooterSettingsView.as_view(), name="footer_settings"),

    # Collections mega menu
    path("menus/collections/", navigation.MegaMenuView.as_view(), name="mega_menu"),
    path("menus/collections/add/", navigation.MegaMenuItemCreateView.as_view(), name="mega_menu_item_create"),
    path("menus/collections/reorder/", navigation.MegaMenuItemReorderView.as_view(), name="mega_menu_item_reorder"),
    path("menus/collections/<int:pk>/", navigation.MegaMenuItemUpdateView.as_view(), name="mega_menu_item_update"),
    path("menus/collections/<int:pk>/delete/", navigation.MegaMenuItemDeleteView.as_view(), name="mega_menu_item_delete"),
    path("menus/collections/<int:pk>/toggle-active/", navigation.MegaMenuItemToggleActiveView.as_view(), name="mega_menu_item_toggle_active"),
    path("menus/collections/<int:pk>/move/<slug:direction>/", navigation.MegaMenuItemMoveView.as_view(), name="mega_menu_item_move"),

    # Catalog: products
    path("products/", catalog.ProductListView.as_view(), name="product_list"),
    path("products/add/", catalog.ProductCreateView.as_view(), name="product_create"),
    path("products/<int:pk>/", catalog.ProductUpdateView.as_view(), name="product_update"),
    path("products/<int:pk>/delete/", catalog.ProductDeleteView.as_view(), name="product_delete"),
    path("products/<int:pk>/duplicate/", catalog.ProductDuplicateView.as_view(), name="product_duplicate"),
    path("products/<int:pk>/toggle-featured/", catalog.ProductToggleFeaturedView.as_view(), name="product_toggle_featured"),
    path("products/<int:pk>/toggle-publish/", catalog.ProductTogglePublishView.as_view(), name="product_toggle_publish"),
    path("products/<int:pk>/gallery/upload/", catalog.ProductGalleryUploadView.as_view(), name="product_gallery_upload"),
    path("products/images/<int:pk>/delete/", catalog.ProductImageDeleteView.as_view(), name="product_image_delete"),
    path("products/images/reorder/", catalog.ProductImageReorderView.as_view(), name="product_image_reorder"),
    path("products/reorder/", catalog.ProductReorderView.as_view(), name="product_reorder"),
    path("products/bulk/", catalog.ProductBulkActionView.as_view(), name="product_bulk"),

    # Catalog: sub-categories (Collection model)
    path("sub-categories/", catalog.CollectionListView.as_view(), name="collection_list"),
    path("sub-categories/add/", catalog.CollectionCreateView.as_view(), name="collection_create"),
    path("sub-categories/<int:pk>/", catalog.CollectionUpdateView.as_view(), name="collection_update"),
    path("sub-categories/<int:pk>/delete/", catalog.CollectionDeleteView.as_view(), name="collection_delete"),
    path("sub-categories/<int:pk>/toggle-active/", catalog.CollectionToggleActiveView.as_view(), name="collection_toggle_active"),
    path("sub-categories/reorder/", catalog.CollectionReorderView.as_view(), name="collection_reorder"),

    # Catalog: categories
    path("categories/", catalog.CategoryListView.as_view(), name="category_list"),
    path("categories/add/", catalog.CategoryCreateView.as_view(), name="category_create"),
    path("categories/<int:pk>/", catalog.CategoryUpdateView.as_view(), name="category_update"),
    path("categories/<int:pk>/delete/", catalog.CategoryDeleteView.as_view(), name="category_delete"),
    path("categories/reorder/", catalog.CategoryReorderView.as_view(), name="category_reorder"),
    path("categories/<int:pk>/toggle-active/", catalog.CategoryToggleActiveView.as_view(), name="category_toggle_active"),

    # People
    path("team/", people.TeamListView.as_view(), name="team_list"),
    path("team/add/", people.TeamCreateView.as_view(), name="team_create"),
    path("team/<int:pk>/", people.TeamUpdateView.as_view(), name="team_update"),
    path("team/<int:pk>/delete/", people.TeamDeleteView.as_view(), name="team_delete"),
    path("team/<int:pk>/toggle-active/", people.TeamToggleActiveView.as_view(), name="team_toggle_active"),
    path("team/reorder/", people.TeamReorderView.as_view(), name="team_reorder"),

    # Leads
    path("enquiries/", people.EnquiryListView.as_view(), name="enquiry_list"),
    path("enquiries/<int:pk>/", people.EnquiryDetailView.as_view(), name="enquiry_detail"),
    path("enquiries/<int:pk>/status/", people.EnquiryStatusView.as_view(), name="enquiry_status"),
    path("enquiries/<int:pk>/delete/", people.EnquiryDeleteView.as_view(), name="enquiry_delete"),

    # Settings
    path("settings/site/", settings.SiteSettingsView.as_view(), name="site_settings"),
]
