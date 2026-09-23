# Deploying COFUR CMS on an Ubuntu VPS (Hostinger KVM)

Target: Ubuntu 24.04 LTS, Python 3.12, MySQL 8, gunicorn behind nginx, HTTPS via Let's Encrypt.
Every command below is copy-and-paste. Replace `example.com` with your domain and `YOUR_VPS_IP`
with the server address from hPanel.

Ready-made config files live in `deploy/`:

| File | Purpose |
| --- | --- |
| `deploy/cofur.service` | systemd unit that runs gunicorn |
| `deploy/cofur.nginx` | nginx site that serves `/static/`, `/media/` and proxies to gunicorn |
| `deploy/update.sh` | one-command update for later releases |

---

## 1. Order the server

In Hostinger choose **VPS → KVM 1** (or KVM 2), operating system **Ubuntu 24.04**, data centre
**India**, and set a strong root password. Hostinger's "Django" template is optional; the steps
below install everything explicitly so they work on the plain Ubuntu image too.

## 2. Point the domain

In your DNS panel add two records and wait until they resolve (`ping example.com`):

```
A     example.com        YOUR_VPS_IP
A     www.example.com    YOUR_VPS_IP
```

## 3. First login and base packages

```bash
ssh root@YOUR_VPS_IP
apt update && apt upgrade -y
apt install -y python3.12 python3.12-venv python3-pip build-essential pkg-config \
    default-libmysqlclient-dev mysql-server nginx certbot python3-certbot-nginx git ufw
```

Firewall: allow SSH and web traffic only.

```bash
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
```

Create a dedicated user that will own the app (never run it as root):

```bash
adduser --disabled-password --gecos "" cofur
usermod -aG www-data cofur
mkdir -p /srv/cofur /var/log/cofur
chown -R cofur:www-data /srv/cofur /var/log/cofur
```

## 4. MySQL 8

```bash
mysql_secure_installation     # set a root password, remove test DB, disallow remote root
mysql -u root -p
```

Inside the MySQL prompt (choose your own password):

```sql
CREATE DATABASE cofur CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'cofur'@'localhost' IDENTIFIED BY 'CHOOSE-A-STRONG-PASSWORD';
GRANT ALL PRIVILEGES ON cofur.* TO 'cofur'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## 5. Upload the project

Either push the project to a Git repository and clone it, or copy the folder from your PC.

**Option A – git (recommended)**

```bash
su - cofur
git clone https://github.com/YOUR-ACCOUNT/cofur.git /srv/cofur
```

**Option B – copy from Windows** (run in PowerShell on your PC, from the folder above `cofur`):

```powershell
scp -r "C:\main Projects\cofur" cofur@YOUR_VPS_IP:/srv/
```

Do **not** copy your local `.env`, `db.sqlite3`, `staticfiles/` or `.venv/`. The `media/`
folder *should* be copied if you already uploaded images locally.

## 6. Python environment

```bash
su - cofur
cd /srv/cofur
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt
```

## 7. Production `.env`

```bash
cp .env.example .env
nano .env
```

Set at least these values (everything else can keep the example defaults):

```
SECRET_KEY=            # paste a long random string, e.g. from: python -c "import secrets;print(secrets.token_urlsafe(64))"
DEBUG=False
ALLOWED_HOSTS=example.com,www.example.com
CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com
CORS_ALLOWED_ORIGINS=https://example.com,https://www.example.com

DATABASE_ENGINE=mysql
DATABASE_NAME=cofur
DATABASE_USER=cofur
DATABASE_PASSWORD=CHOOSE-A-STRONG-PASSWORD
DATABASE_HOST=127.0.0.1
DATABASE_PORT=3306

SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_PROXY_SSL_HEADER=True

ADMIN_USERNAME=admin
ADMIN_PASSWORD=                # strong, 12+ characters – used once by seed_cofur
ADMIN_URL=admin/               # optionally change to a private path, e.g. cofur-office-9f3a/
ADMIN_ALLOWED_IPS=             # optional: your office/VPN IPs, comma separated

EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.hostinger.com
EMAIL_PORT=465
EMAIL_USE_SSL=True
EMAIL_HOST_USER=info@example.com
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=info@example.com
ENQUIRY_NOTIFICATION_EMAIL=info@example.com
```

Lock the file down: `chmod 600 .env`.

## 8. Database, content and static files

```bash
python manage.py migrate
python manage.py seed_cofur          # loads the website content and creates the admin user
python manage.py convert_webp        # converts any JPG/PNG already in media/ to WebP
python manage.py collectstatic --noinput
python manage.py check --deploy      # must print "System check identified no issues"
exit                                 # back to root
```

## 9. gunicorn service

```bash
cp /srv/cofur/deploy/cofur.service /etc/systemd/system/cofur.service
systemctl daemon-reload
systemctl enable --now cofur
systemctl status cofur --no-pager    # should say "active (running)"
```

## 10. nginx and HTTPS

```bash
cp /srv/cofur/deploy/cofur.nginx /etc/nginx/sites-available/cofur
sed -i 's/example.com/YOURDOMAIN/g' /etc/nginx/sites-available/cofur   # replace YOURDOMAIN
ln -s /etc/nginx/sites-available/cofur /etc/nginx/sites-enabled/cofur
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
certbot --nginx -d example.com -d www.example.com     # answers: your email, agree, redirect = yes
```

Certbot rewrites the nginx file for HTTPS and installs automatic renewal.

## 11. Verify

- `https://example.com/` shows the website.
- `https://example.com/admin/` (or your private `ADMIN_URL`) shows the login page; sign in with
  the admin user.
- Upload an image in the admin: it should appear on the site, and `ls /srv/cofur/media/...`
  should show a `.webp` file.
- Submit the contact form once and confirm the enquiry appears under Leads › Enquiries and
  arrives by email.
- `curl -I https://example.com/admin/` should show `Cache-Control: no-store` and
  `Strict-Transport-Security`.

## 12. Updating the site later

```bash
ssh cofur@YOUR_VPS_IP
cd /srv/cofur && bash deploy/update.sh
```

The script pulls the code, installs requirements, runs migrations and `collectstatic`, runs the
deploy check and restarts gunicorn. If you copy files instead of using git, run the same script
after copying.

## 13. Backups and maintenance

- **Database**: `mysqldump -u cofur -p cofur | gzip > /srv/backups/cofur-$(date +%F).sql.gz`
  (create `/srv/backups` first). Hostinger's weekly VPS snapshots cover the whole server too.
- **Uploads**: back up `/srv/cofur/media/` together with the database dump.
- **Logs**: `journalctl -u cofur -f` for the app, `/var/log/cofur/` for gunicorn,
  `/var/log/nginx/` for the web server. Failed admin logins appear in the app log.
- **Ubuntu updates**: `apt update && apt upgrade -y` monthly, then `reboot` if the kernel changed.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| 502 Bad Gateway | `systemctl status cofur` and `tail /var/log/cofur/error.log`; usually a bad `.env` value |
| Static files missing (unstyled pages) | `python manage.py collectstatic` ran, and the `alias` paths in the nginx file match `/srv/cofur/staticfiles/` |
| CSRF error on login | `CSRF_TRUSTED_ORIGINS` must include `https://example.com` |
| Images upload but do not show | nginx `/media/` alias and folder permissions: `chown -R cofur:www-data /srv/cofur/media` |
| Locked out of admin | wait `ADMIN_LOGIN_LOCKOUT_MINUTES`, or restart gunicorn to clear the counters |
| Forgot admin password | `python manage.py changepassword admin` inside the venv |
