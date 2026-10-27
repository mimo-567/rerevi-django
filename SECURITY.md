# Security and private data

Never commit `.env` files, Django secret keys, SMTP passwords, Cloudflare tunnel credentials, certificates/private keys, databases, account exports, feedback, submissions, deletion receipts, logs or backups.

The public content snapshot uses an explicit field allowlist. It includes no user accounts, password hashes, sessions, feedback, admin notifications, import logs, private permission notes, content revision history or saved answers. Generate a new Django secret key for every installation. Keep private runtime directories outside the web root and Git checkout when deploying.

Email is disabled until the administrator configures their own SMTP settings and password. The password is saved outside the database in the private runtime directory. Do not place it in source code.

For a vulnerability, use GitHub's private vulnerability reporting if available, or contact **rerevi@zafirshirazi.com**. Do not post real keys, student data, answer links or deletion keys in a public issue.
