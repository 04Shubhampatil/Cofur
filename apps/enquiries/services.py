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


def save_enquiry(enquiry: Enquiry, request=None, source="contact", collection_ref="", notify=None):
    enquiry.source = source
    if collection_ref and not enquiry.collection_ref:
        enquiry.collection_ref = collection_ref[:120]
    if request is not None:
        enquiry.ip_address = client_ip(request)
        enquiry.user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]
    enquiry.save()
    notify_admins(enquiry, notify=notify)
    return enquiry


def notify_admins(enquiry, notify=None):
    """Email the enquiry to the team.

    ``notify`` lets a campaign landing page say where its leads go, which page
    produced them and which product the visitor picked:
    {"email", "page_title", "page_url", "product_interest"}. Without it the
    mail behaves exactly as before — straight to ENQUIRY_NOTIFICATION_EMAIL,
    with no page lines.
    """
    notify = notify or {}
    recipient = notify.get("email") or settings.ENQUIRY_NOTIFICATION_EMAIL
    if not recipient:
        return
    subject = f"New enquiry from {enquiry.name}"
    if notify.get("page_title"):
        subject = f"{subject} — {notify['page_title']}"
    page_lines = []
    if notify.get("page_title"):
        page_lines.append(f"Page: {notify['page_title']}")
    if notify.get("page_url"):
        page_lines.append(f"Page URL: {notify['page_url']}")
    if page_lines:
        page_lines.append("")
    # A campaign page's products are a fixed list, not always catalogue
    # records, so fall back to the label the visitor actually chose.
    product = enquiry.product or notify.get("product_interest") or "-"
    body = "\n".join(page_lines + [
        f"Name: {enquiry.name}",
        f"Email: {enquiry.email}",
        f"Phone: {enquiry.phone}",
        f"Company: {enquiry.company}",
        f"City: {enquiry.city}",
        f"Product: {product}",
        f"Interest: {enquiry.collection_ref or '-'}",
        "",
        enquiry.message,
    ])
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=True)
    except Exception:  # pragma: no cover
        logger.exception("Failed to send enquiry notification")
