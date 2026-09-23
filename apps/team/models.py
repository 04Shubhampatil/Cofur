from django.db import models

from apps.core.images import make_thumbnail, optimise_fields
from apps.core.mixins import ActivatableModel, OrderableModel, TimeStampedModel


class TeamMember(OrderableModel, ActivatableModel, TimeStampedModel):
    name = models.CharField(max_length=120)
    designation = models.CharField(max_length=160, blank=True)
    quote = models.TextField(blank=True, help_text="Optional highlighted quote shown before the biography.")
    biography = models.TextField(blank=True, help_text="Blank lines start a new paragraph.")
    image = models.ImageField(upload_to="team/", blank=True, null=True)
    thumbnail = models.ImageField(upload_to="team/thumbs/", blank=True, null=True, editable=False)
    linkedin_url = models.URLField(blank=True)
    email = models.EmailField(blank=True)

    class Meta(OrderableModel.Meta):
        verbose_name = "Team member"
        indexes = [models.Index(fields=["is_active", "order"])]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        old_image = None
        if self.pk:
            old_image = TeamMember.objects.filter(pk=self.pk).values_list("image", flat=True).first()
        super().save(*args, **kwargs)
        current = self.image.name if self.image else None
        if self.image and (old_image != current or not self.thumbnail):
            optimise_fields(self, "image")
            thumb = make_thumbnail(self.image, size=(400, 400))
            if thumb:
                TeamMember.objects.filter(pk=self.pk).update(thumbnail=thumb)
                self.thumbnail.name = thumb
