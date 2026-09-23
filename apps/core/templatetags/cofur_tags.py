import re

from django import template
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

register = template.Library()

MOBILE_MEDIA = "(max-width:767px)"


class PictureNode(template.Node):
    """Wrap the enclosed <img> in <picture> with a mobile <source> when a mobile image exists."""

    def __init__(self, mobile_expr, nodelist):
        self.mobile_expr = mobile_expr
        self.nodelist = nodelist

    def render(self, context):
        inner = self.nodelist.render(context)
        try:
            mobile = self.mobile_expr.resolve(context)
            url = mobile.url if mobile else ""
        except (template.VariableDoesNotExist, ValueError, AttributeError):
            url = ""
        if not url:
            return inner
        return f'<picture><source media="{MOBILE_MEDIA}" srcset="{url}">{inner}</picture>'


@register.tag
def picture(parser, token):
    bits = token.split_contents()
    if len(bits) != 2:
        raise template.TemplateSyntaxError("Usage: {% picture <mobile image> %}<img ...>{% endpicture %}")
    nodelist = parser.parse(("endpicture",))
    parser.delete_first_token()
    return PictureNode(parser.compile_filter(bits[1]), nodelist)


@register.simple_tag
def mobile_source(mobile):
    """<source> for an existing <picture> wrapper; empty when no mobile image."""
    try:
        url = mobile.url if mobile else ""
    except (ValueError, AttributeError):
        url = ""
    if not url:
        return ""
    from django.utils.safestring import mark_safe

    return mark_safe(f'<source media="{MOBILE_MEDIA}" srcset="{url}">')


@register.filter(name="paragraphs")
def paragraphs(value, css_class=""):
    """Split text on blank lines into <p> elements, escaping content and keeping single newlines as <br>."""
    if not value:
        return ""
    blocks = [block.strip() for block in re.split(r"\n\s*\n", str(value).strip()) if block.strip()]
    cls = f' class="{escape(css_class)}"' if css_class else ""
    html = "".join(f"<p{cls}>{escape(block).replace(chr(10), '<br>')}</p>" for block in blocks)
    return mark_safe(html)


@register.filter(name="lines")
def lines(value):
    """Split text into a list of non-empty lines."""
    if not value:
        return []
    return [line.strip() for line in str(value).splitlines() if line.strip()]


@register.filter(name="br")
def br(value):
    """Escape and convert newlines to <br>."""
    if not value:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    return mark_safe(escape(text).replace("\n", "<br>"))


@register.filter(name="image_url")
def image_url(field_file, fallback=""):
    try:
        if field_file:
            return field_file.url
    except ValueError:
        pass
    return fallback


