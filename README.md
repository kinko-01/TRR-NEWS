# TRR NEWS

TRR NEWS is a Flask-based digital news platform evolved from the KINKO NEWS V1 codebase. It provides a public news website and a role-based newsroom for publishing articles, managing categories, moderating comments and managing users.

## Features

- Responsive public news homepage
- Breaking and featured stories
- Categories and paginated search/archive listings
- RSS feed at `/feed.xml` for news readers
- Related stories, share links and estimated reading time
- Article pages and comments with moderation
- Email/password registration and login
- Email/password login and registration (Google authentication temporarily disabled)
- Reader, journalist, editor and admin roles
- Role-aware article management
- Secure image uploads (JPG/PNG/WebP validation)
- Sanitized article HTML
- CSRF protection on state-changing forms
- Security headers and secure-cookie configuration
- Rate limiting for authentication and comments
- PostgreSQL-compatible SQLAlchemy configuration
- Database migrations with Flask-Migrate/Alembic
- Health endpoint at `/healthz`
- SEO metadata, canonical URLs, robots.txt and sitemap.xml
- Gunicorn deployment support

## Local development

1. Create and activate a virtual environment:

```bash
python -m venv .venv
# Windows PowerShell
.venv\\Scripts\\Activate.ps1
# macOS/Linux
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and set `SECRET_KEY`.

4. For local development, `AUTO_CREATE_DB=true` is convenient. Start the app:

```bash
python run.py
```

5. Create an administrator:

```bash
flask --app run.py create-admin
# If an administrator already exists and needs a password reset:
flask --app run.py reset-admin
```

6. Open `http://127.0.0.1:5000`.

## Production deployment

Set these environment variables:

```text
FLASK_CONFIG=production
SECRET_KEY=<long-random-secret>
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/trr_news
TRR_SITE_URL=https://trrnewstv.com
AUTO_CREATE_DB=false
SEED_SAMPLE_CONTENT=false
RATELIMIT_ENABLED=true
RATELIMIT_STORAGE_URI=redis://HOST:6379/0
SESSION_COOKIE_SECURE=true
REMEMBER_COOKIE_SECURE=true
GOOGLE_AUTH_ENABLED=false
# GOOGLE_CLIENT_ID=<future use>
# GOOGLE_CLIENT_SECRET=<future use>
```

Install dependencies and apply migrations:

```bash
pip install -r requirements.txt
flask --app run.py db upgrade
flask --app run.py seed
flask --app run.py create-admin
```

Start Gunicorn:

```bash
gunicorn --workers 3 --timeout 120 --bind 0.0.0.0:$PORT run:app
```

Put Gunicorn behind a TLS-enabled reverse proxy/load balancer. The application trusts one proxy hop via `ProxyFix`; only use this configuration when the deployment topology actually has one trusted proxy in front of the app.

### Google authentication

Google authentication is intentionally disabled in this early release. The Google routes remain as compatibility redirects, while the database `google_id` field is retained so Google sign-in can be restored later without a destructive database change.

### Uploads

Local uploads are supported for development. For production, mount `UPLOAD_FOLDER` on durable storage or migrate media to an object-storage/CDN architecture before operating at scale. Back up uploaded media separately from the database.

### Rate limiting

`Flask-Limiter` is enabled for authentication and comment submission. Use Redis (or another shared backend supported by Flask-Limiter) in a multi-worker production deployment; `memory://` is intended only for development/single-process use.

## Existing database migration

If you already have a KINKO NEWS database containing real data, **do not point production at the new schema blindly**. Take a full database backup first and create a data/schema migration plan. The included `0001_initial` migration is intended for a fresh database. Existing installations should be migrated deliberately after comparing their current schema.

## Security checklist before going live

- Set a unique strong `SECRET_KEY`.
- Use PostgreSQL and durable backups.
- Use HTTPS everywhere.
- Set secure cookies to true.
- Use Redis/shared rate-limit storage with multiple workers.
- Create an admin through the CLI; no default password is shipped.
- Restrict Google OAuth redirect URIs to your actual domains.
- Keep dependencies updated.
- Store uploads on durable storage and back them up.
- Monitor application logs and `/healthz`.
- Never commit `.env`, credentials, database files or uploaded media.

## Beginner maintenance guide

