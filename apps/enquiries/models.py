from django.db import models

from apps.core.mixins import TimeStampedModel


class Enquiry(TimeStampedModel):
    STATUS_NEW = "new"
    STATUS_CONTACTED = "contacted"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_CONVERTED = "converted"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_NEW, "New"),
        (STATUS_CONTACTED, "Contacted"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_CONVERTED, "Converted"),
        (STATUS_CLOSED, "Closed"),
    ]
    PENDING_STATUSES = [STATUS_NEW, STATUS_CONTACTED, STATUS_IN_PROGRESS]

    SOURCE_CHOICES = [
        ("contact", "Contact form"),
        ("product", "Product enquiry"),
        ("api", "API"),
        ("other", "Other"),
    ]

    name = models.CharField(max_length=150)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=40, blank=True)
    company = models.CharField(max_length=150, blank=True)
    city = models.CharField(max_length=100, blank=True)
    product = models.ForeignKey("catalog.Product", null=True, blank=True, related_name="enquiries", on_delete=models.SET_NULL)
    collection_ref = models.CharField("Collection / interest", max_length=120, blank=True, help_text="Free-text interest captured from ?collection= links.")
    message = models.TextField(blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="contact")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW, db_index=True)
    admin_notes = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Enquiry"
        verbose_name_plural = "Enquiries"
        indexes = [models.Index(fields=["status", "created_at"])]

    def __str__(self):
        return f"{self.name} ({self.email})"

    @property
    def is_pending(self):
        return self.status in self.PENDING_STATUSES
