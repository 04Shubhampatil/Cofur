from django.test import TestCase

from apps.core.tests import make_image

from .models import TeamMember


class TeamMemberTests(TestCase):
    def test_ordering_and_active_filter(self):
        TeamMember.objects.create(name="Second", order=2)
        TeamMember.objects.create(name="First", order=1)
        TeamMember.objects.create(name="Hidden", order=0, is_active=False)
        self.assertEqual([m.name for m in TeamMember.objects.filter(is_active=True)], ["First", "Second"])

    def test_thumbnail_generated(self):
        member = TeamMember(name="Photo")
        member.image = make_image("p.jpg", size=(1200, 900), fmt="JPEG")
        member.save()
        member.refresh_from_db()
        self.assertTrue(member.thumbnail)
        self.assertEqual(str(member), "Photo")
