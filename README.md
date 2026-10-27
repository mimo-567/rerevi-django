# ReRevi

An interactive practice-paper and worksheet builder for **Eduqas GCSE Religious Studies Route A**, covering Component 1, Christianity and Islam.

Created by **Zafir Shirazi**. [Use ReRevi](https://rerevi.zafirshirazi.com) · [Source](https://github.com/mimo-567/rerevi-django) · [Attribution](NOTICE.md)

This is the current **Django application**, published separately from the earlier Astro/Supabase project. It contains RE only. English and History prototypes are not included.

## What it does

- Choose focused practice, keyword practice or a full practice paper.
- Select original-year Part A questions when practising a particular paper year.
- Build worksheets from the question bank and optionally omit additional practice.
- Type answers, use a timer, reveal marking guidance and self-mark with optional SPaG where applicable.
- Download question/answer and marking PDFs in ReRevi or Eduqas-inspired layouts.
- Export/import `.rerevi` files to reopen a practice set, optionally including your work.
- Optionally share answers using expiring private links, with separate deletion controls.
- Manage questions, resources, announcements, Markdown articles, FAQs and feedback through Django admin.

There is no live AI question generation or automatic grading. Some bundled additional practice was AI-assisted and is labelled separately from official questions.

## Included content

The initial public snapshot contains **547 questions, 51 keywords, six marking rubrics and eight attributed resource collections**. Official papers, schemes, glossary and supporting reference files are in `resources/`; booklet templates and question mappings are in `practice/data/`.

The project owner has requested inclusion of the educational material and states that permission has been obtained. **AGPL licenses the software, not third-party papers or questions.** Those retain their original rights and credits. See [NOTICE.md](NOTICE.md) before redistributing educational material.

No production database, accounts, password hashes, SMTP settings, tunnel credentials, submissions, feedback, private admin notes or unpublished articles are included.

## Stack

Python 3.12+, Django 5.2, SQLite, Gunicorn, ReportLab, pypdf, Markdown and plain JavaScript/CSS. The application is designed for Linux. The pinned dependencies reflect the production environment at the release date; `requirements.txt` lists supported dependency ranges.

## Run locally

```bash
git clone https://github.com/mimo-567/rerevi-django.git
cd rerevi-django
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
cp .env.example .env
python -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Put the generated value in `DJANGO_SECRET_KEY` in your private `.env`. Load the environment and initialise your own database:

```bash
set -a
source .env
set +a
python manage.py migrate
python manage.py import_public_bank
python manage.py createsuperuser
python manage.py collectstatic --noinput
python manage.py check
python manage.py runserver
```

Open `http://127.0.0.1:8000/`; admin is at `/admin/`. You create your own administrator and password. There is no bundled default login. Imports preserve existing admin edits when rerun. Do not load a production database to seed a new installation.

## Configure your installation

`.env` is a shell-compatible example; Django reads process environment variables, not the file automatically. Keep production environment files outside the checkout.

| Setting | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Unique random signing/session key. Required. |
| `DJANGO_DEBUG` | Set `false` in production. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames for your installation. |
| `DJANGO_CSRF_ORIGINS` | Comma-separated HTTPS origins in production. |
| `REREVI_PUBLIC_BASE_URL` | Your canonical URL, used in links and emails. |
| `REREVI_DATA_DIR` | Private database/cache/mail directory; defaults to `var/`. |
| `REREVI_SHARE_DIR` | Private expiring answer/mail queue storage, separate from database backups. |
| `REREVI_RESOURCE_ROOT` | Bundled reference files; defaults to `resources/`. |
| `REREVI_SUPPORT_EMAIL` | Your installation's public contact address. |
| `REREVI_SOURCE_URL` | Corresponding source for your running version, including your modifications. |

Review the editable **About & privacy page, footer, announcements and FAQs** in admin before inviting users. Original migration text describes the original service; customise it for your own operator, contact details, hosting and email processors.

Optional email settings are listed in `.env.example`. Set your own SMTP host, port, username, sender and recipient, then enter the password and enable email under **Admin → Owner email notifications**. No credentials are shipped. Run `python manage.py deliver_notifications` regularly to process the queue.

Run `python manage.py purge_shares` at least hourly using a scheduler. Shared answers expire within 30 days; keep that storage and mail queues out of database backups. Downloaded practice files are held by their recipients and do not automatically expire.

## Production

Use a dedicated unprivileged service account, HTTPS, a private environment file and Gunicorn behind a reverse proxy. Example units and proxy configuration are in [`deploy/`](deploy/). They are templates, not an installer that changes an existing server. Configure your own hostname, filesystem ownership, backups and Cloudflare tunnel if used.

Run `python manage.py check --deploy` with your production environment. Never expose `var/`, mail queues, backups, environment files or answer snapshots through the static-file server. Never run the Django development server publicly.

## Contributing and licensing

Software © 2026 Zafir Shirazi, licensed under **GNU AGPL-3.0-only**. When you offer a modified version over a network, provide its corresponding source as required by the licence. Keep the source-code link accurate for your deployment.

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) and [NOTICE.md](NOTICE.md). ReRevi was inspired by [re.ibzz.uk](https://re.ibzz.uk), another useful revision resource to use alongside it.
