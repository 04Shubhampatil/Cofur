from django.test import TestCase

# Create your tests here.
import datetime

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse

from apps.core.roles import ensure_roles
from apps.stories.models import Story

User = get_user_model()


def make_story(title, kind=Story.KIND_BLOG, status=Story.STATUS_PUBLISHED, days_ago=0, **extra):
    return Story.objects.create(
        title=title, kind=kind, status=status,
        published_at=datetime.date.today() - datetime.timedelta(days=days_ago), **extra,
    )


class StoryModelTests(TestCase):
    def test_slug_is_built_from_the_title_and_stays_unique(self):
        first = make_story("Introducing the Cove Collection")
        second = make_story("Introducing the Cove Collection")
        self.assertEqual(first.slug, "introducing-the-cove-collection")
        self.assertNotEqual(second.slug, first.slug)

    def test_summary_joins_excerpt_and_body_and_cuts_on_a_word(self):
        short = make_story("Short", excerpt="Just a line.", body="And a little more.")
        self.assertEqual(short.summary, "Just a line. And a little more.")

        long_post = make_story("Long", body=" ".join(["word"] * 200))
        self.assertTrue(long_post.summary.endswith(" […]"))
        self.assertEqual(len(long_post.summary.removesuffix(" […]").split(" ")), Story.SUMMARY_WORDS)
        # cut between words, never mid-word
        self.assertNotIn("wor […]", long_post.summary)

    def test_newest_first(self):
        old = make_story("Older", days_ago=10)
        new = make_story("Newer", days_ago=1)
        self.assertEqual(list(Story.objects.published()), [new, old])


class StoryListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        make_story("Autonomy at work", Story.KIND_BLOG, days_ago=1)
        make_story("Acoustic ceilings", Story.KIND_NEWS, days_ago=2, body="Baffles and rafts")
        make_story("Cove is here", Story.KIND_ANNOUNCEMENT, days_ago=3)
        make_story("Not finished", Story.KIND_BLOG, status=Story.STATUS_DRAFT, days_ago=0)

    def test_only_published_posts_are_listed(self):
        response = self.client.get(reverse("website:stories"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total"], 3)
        self.assertNotContains(response, "Not finished")
        self.assertContains(response, "3 Items")

    def test_filtering_by_category(self):
        response = self.client.get(reverse("website:stories"), {"kind": "news"})
        self.assertEqual(response.context["total"], 1)
        self.assertEqual([post.title for post in response.context["posts"]], ["Acoustic ceilings"])

    def test_several_categories_at_once(self):
        response = self.client.get(reverse("website:stories"), {"kind": ["news", "announcement"]})
        self.assertEqual(response.context["total"], 2)

    def test_unknown_category_is_ignored_rather_than_erroring(self):
        response = self.client.get(reverse("website:stories"), {"kind": "nonsense"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total"], 3)

    def test_search_covers_title_and_body(self):
        self.assertEqual(self.client.get(reverse("website:stories"), {"q": "cove"}).context["total"], 1)
        self.assertEqual(self.client.get(reverse("website:stories"), {"q": "baffles"}).context["total"], 1)

    def test_boxes_start_ticked_and_reflect_the_filter(self):
        all_on = self.client.get(reverse("website:stories")).context["kinds"]
        self.assertTrue(all(k["checked"] for k in all_on))
        filtered = self.client.get(reverse("website:stories"), {"kind": "news"}).context["kinds"]
        self.assertEqual([k["value"] for k in filtered if k["checked"]], ["news"])

    def test_empty_state_offers_a_way_back(self):
        response = self.client.get(reverse("website:stories"), {"q": "nothing matches this"})
        self.assertEqual(response.context["total"], 0)
        self.assertContains(response, "Show everything")


class StoryDetailTests(TestCase):
    def test_published_post_renders(self):
        post = make_story("Cove is here", body="One paragraph.\n\nAnother one.")
        response = self.client.get(post.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cove is here")
        self.assertContains(response, "Another one.")

    def test_draft_is_not_reachable(self):
        post = make_story("Secret", status=Story.STATUS_DRAFT)
        self.assertEqual(self.client.get(post.get_absolute_url()).status_code, 404)


class StoryDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.groups = ensure_roles()
        cls.admin = User.objects.create_superuser("story-admin", "s@example.com", "Admin-Pass-123!")
        cls.staffer = User.objects.create_user("story-staff", password="Staff-Pass-123!", is_staff=True)
        cls.staffer.groups.add(cls.groups["Staff"])

    def test_editor_can_write_and_publish_a_post(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("dashboard:story_create"), {
            "title": "A new bench", "kind": Story.KIND_NEWS, "status": Story.STATUS_PUBLISHED,
            "published_at": datetime.date.today().isoformat(), "body": "Details here.", "robots": "index, follow",
            # the photographs formset posts alongside the post itself
            "images-TOTAL_FORMS": 0, "images-INITIAL_FORMS": 0,
            "images-MIN_NUM_FORMS": 0, "images-MAX_NUM_FORMS": 1000,
        })
        self.assertEqual(response.status_code, 302)
        post = Story.objects.get(title="A new bench")
        self.assertEqual(post.slug, "a-new-bench")
        self.assertContains(self.client.get(reverse("website:stories")), "A new bench")

    def test_list_screen_and_delete(self):
        self.client.force_login(self.admin)
        post = make_story("Removable")
        self.assertContains(self.client.get(reverse("dashboard:story_list")), "Removable")
        self.assertEqual(self.client.post(reverse("dashboard:story_delete", args=[post.pk])).status_code, 302)
        self.assertFalse(Story.objects.filter(pk=post.pk).exists())

    def test_read_only_staff_cannot_create(self):
        self.client.force_login(self.staffer)
        self.assertEqual(self.client.get(reverse("dashboard:story_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("dashboard:story_create")).status_code, 403)


class StoryRelatedPostsTests(TestCase):
    """The 'More from COFUR' row under an article: two cards, side by side."""

    def test_shows_two_other_posts_however_many_exist(self):
        posts = [make_story(f"Post {n}", days_ago=n) for n in range(8)]
        response = self.client.get(posts[0].get_absolute_url())
        self.assertEqual(response.content.decode().count('class="story-card"'), 2)

    def test_never_includes_the_post_being_read(self):
        posts = [make_story(f"Post {n}", days_ago=n) for n in range(8)]
        response = self.client.get(posts[0].get_absolute_url())
        self.assertNotIn(posts[0].get_absolute_url(), response.content.decode().split("story-more")[1])

    def test_shows_the_one_there_is_when_only_two_posts_exist(self):
        posts = [make_story(f"Post {n}", days_ago=n) for n in range(2)]
        response = self.client.get(posts[0].get_absolute_url())
        self.assertEqual(response.content.decode().count('class="story-card"'), 1)

    def test_section_is_hidden_for_the_only_post(self):
        only = make_story("The only post")
        self.assertNotContains(self.client.get(only.get_absolute_url()), "More from COFUR")

    def test_drafts_are_never_suggested(self):
        make_story("Published one", days_ago=1)
        make_story("A draft", status=Story.STATUS_DRAFT, days_ago=2)
        current = make_story("Current", days_ago=0)
        body = self.client.get(current.get_absolute_url()).content.decode()
        self.assertIn("Published one", body)
        self.assertNotIn("A draft", body)


class RichTextTests(TestCase):
    """The body is editor HTML now, so it is rendered rather than escaped.

    That makes the allow-list the thing standing between a CMS account and a
    script tag on a public page, so these lean on the nasty cases.
    """

    def render(self, body):
        from apps.core.templatetags.cofur_tags import richtext

        return str(richtext(body))

    def test_allowed_formatting_survives(self):
        html = "<p>A <strong>bold</strong> and <em>italic</em> line.</p><h2>Heading</h2><ul><li>One</li></ul>"
        out = self.render(html)
        for fragment in ("<strong>bold</strong>", "<em>italic</em>", "<h2>Heading</h2>", "<li>One</li>"):
            self.assertIn(fragment, out)

    def test_script_tag_and_its_contents_are_dropped(self):
        out = self.render("<p>Before</p><script>alert('x')</script><p>After</p>")
        self.assertNotIn("<script", out)
        self.assertNotIn("alert", out)
        self.assertIn("<p>Before</p>", out)
        self.assertIn("<p>After</p>", out)

    def test_event_handlers_are_stripped(self):
        out = self.render('<p onclick="steal()">Text</p>')
        self.assertNotIn("onclick", out)
        self.assertNotIn("steal", out)
        self.assertIn("Text", out)

    def test_javascript_links_are_refused_but_the_words_remain(self):
        out = self.render('<p><a href="javascript:alert(1)">Click</a></p>')
        self.assertNotIn("javascript:", out)
        self.assertIn("Click", out)

    def test_ordinary_links_are_kept(self):
        out = self.render('<p><a href="https://cofur.in/about/">About</a></p>')
        self.assertIn('href="https://cofur.in/about/"', out)

    def test_iframe_is_dropped(self):
        self.assertNotIn("<iframe", self.render('<p>x</p><iframe src="https://evil.test"></iframe>'))

    def test_unknown_tags_lose_markup_but_keep_text(self):
        out = self.render("<p>Hello <marquee>there</marquee></p>")
        self.assertNotIn("marquee", out)
        self.assertIn("there", out)

    def test_plain_text_bodies_still_render_as_paragraphs(self):
        out = self.render("First para.\n\nSecond para.")
        self.assertIn("<p>First para.</p>", out)
        self.assertIn("<p>Second para.</p>", out)

    def test_plain_text_is_still_escaped(self):
        self.assertNotIn("<script", self.render("Plain <script>alert(1)</script> text"))

    def test_summary_strips_markup(self):
        post = make_story("Marked up", body="<p>Anyone can <strong>fill</strong> a room.</p>")
        self.assertNotIn("<", post.summary)
        self.assertIn("Anyone can fill a room.", post.summary)

    def test_article_page_renders_the_markup(self):
        post = make_story("Formatted", body="<p>Lead.</p><h2>Section</h2>")
        body = self.client.get(post.get_absolute_url()).content.decode()
        self.assertIn("<h2>Section</h2>", body)
        self.assertNotIn("&lt;h2&gt;", body)


class RichTextAliasTests(TestCase):
    """contenteditable emits presentational tags; they must survive as semantic ones."""

    def render(self, body):
        from apps.core.templatetags.cofur_tags import richtext

        return str(richtext(body))

    def test_b_and_i_become_strong_and_em(self):
        out = self.render("<p><b>Bold</b> and <i>italic</i></p>")
        self.assertIn("<strong>Bold</strong>", out)
        self.assertIn("<em>italic</em>", out)
        self.assertNotIn("<b>", out)

    def test_div_becomes_a_paragraph(self):
        self.assertIn("<p>Line</p>", self.render("<div>Line</div>"))

    def test_a_body_of_only_b_tags_is_detected_as_html(self):
        # looks_like_html must see the aliases too, or a bold-only body would
        # be treated as plain text and escaped
        self.assertIn("<strong>Bold</strong>", self.render("<b>Bold</b>"))


class StorySliderTests(TestCase):
    """The cover becomes a slider once a post has more photographs."""

    def setUp(self):
        self.post = make_story("Beyond Open Plan")

    def test_a_post_with_only_a_cover_has_no_slider(self):
        self.post.cover_image = "stories/cover.jpg"
        self.post.save()
        body = self.client.get(self.post.get_absolute_url()).content.decode()
        self.assertIn("story-article__cover", body)
        self.assertNotIn("data-carousel-next", body)
        self.assertNotIn("data-carousel", body)

    def test_a_post_with_no_images_renders_no_figure(self):
        self.assertNotContains(self.client.get(self.post.get_absolute_url()), "story-article__cover")

    def test_extra_images_turn_the_cover_into_a_slider(self):
        from apps.stories.models import StoryImage

        self.post.cover_image = "stories/cover.jpg"
        self.post.save()
        StoryImage.objects.create(story=self.post, image="stories/two.jpg", order=0)
        StoryImage.objects.create(story=self.post, image="stories/three.jpg", order=1)
        body = self.client.get(self.post.get_absolute_url()).content.decode()
        self.assertIn("data-carousel", body)
        self.assertIn("data-carousel-next", body)
        self.assertEqual(body.count('class="media-slide'), 3)
        self.assertEqual(body.count("data-carousel-dot"), 3)

    def test_the_cover_leads_the_slider(self):
        from apps.stories.models import StoryImage

        self.post.cover_image = "stories/cover.jpg"
        self.post.save()
        StoryImage.objects.create(story=self.post, image="stories/second.jpg", order=0)
        slides = self.post.slides()
        self.assertEqual(len(slides), 2)
        self.assertIn("cover.jpg", slides[0][0])
        self.assertIn("second.jpg", slides[1][0])

    def test_images_keep_their_order(self):
        from apps.stories.models import StoryImage

        StoryImage.objects.create(story=self.post, image="stories/b.jpg", order=1)
        StoryImage.objects.create(story=self.post, image="stories/a.jpg", order=0)
        self.assertEqual([u for u, _ in self.post.slides()], ["/media/stories/a.jpg", "/media/stories/b.jpg"])

    def test_alt_falls_back_to_the_post_title(self):
        from apps.stories.models import StoryImage

        shot = StoryImage.objects.create(story=self.post, image="stories/a.jpg")
        self.assertEqual(shot.alt_text, "Beyond Open Plan")
        shot.alt = "An open plan floor"
        self.assertEqual(shot.alt_text, "An open plan floor")

    def test_only_the_first_slide_is_exposed_to_assistive_tech(self):
        from apps.stories.models import StoryImage

        self.post.cover_image = "stories/cover.jpg"
        self.post.save()
        StoryImage.objects.create(story=self.post, image="stories/two.jpg")
        StoryImage.objects.create(story=self.post, image="stories/three.jpg")
        body = self.client.get(self.post.get_absolute_url()).content.decode()
        slides = [chunk for chunk in body.split('class="media-slide')[1:]]
        self.assertEqual(len(slides), 3)
        # exactly one visible, the other two hidden from the reading order
        active = [c for c in slides if c.startswith(" is-active")]
        hidden = [c for c in slides if 'aria-hidden="true"' in c.split("</li>")[0]]
        self.assertEqual(len(active), 1)
        self.assertEqual(len(hidden), 2)
