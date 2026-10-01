"""Cache-busting URLs for the static files we edit.

nginx serves /static/ with `expires 30d` and `Cache-Control: immutable`, so a
plain /static/css/style.css URL keeps returning the copy a visitor cached weeks
ago. Appending the file's modification time changes the URL whenever the file
changes, which is what makes a deployed CSS or JS edit actually reach people.
"""
import os

from django.conf import settings
from django.templatetags.static import static as static_url


def versioned_static(path):
    version = 0
    for base in getattr(settings, "STATICFILES_DIRS", []):
        candidate = os.path.join(str(base), path)
        if os.path.exists(candidate):
            version = int(os.path.getmtime(candidate))
            break
    return f"{static_url(path)}?v={version}"
