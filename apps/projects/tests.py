import datetime

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse

from apps.core.roles import ensure_roles
from apps.core.tests import make_image
from apps.projects.models import Project, ProjectFact, ProjectImage

User = get_user_model()


def make_project(title="Emagine Office", status=Project.STATUS_PUBLISHED, **extra):
    return Project.objects.create(title=title, status=status, **extra)


class ProjectModelTests(TestCase):
    def test_slug_is_built_from_the_title_and_stays_unique(self):
        first = make_project("Emagine Office")
        second = make_project("Emagine Office")
        self.assertEqual(first.slug, "emagine-office")
        self.assertNotEqual(second.slug, first.slug)

    def test_published_queryset_excludes_drafts(self):
        live = make_project("Live one")
        make_project("Hidden one", status=Project.STATUS_DRAFT)
        self.assertEqual(list(Project.objects.published()), [live])

    def test_images_split_by_kind(self):
        project = make_project()
        ProjectImage.objects.create(project=project, image="projects/a.jpg", kind=ProjectImage.KIND_CAROUSEL, order=0)
        ProjectImage.objects.create(project=project, image="projects/b.jpg", kind=ProjectImage.KIND_GALLERY, order=1)
        self.assertEqual(project.carousel_images().count(), 1)
        self.assertEqual(project.gallery_images().count(), 1)

    def test_lead_image_prefers_the_carousel_then_the_cover(self):
        project = make_project()
        project.cover_image = "projects/cover.jpg"
        project.save()
        self.assertEqual(project.lead_image.name, "projects/cover.jpg")
        ProjectImage.objects.create(project=project, image="projects/first.jpg", kind=ProjectImage.KIND_CAROUSEL)
        self.assertEqual(project.lead_image.name, "projects/first.jpg")

    def test_image_alt_falls_back_to_the_project_title(self):
        project = make_project("Yandex Office")
        shot = ProjectImage.objects.create(project=project, image="projects/a.jpg")
        self.assertEqual(shot.alt_text, "Yandex Office")
        shot.alt = "A reception desk"
        self.assertEqual(shot.alt_text, "A reception desk")

    def test_facts_keep_their_order(self):
        project = make_project()
        ProjectFact.objects.create(project=project, label="Completed", value="2026", order=1)
        ProjectFact.objects.create(project=project, label="Client", value="Emagine", order=0)
        self.assertEqual([f.label for f in project.facts.all()], ["Client", "Completed"])


class ProjectPageTests(TestCase):
    def test_listing_shows_published_projects_only(self):
        make_project("Live one")
        make_project("Hidden one", status=Project.STATUS_DRAFT)
        body = self.client.get(reverse("website:projects")).content.decode()
        self.assertIn("Live one", body)
        self.assertNotIn("Hidden one", body)

    def test_card_links_to_the_project(self):
        project = make_project()
        self.assertContains(self.client.get(reverse("website:projects")), f'href="{project.get_absolute_url()}"')

    def test_draft_detail_is_not_reachable(self):
        draft = make_project("Hidden one", status=Project.STATUS_DRAFT)
        self.assertEqual(self.client.get(draft.get_absolute_url()).status_code, 404)

    def test_detail_renders_the_four_blocks(self):
        project = make_project(
            body_heading="An office built around focus",
            body="<p>Lead.</p><h2>Supplied</h2>",
            gallery_heading="More photographs",
        )
        ProjectFact.objects.create(project=project, label="Client", value="Emagine")
        ProjectImage.objects.create(project=project, image="projects/a.jpg", kind=ProjectImage.KIND_CAROUSEL)
        ProjectImage.objects.create(project=project, image="projects/b.jpg", kind=ProjectImage.KIND_GALLERY)
        body = self.client.get(project.get_absolute_url()).content.decode()
        self.assertIn("Emagine Office", body)          # heading
        self.assertIn("media-carousel", body)          # carousel
        self.assertIn("Client", body)                  # facts panel
        self.assertIn("An office built around focus", body)
        self.assertIn("<h2>Supplied</h2>", body)       # body is rendered, not escaped
        self.assertIn("More photographs", body)
        self.assertIn("project-tiles", body)          # gallery rail

    def test_body_is_sanitised_like_a_post(self):
        project = make_project(body='<p>Fine</p><script>alert(1)</script>')
        body = self.client.get(project.get_absolute_url()).content.decode()
        self.assertIn("Fine", body)
        self.assertNotIn("alert(1)", body)

    def test_carousel_arrows_only_appear_with_more_than_one_shot(self):
        project = make_project()
        ProjectImage.objects.create(project=project, image="projects/a.jpg", kind=ProjectImage.KIND_CAROUSEL)
        self.assertNotContains(self.client.get(project.get_absolute_url()), "data-carousel-next")
        ProjectImage.objects.create(project=project, image="projects/b.jpg", kind=ProjectImage.KIND_CAROUSEL)
        self.assertContains(self.client.get(project.get_absolute_url()), "data-carousel-next")

    def test_a_projects_nav_item_resolves_to_the_listing(self):
        from apps.core.models import NavigationItem, NavigationMenu

        # this TestCase does not seed, so build the one row the assertion needs
        menu = NavigationMenu.objects.create(name="Header", slug="header")
        item = NavigationItem.objects.create(
            menu=menu, label="Projects", link_type="internal", internal_page="website:projects"
        )
        self.assertEqual(item.get_url(), "/projects/")
        self.assertContains(self.client.get(reverse("website:projects")), 'href="/projects/"')


class ProjectDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.groups = ensure_roles()
        cls.superuser = User.objects.create_superuser("padmin", "p@example.com", "Admin-Pass-123!")
        cls.staffer = User.objects.create_user("pstaff", password="Staff-Pass-123!", is_staff=True)
        cls.staffer.groups.add(cls.groups["Staff"])

    def setUp(self):
        self.client.force_login(self.superuser)
        self.project = make_project()

    def mgmt(self, prefix):
        return {
            f"{prefix}-TOTAL_FORMS": 0, f"{prefix}-INITIAL_FORMS": 0,
            f"{prefix}-MIN_NUM_FORMS": 0, f"{prefix}-MAX_NUM_FORMS": 1000,
        }

    def payload(self, **extra):
        data = {
            "title": "Yandex Office", "slug": "", "status": "published", "order": 0,
            "studio": "nefa architects", "cover_alt": "", "body_heading": "", "body": "",
            "gallery_heading": "", "robots": "index, follow",
            **self.mgmt("facts"), **self.mgmt("carousel"), **self.mgmt("images"),
        }
        data.update(extra)
        return data

    def test_list_renders(self):
        response = self.client.get(reverse("dashboard:project_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Emagine Office")

    def test_create_with_inline_facts_and_images(self):
        data = self.payload()
        data.update({
            "facts-TOTAL_FORMS": 1, "facts-0-label": "Client", "facts-0-value": "Yandex", "facts-0-order": 0,
            # the section supplies the kind now, so the row never names it
            "carousel-TOTAL_FORMS": 1, "carousel-0-alt": "Reception", "carousel-0-order": 0,
        })
        data["carousel-0-image"] = make_image("shot.jpg")
        response = self.client.post(reverse("dashboard:project_create"), data)
        self.assertEqual(response.status_code, 302, response.context["form"].errors if response.context else "")
        created = Project.objects.get(slug="yandex-office")
        self.assertEqual(created.facts.count(), 1)
        self.assertEqual(created.carousel_images().count(), 1)
        self.addCleanup(lambda: [i.image.delete(save=False) for i in created.images.all()])

    def test_nothing_is_written_when_a_formset_row_is_invalid(self):
        data = self.payload(title="Should Not Exist")
        data.update({"facts-TOTAL_FORMS": 1, "facts-0-label": "", "facts-0-value": "", "facts-0-order": 0})
        # a row with a value but no label is incomplete, not empty
        data["facts-0-value"] = "Orphan value"
        response = self.client.post(reverse("dashboard:project_create"), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Project.objects.filter(title="Should Not Exist").exists())

    def test_update_keeps_the_project(self):
        data = self.payload(title="Renamed", slug=self.project.slug)
        response = self.client.post(reverse("dashboard:project_update", args=[self.project.pk]), data)
        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, "Renamed")

    def test_toggle_publish_flips_the_status(self):
        self.client.post(reverse("dashboard:project_toggle_publish", args=[self.project.pk]))
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.STATUS_DRAFT)
        self.client.post(reverse("dashboard:project_toggle_publish", args=[self.project.pk]))
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.STATUS_PUBLISHED)

    def test_delete(self):
        self.client.post(reverse("dashboard:project_delete", args=[self.project.pk]))
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())

    def test_staff_cannot_edit(self):
        self.client.force_login(self.staffer)
        self.assertEqual(self.client.get(reverse("dashboard:project_update", args=[self.project.pk])).status_code, 403)

    def test_editor_role_can_manage_projects(self):
        editor = User.objects.create_user("peditor", password="Editor-Pass-123!", is_staff=True)
        editor.groups.add(self.groups["Editor"])
        self.client.force_login(editor)
        self.assertEqual(self.client.get(reverse("dashboard:project_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:project_create")).status_code, 200)


