# COFUR — Django CMS

The COFUR website converted into a database-driven Django 5.1 CMS with a custom admin
dashboard, REST API and MySQL 8 storage. The public frontend keeps the original design
(templates, CSS, GSAP animations) — every piece of content is now editable from `/admin/`.

The original static site is preserved for reference in `legacy/` (its assets now live in `static/`).

## Stack

Python 3.12 · Django 5.1.6 · Django REST Framework 3.15.2 · MySQL 8 (`mysqlclient`) · Pillow ·
django-cors-headers · python-dotenv · Django templates + vanilla CSS/JS. No frontend framework.

## Project layout

```
config/                 settings, urls, wsgi, asgi
apps/
  core/                 SiteSettings, Navigation menus (seeded), SEO mixin, image utils, roles, seed command
  catalog/              Category, Collection (shown as "Sub-category" in the dashboard), Product (+ images, specifications, features, colours)
  pages/                HomePage (+ hero slides, statement lines, differentiators; featured products come from the product flag), AboutPage, ContactPage
  team/                 TeamMember
  enquiries/            Enquiry model, public form, services (rate limiting, notifications)
  website/              public views + legacy URL redirects
  dashboard/            custom admin (auth, CRUD, media, settings)
  api/                  DRF serializers / viewsets
templates/              base.html, partials/, components/, pages/, dashboard/
static/                 css, js, fonts, images, vendor, dashboard/ (admin css+js)
media/                  uploaded files (MEDIA_ROOT, git-ignored)
legacy/                 original static HTML for reference
```

## Development setup

```bash
python -m venv .venv && .venv\Scripts\activate      # (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env  


 python manage.py runserver  

 # then edit values
```

Create the MySQL database and user:

```sql
CREATE DATABASE cofur CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'cofur'@'localhost' IDENTIFIED BY 'change-me';
GRANT ALL PRIVILEGES ON cofur.* TO 'cofur'@'localhost';
GRANT ALL PRIVILEGES ON test_cofur.* TO 'cofur'@'localhost';   -- needed by manage.py test
FLUSH PRIVILEGES;
```

Set `DATABASE_*` in `.env` (`DATABASE_ENGINE=mysql`). For a quick local run without MySQL you can
set `DATABASE_ENGINE=sqlite` — production must use MySQL.

```bash
python manage.py migrate
set ADMIN_PASSWORD=your-strong-password     # or pass --admin-password
python manage.py seed_cofur                 # loads the current website content + creates the admin user
python manage.py runserver
```

* Website: http://127.0.0.1:8000/
* Dashboard: http://127.0.0.1:8000/admin/ (login with the seeded superuser, default username `admin`)
* API: http://127.0.0.1:8000/api/

### Seed command

`python manage.py seed_cofur [--force] [--skip-images] [--admin-username U] [--admin-password P]`

Idempotent: existing records (matched by slug/name) are kept; `--force` refreshes them with the
seed content. Images referenced by the original site are copied from `static/images/` into
`media/seed/...` so they are fully replaceable from the dashboard. Also creates the role groups
**Admin**, **Editor** and **Staff** (see `apps/core/roles.py`).

## Dashboard

| Area | URL |
| --- | --- |
| Dashboard (stats, recent activity, quick actions) | `/admin/` |
| Login / logout / password | `/admin/login/`, `/admin/logout/`, `/admin/password/` |
| Home / About / Contact page content | `/admin/content/home/`, `/admin/content/about/`, `/admin/content/contact/` |
| Footer | `/admin/content/footer/` |
| Products | `/admin/products/` (+ `add/`, `<id>/`, `<id>/delete/`, `<id>/duplicate/`, `<id>/toggle-featured/`, `<id>/toggle-publish/`, `<id>/gallery/upload/`, `reorder/`) |
| Categories / Sub-categories (inline add form + table, status switch) | `/admin/categories/`, `/admin/sub-categories/` (+ `add/`, `<id>/`, `<id>/delete/`, `<id>/toggle-active/`, `reorder/`) |
| Bulk product actions (publish, unpublish, feature, delete) | `/admin/products/bulk/` |
| Team members | `/admin/team/` |
| Enquiries | `/admin/enquiries/`, `/admin/enquiries/<id>/` |
| Site settings (brand, contact, footer social icons) | `/admin/settings/site/` |

Every view checks Django model permissions (`catalog.change_product`, `enquiries.view_enquiry`, …).
The dashboard is used by the single `admin` superuser created by `seed_cofur`. Additional staff
accounts can be created with `python manage.py createsuperuser` if ever needed.

Image uploads (all forms and drag-and-drop galleries) are validated with Pillow
(type, size, dimensions); images wider than `IMAGE_MAX_EDGE` are resized, JPEG/PNG uploads are
stored as **WebP** (`IMAGE_CONVERT_WEBP`, quality `IMAGE_WEBP_QUALITY`; SVG and GIF are kept as
is) and thumbnails are generated. `python manage.py convert_webp` converts images that were
uploaded before this was enabled.

