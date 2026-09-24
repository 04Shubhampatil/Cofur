from django import template
from django.urls import NoReverseMatch, reverse
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def resolve(obj, path):
    """Resolve a dotted attribute path, calling callables without args."""
    value = obj
    for part in str(path).split("."):
        if value is None:
            return None
        value = getattr(value, part, None)
        if callable(value) and not getattr(value, "do_not_call_in_templates", False):
            try:
                value = value()
            except TypeError:
                pass
    return value


@register.simple_tag
def cell(obj, column):
    """Render a table cell for the generic list."""
    ctype = column.get("type", "text")
    value = resolve(obj, column["field"])
    if ctype == "image":
        try:
            url = value.url if value else ""
        except ValueError:
            url = ""
        if url:
            return format_html('<span class="thumb"><img src="{}" alt="" loading="lazy"></span>', url)
        return mark_safe('<span class="thumb thumb--empty"></span>')
    if ctype == "title":
        return format_html('<strong class="cell-title">{}</strong>', value if value is not None else "")
    if ctype == "bool":
        return mark_safe('<span class="dot dot--on" title="Yes"></span>' if value else '<span class="dot" title="No"></span>')
    if ctype == "active":
        return mark_safe('<span class="badge badge--success">Active</span>' if value else '<span class="badge">Inactive</span>')
    if ctype == "status":
        label = escape(resolve(obj, "get_status_display") or value)
        cls = "badge--success" if value == "published" else "badge--warn"
        return format_html('<span class="badge {}">{}</span>', cls, label)
    if ctype == "enquiry_status":
        label = escape(resolve(obj, "get_status_display") or value)
        cls = {"new": "badge--info", "contacted": "badge--warn", "in_progress": "badge--warn", "converted": "badge--success", "closed": ""}.get(value, "")
        return format_html('<span class="badge {}">{}</span>', cls, label)
    if ctype == "featured":
        return mark_safe('<span class="star star--on" title="Featured">★</span>' if value else '<span class="star" title="Not featured">☆</span>')
    if ctype == "date":
        return format_html("{}", value.strftime("%d %b %Y") if value else "—")
    if ctype == "datetime":
        from django.utils import timezone

        if not value:
            return "—"
        local = timezone.localtime(value)
        return format_html('<span title="{}">{}</span>', local.strftime("%d %b %Y %H:%M"), local.strftime("%d %b %Y %H:%M"))
    if value is None or value == "":
        return mark_safe('<span class="muted">—</span>')
    return format_html("{}", value)


@register.simple_tag
def crumb_url(crumb):
    url = crumb.get("url")
    if not url:
        return ""
    if crumb.get("absolute"):
        return url
    try:
        return reverse(url)
    except NoReverseMatch:
        return url


@register.filter
def field_by_name(form, name):
    try:
        return form[name]
    except KeyError:
        return None


@register.filter
def widget_type(bound_field):
    widget = bound_field.field.widget
    return widget.__class__.__name__.lower()


@register.filter
def is_checkbox(bound_field):
    from django import forms

    return isinstance(bound_field.field.widget, forms.CheckboxInput)


@register.filter
def is_image(bound_field):
    from django import forms

    return isinstance(bound_field.field, forms.ImageField)


@register.filter
def is_multi_checkbox(bound_field):
    from django import forms

    return isinstance(bound_field.field.widget, forms.CheckboxSelectMultiple)


@register.simple_tag(takes_context=True)
def qs_replace(context, **kwargs):
    request = context["request"]
    query = request.GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            query.pop(key, None)
        else:
            query[key] = value
    encoded = query.urlencode()
    return f"?{encoded}" if encoded else "?"


@register.simple_tag
def icon(name):
    icons = {
        "home": '<path d="M3 11l9-8 9 8v9a2 2 0 0 1-2 2h-4v-7H9v7H5a2 2 0 0 1-2-2z"/>',
        "layout": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>',
        "info": '<circle cx="12" cy="12" r="9"/><path d="M12 8h.01M11 12h1v4h1"/>',
        "phone": '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.6a2 2 0 0 1-.5 2.1L8 9.7a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.8.3 1.7.5 2.6.7a2 2 0 0 1 1.7 2z"/>',
        "box": '<path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4a2 2 0 0 0 1-1.7z"/><path d="M3.3 7l8.7 5 8.7-5M12 22V12"/>',
        "layers": '<path d="M12 2l10 5-10 5L2 7z"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5"/>',
        "grid": '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
        "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
        "user": '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
        "mail": '<path d="M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/><path d="M22 6l-10 7L2 6"/>',
        "image": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/>',
        "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
        "search": '<circle cx="11" cy="11" r="8"/><path d="M21 21l-4.3-4.3"/>',
        "share": '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/>',
        "menu": '<path d="M3 12h18M3 6h18M3 18h18"/>',
        "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
        "plus": '<path d="M12 5v14M5 12h14"/>',
        "edit": '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.1 2.1 0 0 1 3 3L12 15l-4 1 1-4z"/>',
        "trash": '<path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2m2 0v14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V6h12z"/>',
        "copy": '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
        "eye": '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/><circle cx="12" cy="12" r="3"/>',
        "star": '<path d="M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z"/>',
        "list": '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
        "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5M21 12H9"/>',
        "upload": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M17 8l-5-5-5 5M12 3v12"/>',
        "check": '<path d="M20 6L9 17l-5-5"/>',
        "x": '<path d="M18 6L6 18M6 6l12 12"/>',
        "external": '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><path d="M15 3h6v6M10 14L21 3"/>',
        "drag": '<circle cx="9" cy="6" r="1.5"/><circle cx="15" cy="6" r="1.5"/><circle cx="9" cy="12" r="1.5"/><circle cx="15" cy="12" r="1.5"/><circle cx="9" cy="18" r="1.5"/><circle cx="15" cy="18" r="1.5"/>',
        "dot": '<circle cx="12" cy="12" r="3"/>',
        "chevron": '<path d="M9 18l6-6-6-6"/>',
        "arrow-up": '<path d="M12 19V5M5 12l7-7 7 7"/>',
        "arrow-down": '<path d="M12 5v14M19 12l-7 7-7-7"/>',
        "key": '<path d="M21 2l-2 2m-7.6 7.6a5.5 5.5 0 1 1-7.8 7.8 5.5 5.5 0 0 1 7.8-7.8zm0 0L15 8m0 0l3 3L22 7l-3-3"/>',
    }
    return format_html(
        '<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{}</svg>',
        mark_safe(icons.get(name, icons["dot"])),
    )


@register.filter
def split(value, sep=","):
    return [part for part in str(value).split(sep) if part]


@register.filter
def get_item(mapping, key):
    try:
        return mapping.get(key)
    except AttributeError:
        return None


@register.simple_tag
def static_v(path):
    """Static URL with a ?v= cache-buster based on the file's modification time."""
    import os

    from django.conf import settings
    from django.templatetags.static import static as static_url

    version = 0
    for base in getattr(settings, "STATICFILES_DIRS", []):
        candidate = os.path.join(str(base), path)
        if os.path.exists(candidate):
            version = int(os.path.getmtime(candidate))
            break
    return f"{static_url(path)}?v={version}"