class ProjectsPageTests(TestCase):
    """The listing page itself: title, banner, intro and empty message."""

    @classmethod
    def setUpTestData(cls):
        cls.groups = ensure_roles()
        cls.superuser = User.objects.create_superuser("ppage", "pp@example.com", "Admin-Pass-123!")

    def test_defaults_render_without_configuration(self):
        response = self.client.get(reverse("website:projects"))
        self.assertContains(response, "Projects")
        self.assertContains(response, "The first project is on its way.")

    def test_title_heading_and_empty_message_are_editable(self):
        from apps.pages.models import ProjectsPage

        page = ProjectsPage.load()
        page.page_title = "Our work"
        page.heading = "Spaces we have furnished"
        page.empty_message = "Nothing published yet."
        page.save()
        body = self.client.get(reverse("website:projects")).content.decode()
        self.assertIn("Our work", body)
        self.assertIn("Spaces we have furnished", body)
        self.assertIn("Nothing published yet.", body)

    def test_banner_replaces_the_plain_head(self):
        from apps.pages.models import ProjectsPage

        page = ProjectsPage.load()
        page.banner_image = make_image("projects-banner.jpg")
        page.save()
        self.addCleanup(page.banner_image.delete, save=False)
        body = self.client.get(reverse("website:projects")).content.decode()
        self.assertIn("projects-hero", body)
        self.assertNotIn("projects-head", body)

    def test_empty_message_is_replaced_by_the_cards(self):
        make_project("A real project")
        body = self.client.get(reverse("website:projects")).content.decode()
        self.assertIn("A real project", body)
        self.assertNotIn("The first project is on its way.", body)

    def test_admin_screen_exposes_the_fields(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse("dashboard:page_projects"))
        self.assertEqual(response.status_code, 200)
        for field in ("page_title", "banner_image", "heading", "empty_message"):
            self.assertContains(response, f'name="{field}"')

    def test_editor_role_can_reach_the_screen(self):
        editor = User.objects.create_user("ppeditor", password="Editor-Pass-123!", is_staff=True)
        editor.groups.add(self.groups["Editor"])
        self.client.force_login(editor)
        self.assertEqual(self.client.get(reverse("dashboard:page_projects")).status_code, 200)


class ProjectGalleryCardTests(TestCase):
    """The gallery row is a rail of cards, each with its own words and link."""

    def setUp(self):
        self.project = make_project(gallery_heading="Across the campus")

    def card(self, **extra):
        return ProjectImage.objects.create(
            project=self.project, image="projects/a.jpg", kind=ProjectImage.KIND_GALLERY, **extra
        )

    def test_card_renders_its_name_without_its_caption(self):
        """Cards carry names only; a caption stored on the card is not shown."""
        self.card(title="Cove Solo", caption="Your personal sanctuary at work")
        body = self.client.get(self.project.get_absolute_url()).content.decode()
        self.assertIn('<b class="project-tile__title">Cove Solo</b>', body)
        self.assertNotIn("Your personal sanctuary at work", body)

    def test_the_name_sits_under_the_picture(self):
        self.card(title="Cove Solo")
        body = self.client.get(self.project.get_absolute_url()).content.decode()
        tile = body.split('<li class="project-tile">')[1].split("</li>")[0]
        self.assertLess(tile.index("project-tile__media"), tile.index("project-tile__title"))

    def test_a_card_with_a_link_is_clickable(self):
        self.card(title="Cove Solo", link_url="/collections/cove/")
        body = self.client.get(self.project.get_absolute_url()).content.decode()
        self.assertIn('href="/collections/cove/" class="project-tile__inner"', body)

    def test_a_card_without_a_link_is_not_an_anchor(self):
        self.card(title="Just a photograph")
        body = self.client.get(self.project.get_absolute_url()).content.decode()
        tile = body.split('<li class="project-tile">')[1].split("</li>")[0]
        self.assertIn('<div class="project-tile__inner">', tile)
        self.assertNotIn("<a ", tile)

    def test_the_row_is_a_rail_with_arrows(self):
        self.card(title="One")
        self.card(title="Two")
        body = self.client.get(self.project.get_absolute_url()).content.decode()
        self.assertIn("range-rail__track project-tiles", body)
        self.assertIn("data-rail-prev", body)
        self.assertIn("data-rail-next", body)

    def test_carousel_images_are_not_turned_into_cards(self):
        ProjectImage.objects.create(
            project=self.project, image="projects/c.jpg", kind=ProjectImage.KIND_CAROUSEL, title="Should not show"
        )
        body = self.client.get(self.project.get_absolute_url()).content.decode()
        self.assertNotIn("Should not show", body)

    def test_the_cards_are_one_multi_select(self):
        from django.contrib.auth import get_user_model

        admin = get_user_model().objects.create_superuser("gal", "g@example.com", "Admin-Pass-123!")
        self.client.force_login(admin)
        form = self.client.get(reverse("dashboard:project_update", args=[self.project.pk])).content.decode()
        self.assertIn('name="cards"', form)
        self.assertIn("data-multiselect", form)
        # the per-row card editor is gone entirely
        self.assertNotIn("images-__prefix__", form)



