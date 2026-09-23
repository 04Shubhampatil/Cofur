"""Role (Django Group) definitions for the CMS.

* Admin  – every CMS permission (content, catalog, leads, media, settings).
* Editor – create/edit content and catalog, manage enquiries, no deletions of
           settings/navigation.
* Staff  – read-only content access plus enquiry handling.

Superusers manage users and roles; nobody else can.
"""
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

CMS_MODELS = {
    "catalog": ["category", "collection", "product", "productimage", "productspecification", "productfeature", "productcolor"],
    "pages": ["homepage", "homeheroslide", "homestatementline", "differentiator", "aboutpage", "contactpage"],
    "team": ["teammember"],
    "enquiries": ["enquiry"],
    "core": ["sitesettings", "navigationmenu", "navigationitem"],
}

ROLE_DEFINITIONS = {
    "Admin": {
        "catalog": ["view", "add", "change", "delete"],
        "pages": ["view", "add", "change", "delete"],
        "team": ["view", "add", "change", "delete"],
        "enquiries": ["view", "change", "delete"],
        "core": ["view", "add", "change", "delete"],
    },
    "Editor": {
        "catalog": ["view", "add", "change", "delete"],
        "pages": ["view", "add", "change"],
        "team": ["view", "add", "change", "delete"],
        "enquiries": ["view", "change"],
        "core": ["view", "add", "change"],
    },
    "Staff": {
        "catalog": ["view"],
        "pages": ["view"],
        "team": ["view"],
        "enquiries": ["view", "change"],
        "core": ["view"],
    },
}


def permissions_for(app_label, actions):
    perms = []
    for model in CMS_MODELS.get(app_label, []):
        try:
            ct = ContentType.objects.get(app_label=app_label, model=model)
        except ContentType.DoesNotExist:
            continue
        for action in actions:
            perm = Permission.objects.filter(content_type=ct, codename=f"{action}_{model}").first()
            if perm:
                perms.append(perm)
    return perms


def ensure_roles():
    """Create/refresh the role groups. Safe to run repeatedly."""
    groups = {}
    for name, spec in ROLE_DEFINITIONS.items():
        group, _ = Group.objects.get_or_create(name=name)
        perms = []
        for app_label, actions in spec.items():
            perms.extend(permissions_for(app_label, actions))
        group.permissions.set(perms)
        groups[name] = group
    return groups