### Run locally
1. Open a terminal in the project folder.
2. Create a virtual environment: `python -m venv .venv`
3. Activate it on Windows: `.venv\Scripts\activate`
4. Install packages: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and set a strong `SECRET_KEY`.
6. Run: `python run.py` (the app loads `.env` from the project folder even if you launch it from another working directory).
7. Open `http://127.0.0.1:5000`.

### Backup before changes
Make a copy of the whole project folder and, in production, back up the database and uploaded images separately.

### Git basics
Use `git init`, commit working versions before changes, and create a branch for larger changes. Never commit `.env`, passwords, API keys, or production database files.

### Safe dependency updates
Create a backup, update one group of packages at a time, run the test suite with `pytest`, and only then deploy. Review major-version release notes before upgrading.

### Environment variables
Keep secrets in `.env` locally and in your hosting provider's environment settings in production. Do not paste secret keys into source files.

### Test before publishing
Run `pytest`, start the app locally, test login/logout, article creation/editing, image upload, search, categories, comments, and the public homepage on desktop and mobile widths.

### Deployment and rollback
Deploy only a tested commit. Keep the previous working release available so you can roll back if the new release fails. Database migrations should be backed up and tested before production migration.

### Troubleshooting order
- Frontend: inspect the browser console and page source/CSS.
- Backend: read Flask/Gunicorn logs and reproduce the URL locally.
- Database: test the connection and check migration status.
- Hosting: check service status, process health, memory, disk, and domain/SSL settings.
- Environment: compare required variables with `.env.example`.

### Security basics
Use HTTPS, a strong secret key, secure cookies in production, CSRF protection, least-privilege admin accounts, regular dependency updates, safe image validation, sanitized article HTML, and frequent backups.

### Pre-deployment checklist
- [ ] Tests pass
- [ ] Production `SECRET_KEY` is set
- [ ] `DEBUG` is off
- [ ] Database backup exists
- [ ] Uploads are backed up/persisted
- [ ] HTTPS and domain work
- [ ] Login/logout work
- [ ] Admin permissions are correct
- [ ] Public homepage/search/articles work
- [ ] Logs show no startup errors


### Reset an existing administrator password

Run `flask --app run.py reset-admin` from the project directory with the virtual environment active. Enter the administrator email, then enter and confirm a new password of at least 12 characters. The password is hidden while typing and is stored as a password hash. This command does not print or set a shared default password.


## Vercel preview deployment

This repository includes a Vercel-compatible Flask entrypoint (`wsgi.py`), a pinned Python runtime (`.python-version`), and browser assets mirrored under `public/static/` for CDN delivery.

Before deploying:

1. Push this project to a Git repository. Do not commit `.env` or real credentials.
2. Import the repository into Vercel. Vercel should detect the Flask app from `wsgi.py`; no custom build command or `vercel.json` is required for this layout.
3. In the Vercel project settings, add these environment variables for the Preview environment:
   - `FLASK_CONFIG=production`
   - `SECRET_KEY` = a new, private random value
   - `DATABASE_URL` = a managed PostgreSQL connection string
   - `TRR_SITE_URL` = your Vercel deployment URL (update after the first deployment if needed)
   - `AUTO_CREATE_DB=false`
   - `SEED_SAMPLE_CONTENT=false`
   - `SESSION_COOKIE_SECURE=true`
   - `REMEMBER_COOKIE_SECURE=true`
   - `GOOGLE_AUTH_ENABLED=false`
4. Deploy a preview.
5. Apply database migrations to the same PostgreSQL database from your own computer, using the project environment and `flask --app wsgi.py db upgrade`. Do not run migrations on every web request.

Important preview limitations:

- Vercel's function filesystem is not durable. This build stores temporary runtime files under `/tmp` and disables article image uploads on Vercel. Add a managed image-storage provider before enabling uploads.
- Do not use SQLite for a deployed Vercel site. Use managed PostgreSQL and keep its connection string private.
- The bundled public CSS and logo are copied to `public/static/` so Vercel can serve them as static assets.
- The app requires `DATABASE_URL` on Vercel; deployment will fail clearly if it is missing.
- This is a testing deployment configuration, not a complete production media-storage setup.

Official Vercel guidance: Flask applications are detected from supported entrypoints including `wsgi.py`; Flask static assets should be placed in `public/`, and uploaded media should be stored externally.
"# trr-news" 