Full-width page banners (home hero slides, About and Contact banners, category and collection
banners) have an optional **Mobile banner image** and mobile alt text shown below 768px. When set,
the page renders a `<picture>` with a `(max-width:767px)` source; otherwise the plain `<img>` is
unchanged. Product, mosaic, gallery, swatch and card images are desktop-only.

Rows of kind "Product details mosaic" can be a **video** instead of an image: upload an MP4/WebM
(up to `MAX_VIDEO_UPLOAD_MB`, default 100) or paste a YouTube/Vimeo link; the image, if set, is
used as the poster frame.

## Public URLs

```
/                         home
/about/                   about
/contact/                 contact + enquiry form (GET/POST)
/enquire/                 enquiry endpoint (HTML or AJAX/JSON POST)
/collections/             all collections
/collections/<slug>/      collection detail (products)
/categories/<slug>/       category page (collections in the category)
/products/<slug>/         product detail (specs, gallery, related, enquiry popup)
```

Legacy static URLs (`index.html`, `about.html`, `contact.html`, `soft-seating-main-category.html`,
`cove-collection-sub-cateogry.html`, `product-detailes.html`, `collection.html`, `cove-social.html`)
redirect permanently to the new URLs.

## REST API

```
GET  /api/products/                ?collection=<slug> ?category=<slug> ?featured=1 ?search=
GET  /api/products/<slug>/
GET  /api/collections/             ?category=<slug>
GET  /api/collections/<slug>/
GET  /api/categories/
GET  /api/categories/<slug>/
GET  /api/team/
GET  /api/pages/home/
GET  /api/pages/about/
GET  /api/pages/contact/
GET  /api/settings/
GET  /api/navigation/
POST /api/enquiries/               {name, email, phone, company, city, product(slug), collection_ref, message}
```

Responses are paginated (20/page). Enquiry creation is throttled (10/hour anonymous) and
protected by a honeypot field (`website`) plus a per-IP limit.

## Tests

```bash
python manage.py check
python manage.py test
```

102 tests cover models, URLs, views, forms, authentication, permissions, product/collection/
category/team CRUD, enquiry submission, media upload validation and the API.

## Admin security

Only accounts created by the administrator can sign in; there is no self-registration and the
public site never links to the admin. On top of Django's CSRF, session and password protections:

- **Login lockout**: after `ADMIN_LOGIN_MAX_ATTEMPTS` failed sign-ins (per IP *and* per username)
  the login is refused for `ADMIN_LOGIN_LOCKOUT_MINUTES`. Failures are logged under `cofur.security`.
- **IP allow-list**: set `ADMIN_ALLOWED_IPS` (IPs or CIDR ranges) to make the admin reachable only
  from your office / VPN; everyone else gets 403. Leave empty to allow any IP.
- **Private admin URL**: change `ADMIN_URL` (e.g. `cofur-office-9f3a/`) so the panel is not at a
  guessable address. `/dashboard/…` keeps redirecting to the current prefix.
- **Sessions**: `SameSite=Strict`, `HttpOnly`, secure in production, 12-hour maximum, and automatic
  sign-out after `ADMIN_INACTIVITY_MINUTES` of inactivity. The session key is rotated on login.
- **Passwords**: minimum 12 characters plus Django's similarity, common-password and numeric checks.
- **Headers**: admin responses are `no-store` and `noindex`; the whole site sends `X-Frame-Options: DENY`,
  `nosniff`, a strict referrer policy and (with `SECURE_HSTS_SECONDS`) HSTS. `/robots.txt` disallows
  the admin and API paths.

The lockout counters use Django's cache. With several gunicorn workers use a shared cache
(`CACHES` → Redis or the database cache) so all workers see the same counts.

## Deployment

See [DEPLOY.md](DEPLOY.md) for the complete Ubuntu VPS guide (Hostinger KVM), with ready-made
gunicorn, nginx and update scripts in `deploy/`.

## Production setup

1. `.env`: `DEBUG=False`, a long random `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`,
   MySQL credentials, `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`,
   `CSRF_COOKIE_SECURE=True`, `SECURE_HSTS_SECONDS=31536000`, `SECURE_PROXY_SSL_HEADER=True`
   (when behind nginx/a load balancer), SMTP settings and `ENQUIRY_NOTIFICATION_EMAIL`.
2. `pip install -r requirements.txt` (plus `gunicorn` or `uvicorn`).
3. `python manage.py migrate && python manage.py seed_cofur --admin-password ...`
4. `python manage.py collectstatic --noinput` → serves `STATIC_ROOT` (default `staticfiles/`).
   Set `USE_MANIFEST_STATIC=True` to enable hashed filenames.
5. Serve with WSGI (`gunicorn config.wsgi:application`) or ASGI (`uvicorn config.asgi:application`).
6. nginx (or equivalent) serves `STATIC_URL` from `STATIC_ROOT` and `MEDIA_URL` from `MEDIA_ROOT`;
   Django never serves them when `DEBUG=False`.
7. `python manage.py check --deploy` should report no warnings once the `.env` above is in place.

Never commit `.env`. Secrets are read only from environment variables.
