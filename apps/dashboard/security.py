"""Admin-panel hardening: login lockout, IP allow-list, inactivity logout, no-cache headers."""
import ipaddress
import logging
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse

from apps.enquiries.services import client_ip

log = logging.getLogger("cofur.security")


def admin_prefix():
    return "/" + settings.ADMIN_URL.strip("/") + "/"


# ---------------------------------------------------------------- login lockout
def _keys(ip, username):
    return f"login-fail:ip:{ip}", f"login-fail:user:{(username or '').strip().lower()[:150]}"


def lockout_seconds(ip, username):
    """Seconds left on a lockout for this IP or username, 0 when not locked."""
    limit = settings.ADMIN_LOGIN_MAX_ATTEMPTS
    remaining = 0
    for key in _keys(ip, username):
        entry = cache.get(key)
        if entry and entry["count"] >= limit:
            remaining = max(remaining, int(entry["until"] - time.time()))
    return max(remaining, 0)


def record_failure(ip, username):
    window = settings.ADMIN_LOGIN_LOCKOUT_MINUTES * 60
    for key in _keys(ip, username):
        entry = cache.get(key) or {"count": 0, "until": time.time() + window}
        entry["count"] += 1
        entry["until"] = time.time() + window
        cache.set(key, entry, window)
    log.warning("Failed admin login for %r from %s", username, ip)


def reset_failures(ip, username):
    cache.delete_many(_keys(ip, username))


# ---------------------------------------------------------------- IP allow-list
def ip_allowed(ip):
    allowed = settings.ADMIN_ALLOWED_IPS
    if not allowed:
        return True
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for rule in allowed:
        try:
            if address in ipaddress.ip_network(rule, strict=False):
                return True
        except ValueError:
            continue
    return False


class AdminAccessMiddleware:
    """Guards every request under the admin prefix."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith(admin_prefix()):
            return self.get_response(request)

        ip = client_ip(request)
        if not ip_allowed(ip):
            log.warning("Admin request from disallowed IP %s to %s", ip, request.path)
            return HttpResponseForbidden("Admin access is restricted.")

        if request.user.is_authenticated:
            now = time.time()
            last = request.session.get("admin_last_activity")
            limit = settings.ADMIN_INACTIVITY_MINUTES * 60
            if last and now - last > limit:
                logout(request)
                messages.info(request, "You were signed out after a period of inactivity.")
                return redirect(f"{reverse('dashboard:login')}?next={request.path}")
            request.session["admin_last_activity"] = now

        response = self.get_response(request)
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response["Pragma"] = "no-cache"
        response["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        return response