class ProjectImageSectionTests(TestCase):
    """Carousel and cards are separate sections, and the section sets the kind."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("psec", "s@example.com", "Admin-Pass-123!")

    def setUp(self):
        self.client.force_login(self.admin)
        self.project = make_project()
        self.url = reverse("dashboard:project_update", args=[self.project.pk])

    def mgmt(self, prefix, total=0, initial=0):
        return {
            f"{prefix}-TOTAL_FORMS": total, f"{prefix}-INITIAL_FORMS": initial,
            f"{prefix}-MIN_NUM_FORMS": 0, f"{prefix}-MAX_NUM_FORMS": 1000,
        }

    def post(self, **extra):
        data = {
            "title": self.project.title, "slug": self.project.slug, "status": "published",
            "order": 0, "studio": "", "cover_alt": "", "body_heading": "", "body": "",
            "gallery_heading": "", "robots": "index, follow",
            **self.mgmt("facts"), **self.mgmt("carousel"), **self.mgmt("images"),
        }
        data.update(extra)
        return self.client.post(self.url, data)

    def test_each_section_stamps_its_own_kind(self):
        from apps.catalog.models import Product

        product = Product.objects.create(name="Cove Solo", status=Product.STATUS_PUBLISHED)
        response = self.post(**{
            **self.mgmt("carousel", total=1),
            "carousel-0-alt": "Wide shot", "carousel-0-order": 0, "carousel-0-image": make_image("c.jpg"),
            **self.mgmt("images", total=1),
            "cards": [product.pk],
        })
        self.assertEqual(response.status_code, 302, response.context["form"].errors if response.context else "")
        self.addCleanup(lambda: [i.image.delete(save=False) for i in self.project.images.all() if i.image])
        self.assertEqual(self.project.carousel_images().count(), 1)
        self.assertEqual(self.project.gallery_images().count(), 1)
        self.assertEqual(self.project.carousel_images().first().alt, "Wide shot")
        self.assertEqual(self.project.gallery_images().first().product, product)

    def test_each_section_lists_only_its_own_rows(self):
        ProjectImage.objects.create(
            project=self.project, image="projects/c.jpg", kind=ProjectImage.KIND_CAROUSEL, alt="Carousel one"
        )
        ProjectImage.objects.create(
            project=self.project, image="projects/g.jpg", kind=ProjectImage.KIND_GALLERY, title="Card one"
        )
        body = self.client.get(self.url).content.decode()
        self.assertIn("Carousel photographs", body)
        self.assertIn("More from this project", body)
        # one row apiece: neither section may show the other's picture
        self.assertIn('name="carousel-0-alt"', body)
        self.assertNotIn('name="carousel-1-alt"', body)
        self.assertIn('name="cards"', body)
        self.assertNotIn("images-0-", body)

    def test_the_carousel_section_drops_the_card_only_fields(self):
        body = self.client.get(self.url).content.decode()
        for name in ("title", "caption", "link_url", "product"):
            self.assertNotIn(f"carousel-__prefix__-{name}", body)

    def test_a_carousel_row_still_demands_a_picture(self):
        """The column is optional for product cards; a slide is nothing without one."""
        response = self.post(**{
            **self.mgmt("carousel", total=1),
            "carousel-0-alt": "No file attached", "carousel-0-order": 0,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.project.carousel_images().count(), 0)

    def test_kind_is_no_longer_asked_for(self):
        body = self.client.get(self.url).content.decode()
        self.assertNotIn("carousel-__prefix__-kind", body)
        self.assertNotIn("images-__prefix__-kind", body)


class ProjectCardProductTests(TestCase):
    """A card can point at a product chosen from the searchable dropdown."""

    def setUp(self):
        from apps.catalog.models import Collection, Product

        self.project = make_project(gallery_heading="More from this project")
        self.collection = Collection.objects.create(name="Cove", slug="cove")
        self.product = Product.objects.create(
            name="Cove Solo", collection=self.collection, status=Product.STATUS_PUBLISHED
        )

    def card(self, **extra):
        return ProjectImage.objects.create(
            project=self.project, image="projects/a.jpg", kind=ProjectImage.KIND_GALLERY, **extra
        )

    def test_the_card_links_to_the_chosen_product(self):
        self.card(title="Cove Solo", product=self.product)
        body = self.client.get(self.project.get_absolute_url()).content.decode()
        self.assertIn(f'href="{self.product.get_absolute_url()}" class="project-tile__inner"', body)

    def test_a_product_wins_over_a_typed_address(self):
        card = self.card(title="Cove Solo", product=self.product, link_url="/collections/cove/")
        self.assertEqual(card.card_url, self.product.get_absolute_url())

    def test_a_card_with_neither_is_still_not_a_link(self):
        self.assertEqual(self.card(title="Just a photograph").card_url, "")

    def test_a_removed_product_leaves_the_card_without_a_link(self):
        card = self.card(title="Cove Solo", product=self.product)
        self.product.delete()
        card.refresh_from_db()
        self.assertEqual(card.card_url, "")

    def test_the_dropdown_offers_published_products_and_is_searchable(self):
        from apps.catalog.models import Product

        from apps.dashboard.forms import ProjectForm

        draft = Product.objects.create(name="Not ready", collection=self.collection)
        field = ProjectForm().fields["cards"]
        self.assertIn(self.product, field.queryset)
        self.assertNotIn(draft, field.queryset)
        self.assertEqual(field.widget.attrs.get("data-multiselect"), "true")

    def test_the_card_takes_its_picture_name_and_line_from_the_product(self):
        card = self.card(product=self.product)
        self.assertEqual(card.card_title, "Cove Solo")
        self.assertEqual(card.card_caption, self.product.tagline)
        self.assertEqual(card.card_picture, self.product.card_picture)

    def test_the_card_shows_the_product_name_and_nothing_else(self):
        """The cards carry names only: the tagline belongs on the product page."""
        self.product.tagline = "Comfort better shared"
        self.product.save(update_fields=["tagline"])
        self.card(product=self.product)
        body = self.client.get(self.project.get_absolute_url()).content.decode()
        self.assertIn('<b class="project-tile__title">Cove Solo</b>', body)
        self.assertNotIn("Comfort better shared", body)
        self.assertNotIn("project-tile__caption", body)

    def test_a_product_card_needs_no_uploaded_picture(self):
        card = ProjectImage.objects.create(
            project=self.project, kind=ProjectImage.KIND_GALLERY, product=self.product
        )
        self.assertFalse(card.image)
        self.assertEqual(card.card_picture, self.product.card_picture)

    def test_a_card_written_before_products_keeps_its_own_words(self):
        card = self.card(title="Seminar Tables", caption="Teaching in the morning", link_url="/collections/cove/")
        self.assertEqual(card.card_title, "Seminar Tables")
        self.assertEqual(card.card_caption, "Teaching in the morning")
        self.assertEqual(card.card_url, "/collections/cove/")

    def test_the_chosen_order_is_offered_back_to_the_widget(self):
        from apps.dashboard.forms import ProjectForm

        second = self.card(product=self.product)
        second.order = 1
        second.save()
        form = ProjectForm(instance=self.project)
        self.assertEqual(form.fields["cards"].initial, [self.product.pk])
        self.assertEqual(form.fields["cards"].widget.attrs["data-selected-order"], str(self.product.pk))


class ProjectCardMultiSelectTests(TestCase):
    """One list of products replaces the row-per-card editor."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("pmulti", "m@example.com", "Admin-Pass-123!")

    def setUp(self):
        from apps.catalog.models import Collection, Product

        self.client.force_login(self.admin)
        self.project = make_project()
        self.url = reverse("dashboard:project_update", args=[self.project.pk])
        self.collection = Collection.objects.create(name="Cove", slug="cove")
        self.products = {
            name: Product.objects.create(name=name, collection=self.collection, status=Product.STATUS_PUBLISHED)
            for name in ("Cove Solo", "Cove Duo", "Cove Team", "Grove Trio")
        }

    def mgmt(self, prefix):
        return {
            f"{prefix}-TOTAL_FORMS": 0, f"{prefix}-INITIAL_FORMS": 0,
            f"{prefix}-MIN_NUM_FORMS": 0, f"{prefix}-MAX_NUM_FORMS": 1000,
        }

    def post(self, names):
        data = {
            "title": self.project.title, "slug": self.project.slug, "status": "published",
            "order": 0, "studio": "", "cover_alt": "", "body_heading": "", "body": "",
            "gallery_heading": "", "robots": "index, follow",
            "cards": [self.products[n].pk for n in names],
            **self.mgmt("facts"), **self.mgmt("carousel"),
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302, response.context["form"].errors if response.context else "")
        return response

    def card_names(self):
        return [row.product.name for row in self.project.gallery_images().order_by("order", "pk")]

    def test_several_products_are_chosen_at_once(self):
        self.post(["Cove Solo", "Cove Duo", "Cove Team"])
        self.assertEqual(self.card_names(), ["Cove Solo", "Cove Duo", "Cove Team"])

    def test_the_order_chosen_is_the_order_shown(self):
        self.post(["Grove Trio", "Cove Solo", "Cove Duo"])
        self.assertEqual(self.card_names(), ["Grove Trio", "Cove Solo", "Cove Duo"])
        self.assertEqual([r.order for r in self.project.gallery_images().order_by("order")], [0, 1, 2])

    def test_reordering_the_list_reorders_the_cards(self):
        self.post(["Cove Solo", "Cove Duo"])
        self.post(["Cove Duo", "Cove Solo"])
        self.assertEqual(self.card_names(), ["Cove Duo", "Cove Solo"])

    def test_dropping_a_product_removes_its_card(self):
        self.post(["Cove Solo", "Cove Duo", "Cove Team"])
        self.post(["Cove Solo", "Cove Team"])
        self.assertEqual(self.card_names(), ["Cove Solo", "Cove Team"])

    def test_clearing_the_list_removes_every_card(self):
        self.post(["Cove Solo", "Cove Duo"])
        self.post([])
        self.assertEqual(self.card_names(), [])

    def test_a_kept_product_keeps_its_row(self):
        """Re-saving must not churn rows, or the cards lose their identity."""
        self.post(["Cove Solo", "Cove Duo"])
        pks = {row.product_id: row.pk for row in self.project.gallery_images()}
        self.post(["Cove Duo", "Cove Solo"])
        self.assertEqual({row.product_id: row.pk for row in self.project.gallery_images()}, pks)

    def test_a_duplicate_left_by_the_old_editor_collapses(self):
        for order in (0, 1):
            ProjectImage.objects.create(
                project=self.project, kind=ProjectImage.KIND_GALLERY,
                product=self.products["Cove Team"], order=order,
            )
        self.assertEqual(self.project.gallery_images().count(), 2)
        self.post(["Cove Team"])
        self.assertEqual(self.card_names(), ["Cove Team"])

    def test_the_carousel_is_untouched_by_a_card_edit(self):
        slide = ProjectImage.objects.create(
            project=self.project, image="projects/c.jpg", kind=ProjectImage.KIND_CAROUSEL, alt="Slide"
        )
        self.post(["Cove Solo"])
        self.assertTrue(ProjectImage.objects.filter(pk=slide.pk).exists())
        self.assertEqual(self.project.carousel_images().count(), 1)

    def test_a_card_without_a_product_is_left_alone(self):
        """Hand-written cards predate the picker and are not in the list."""
        legacy = ProjectImage.objects.create(
            project=self.project, image="projects/g.jpg", kind=ProjectImage.KIND_GALLERY,
            title="Seminar Tables", link_url="/collections/cove/", order=9,
        )
        self.post(["Cove Solo"])
        legacy.refresh_from_db()
        self.assertEqual(legacy.title, "Seminar Tables")
