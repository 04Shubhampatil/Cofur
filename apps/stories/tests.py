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
