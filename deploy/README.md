# Deployment templates

These examples assume Linux, a dedicated `rerevi` service account, application code in `/srv/rerevi/app`, a virtual environment in `/srv/rerevi/venv`, and a private environment file at `/etc/rerevi.env` (mode 0600). Set the values for your own installation.

Create writable private directories `/var/lib/rerevi` and `/var/lib/rerevi-shares`, owned by the service account with mode 0700. Set `REREVI_DATA_DIR=/var/lib/rerevi` and `REREVI_SHARE_DIR=/var/lib/rerevi-shares`. Keep application code read-only to the service account, apart from collecting static files during deployment under controlled permissions.

Run migrations, import the public bank, create your own superuser and collect static files before starting Gunicorn. Enable the application service after checking all paths and ownership. The nginx example listens only on localhost; terminate HTTPS at your trusted reverse proxy or tunnel and route traffic to localhost:8080. Do not trust forwarded-protocol headers from arbitrary clients.

Enable the cleanup and notification timers. Notifications remain disabled until SMTP is configured. Back up the SQLite database using SQLite's backup API or an equivalent consistent backup method. Protect and rotate database backups, and exclude the separate shared-answer/mail storage from them.

Run the deployment checks from README.md, inspect generated PDFs and review your own public privacy/contact content before launch. No production tunnel token, private certificate, server password or default administrator is included.