@register.simple_tag
def social_icon(platform):
    paths = {
        "linkedin": '<path d="M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5zM3 9h4v12H3zM10 9h3.8v1.7h.05c.53-.95 1.83-1.95 3.77-1.95 4.03 0 4.78 2.5 4.78 5.76V21h-4v-5.6c0-1.34-.03-3.06-1.9-3.06-1.9 0-2.2 1.45-2.2 2.96V21h-4z"/>',
        "instagram": '<path d="M12 2.2c3.2 0 3.58.01 4.85.07 1.17.05 1.8.25 2.23.41.56.22.96.48 1.38.9.42.42.68.82.9 1.38.16.42.36 1.06.41 2.23.06 1.27.07 1.65.07 4.85s-.01 3.58-.07 4.85c-.05 1.17-.25 1.8-.41 2.23-.22.56-.48.96-.9 1.38-.42.42-.82.68-1.38.9-.42.16-1.06.36-2.23.41-1.27.06-1.65.07-4.85.07s-3.58-.01-4.85-.07c-1.17-.05-1.8-.25-2.23-.41-.56-.22-.96-.48-1.38-.9-.42-.42-.68-.82-.9-1.38-.16-.42-.36-1.06-.41-2.23C2.21 15.58 2.2 15.2 2.2 12s.01-3.58.07-4.85c.05-1.17.25-1.8.41-2.23.22-.56.48-.96.9-1.38.42-.42.82-.68 1.38-.9.42-.16 1.06-.36 2.23-.41C8.42 2.21 8.8 2.2 12 2.2zm0 3.05A6.75 6.75 0 1 0 18.75 12 6.75 6.75 0 0 0 12 5.25zm0 11.13A4.38 4.38 0 1 1 16.38 12 4.38 4.38 0 0 1 12 16.38zm6.99-11.4a1.58 1.58 0 1 1-1.58-1.57 1.58 1.58 0 0 1 1.58 1.57z"/>',
        "x": '<path d="M17.5 3h3.1l-6.8 7.77L21.8 21h-6.2l-4.86-6.35L5.18 21H2.07l7.27-8.31L2.2 3h6.36l4.39 5.8zm-1.09 16.1h1.72L7.66 4.81H5.82z"/>',
        "facebook": '<path d="M13.5 21v-7h2.4l.4-3h-2.8V9.1c0-.9.3-1.5 1.5-1.5h1.4V5.1c-.3 0-1.1-.1-2.1-.1-2.1 0-3.6 1.3-3.6 3.7V11H8v3h2.7v7z"/>',
        "youtube": '<path d="M21.6 7.2a2.5 2.5 0 0 0-1.8-1.8C18.2 5 12 5 12 5s-6.2 0-7.8.4A2.5 2.5 0 0 0 2.4 7.2 26 26 0 0 0 2 12a26 26 0 0 0 .4 4.8 2.5 2.5 0 0 0 1.8 1.8C5.8 19 12 19 12 19s6.2 0 7.8-.4a2.5 2.5 0 0 0 1.8-1.8A26 26 0 0 0 22 12a26 26 0 0 0-.4-4.8zM10 15V9l5.2 3z"/>',
        "whatsapp": '<path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8s-.4-.1-.6.1-.6.8-.8 1-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.2-.4.7-1.3a.5.5 0 0 0 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 2.9 2.9 0 0 0-.9 2.2 5 5 0 0 0 1 2.7 11.4 11.4 0 0 0 4.4 3.9c1.6.7 2.3.7 3.1.6a2.6 2.6 0 0 0 1.7-1.2 2.1 2.1 0 0 0 .2-1.2c-.1-.1-.3-.2-.5-.3z"/>',
        "pinterest": '<path d="M12 2a10 10 0 0 0-3.6 19.3c-.1-.8-.2-2 0-2.9l1.2-5s-.3-.6-.3-1.5c0-1.4.8-2.4 1.8-2.4.9 0 1.3.6 1.3 1.4 0 .9-.5 2.2-.8 3.4-.2 1 .5 1.8 1.5 1.8 1.8 0 3.1-1.9 3.1-4.6 0-2.4-1.7-4.1-4.2-4.1-2.9 0-4.5 2.1-4.5 4.4 0 .9.3 1.8.8 2.3.1.1.1.2.1.3l-.3 1.2c0 .2-.2.2-.4.1-1.2-.6-2-2.4-2-3.9 0-3.2 2.3-6.1 6.6-6.1 3.5 0 6.2 2.5 6.2 5.8 0 3.4-2.2 6.2-5.2 6.2-1 0-2-.5-2.3-1.1l-.6 2.4c-.2.9-.8 2-1.2 2.6A10 10 0 1 0 12 2z"/>',
    }
    path = paths.get(platform, '<circle cx="12" cy="12" r="9"/>')
    return format_html('<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">{}</svg>', mark_safe(path))


@register.simple_tag(takes_context=True)
def query_replace(context, **kwargs):
    """Return the current query string with the given parameters replaced."""
    request = context["request"]
    query = request.GET.copy()
    for key, value in kwargs.items():
        if value is None or value == "":
            query.pop(key, None)
        else:
            query[key] = value
    encoded = query.urlencode()
    return f"?{encoded}" if encoded else "?"


@register.filter
def get_item(mapping, key):
    try:
        return mapping.get(key)
    except AttributeError:
        return None


@register.filter
def attr(obj, name):
    """Access an attribute or callable by name in templates (used by generic dashboard lists)."""
    if obj is None:
        return ""
    value = obj
    for part in str(name).split("."):
        if value is None:
            return ""
        if isinstance(value, dict):
            value = value.get(part)
        else:
            value = getattr(value, part, "")
        if callable(value) and not getattr(value, "do_not_call_in_templates", False):
            try:
                value = value()
            except TypeError:
                pass
    return value
