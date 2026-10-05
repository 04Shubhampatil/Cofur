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
            **self.mgmt("facts"), **self.mgmt("images"),
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
            "images-TOTAL_FORMS": 1, "images-0-alt": "Reception", "images-0-kind": "carousel", "images-0-order": 0,
        })
        data["images-0-image"] = make_image("shot.jpg")
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

    def test_card_renders_its_words(self):
        self.card(title="Cove Solo", caption="Your personal sanctuary at work")
        body = self.client.get(self.project.get_absolute_url()).content.decode()
        self.assertIn('<b class="project-tile__title">Cove Solo</b>', body)
        self.assertIn("Your personal sanctuary at work", body)

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

    def test_card_fields_are_on_the_admin_form(self):
        from django.contrib.auth import get_user_model

        admin = get_user_model().objects.create_superuser("gal", "g@example.com", "Admin-Pass-123!")
        self.client.force_login(admin)
        form = self.client.get(reverse("dashboard:project_update", args=[self.project.pk])).content.decode()
        for field in ("images-__prefix__-title", "images-__prefix__-caption", "images-__prefix__-link_url"):
            self.assertIn(field, form)


class ProjectCardLinkValidationTests(TestCase):
    """A card link must lead somewhere, or be empty."""

    def form(self, url):
        from apps.dashboard.forms import ProjectImageForm

        project = make_project()
        return ProjectImageForm(
            data={"alt": "", "kind": ProjectImage.KIND_GALLERY, "title": "A card",
                  "caption": "", "link_url": url, "order": 0},
            files={"image": make_image("card.jpg")},
            instance=ProjectImage(project=project),
        )

    def test_empty_is_allowed(self):
        form = self.form("")
        self.assertTrue(form.is_valid(), form.errors)

    def test_a_real_internal_path_is_allowed(self):
        from apps.catalog.models import Category

        Category.objects.create(name="Acoustic Ceilings", slug="acoustic-ceilings")
        form = self.form("/categories/acoustic-ceilings/")
        self.assertTrue(form.is_valid(), form.errors)

    def test_a_path_that_matches_no_url_is_refused(self):
        form = self.form("/not-a-section/at-all/")
        self.assertFalse(form.is_valid())
        self.assertIn("Nothing is served at that address", str(form.errors["link_url"]))

    def test_a_real_url_with_a_missing_slug_is_refused(self):
        # the exact mistake: the category is called acoustic-ceilings
        form = self.form("/categories/acoustics/")
        self.assertFalse(form.is_valid())
        self.assertIn("no category with the address", str(form.errors["link_url"]).lower())

    def test_external_addresses_are_taken_on_trust(self):
        for url in ("https://example.test/page/", "mailto:hello@cofur.in", "tel:+919320461618"):
            with self.subTest(url=url):
                self.assertTrue(self.form(url).is_valid())

    def test_a_query_string_or_anchor_does_not_confuse_it(self):
        from apps.catalog.models import Category

        Category.objects.create(name="Phone Booth", slug="phone-booth")
        self.assertTrue(self.form("/categories/phone-booth/?from=project#top").is_valid())
