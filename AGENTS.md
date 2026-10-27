# ReRevi Django contributor instructions

This is the standalone Django/SQLite ReRevi application for Eduqas GCSE Religious Studies Route A, Christianity and Islam. See README.md, NOTICE.md and SECURITY.md before making changes.

- Keep credentials, databases, submissions, feedback and runtime files out of Git.
- Never read a production environment file or database into a public export. Use explicit content-field allowlists.
- Preserve the user's choice to omit additional practice, original-year Part A selection, self-marking guidance and optional SPaG.
- Preserve the 30-day limit for shared answers and private deletion controls.
- Keep administrator submission listings limited to name, date and deletion controls.
- Keep this repository focused on RE. English/History prototypes are not included.
- Keep source and scheme attribution. Third-party resources retain their own rights; AGPL applies to the software.
- Make local changes reviewable; do not deploy or publish unrelated changes.
