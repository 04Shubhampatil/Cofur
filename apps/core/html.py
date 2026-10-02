"""Allow-list sanitiser for editor-authored HTML.

The body of a post used to be plain text that the ``paragraphs`` filter
escaped on the way out, so nothing an editor typed could become markup. A
rich-text editor changes that: the field now stores HTML and the page has to
render it as HTML, which is an injection route if anything is trusted blindly.

Only CMS users can reach these fields, so this is not the first line of
defence — it is the one that holds if an account is taken over, or if content
arrives from an import or a restored dump. Everything not on the list below is
dropped: unknown tags lose their markup but keep their text, and script,
style, iframe and friends lose their contents too.

No dependency: Python's own parser does the work, so there is nothing new to
install on the server.
"""
from html import escape
from html.parser import HTMLParser

from django.utils.safestring import mark_safe

# What the toolbar can produce, and nothing else.
ALLOWED = {
    "p": set(),
    "br": set(),
    "strong": set(),
    "em": set(),
    "u": set(),
    "h2": set(),
    "h3": set(),
    "ul": set(),
    "ol": set(),
    "li": set(),
    "blockquote": set(),
    "a": {"href", "title", "target", "rel"},
}
VOID = {"br"}
# contenteditable writes presentational tags; store the semantic ones instead.
# Without this, execCommand('bold') produces <b>, which is not on the list and
# would be stripped on the way out — the formatting would vanish on save.
ALIASES = {"b": "strong", "i": "em", "div": "p"}
# Tags whose text is markup or code, so dropping the tag must drop the text too.
DROP_CONTENT = {"script", "style", "iframe", "object", "embed", "template", "noscript"}
SAFE_SCHEMES = ("http://", "https://", "mailto:", "tel:", "/", "#")


def _safe_href(value):
    candidate = (value or "").strip()
    # javascript: and data: are the ones that matter; anything relative is fine.
    return candidate if candidate.lower().startswith(SAFE_SCHEMES) else ""


class _Cleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.open_tags = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in DROP_CONTENT:
            self.skip_depth += 1
            return
        tag = ALIASES.get(tag, tag)
        if self.skip_depth or tag not in ALLOWED:
            return
        kept = []
        for name, value in attrs:
            if name not in ALLOWED[tag]:
                continue
            if name == "href":
                value = _safe_href(value)
                if not value:
                    continue
            kept.append(f' {name}="{escape(value or "", quote=True)}"')
        if tag == "a" and not any(a.startswith(' href=') for a in kept):
            return  # a link to nowhere is just text
        if tag in VOID:
            self.out.append(f"<{tag}>")
            return
        self.out.append(f"<{tag}{''.join(kept)}>")
        self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if tag in DROP_CONTENT:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        tag = ALIASES.get(tag, tag)
        if self.skip_depth or tag in VOID or tag not in ALLOWED:
            return
        if tag in self.open_tags:
            # close anything left open inside it, so the output stays balanced
            while self.open_tags:
                open_tag = self.open_tags.pop()
                self.out.append(f"</{open_tag}>")
                if open_tag == tag:
                    break

    def handle_startendtag(self, tag, attrs):
        if tag in VOID and not self.skip_depth:
            self.out.append(f"<{tag}>")

    def handle_data(self, data):
        if not self.skip_depth:
            self.out.append(escape(data, quote=False))

    def result(self):
        while self.open_tags:
            self.out.append(f"</{self.open_tags.pop()}>")
        return "".join(self.out)


def sanitise_rich_text(value):
    """Return `value` with everything outside the allow-list removed."""
    if not value:
        return ""
    cleaner = _Cleaner()
    cleaner.feed(str(value))
    cleaner.close()
    return mark_safe(cleaner.result())


def looks_like_html(value):
    """True when the value carries markup the editor would have written.

    Posts written before the editor existed are plain text with blank lines
    between paragraphs, and have to keep rendering that way.
    """
    if not value:
        return False
    lowered = str(value).lower()
    return any(f"<{tag}" in lowered for tag in (*ALLOWED, *ALIASES))
