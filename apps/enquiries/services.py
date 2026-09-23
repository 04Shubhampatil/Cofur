"""Enquiry creation helpers shared by the website form and the REST API."""
import logging

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail

from .models import Enquiry

logger = logging.getLogger(__name__)

RATE_LIMIT = 8  # submissions
RATE_WINDOW = 60 * 60  # per hour, per IP


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    return request.META.get("REMOTE_ADDR")


def is_rate_limited(request):
    ip = client_ip(request) or "unknown"
    key = f"enquiry-rate:{ip}"
    count = cache.get(key, 0)
    if count >= RATE_LIMIT:
        return True
    cache.set(key, count + 1, RATE_WINDOW)
    return False


def save_enquiry(enquiry: Enquiry, request=None, source="contact", collection_ref=""):
    enquiry.source = source
    if collection_ref and not enquiry.collection_ref:
        enquiry.collection_ref = collection_ref[:120]
    if request is not None:
        enquiry.ip_address = client_ip(request)
        enquiry.user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]
    enquiry.save()
    notify_admins(enquiry)
    return enquiry


def notify_admins(enquiry):
    recipient = settings.ENQUIRY_NOTIFICATION_EMAIL
    if not recipient:
        return
    subject = f"New enquiry from {enquiry.name}"
    body = "\n".join([
        f"Name: {enquiry.name}",
        f"Email: {enquiry.email}",
        f"Phone: {enquiry.phone}",
        f"Company: {enquiry.company}",
        f"City: {enquiry.city}",
        f"Product: {enquiry.product or '-'}",
        f"Interest: {enquiry.collection_ref or '-'}",
        "",
        enquiry.message,
    ])
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=True)
    except Exception:  # pragma: no cover
        logger.exception("Failed to send enquiry notification")
