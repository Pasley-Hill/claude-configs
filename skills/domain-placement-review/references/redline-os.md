# redline-os pack

Base branch: `dev`, unless the PR says otherwise.

Source rules, to quote from `origin/dev` when citing:
- ADR-009 (`docs/adr/adr-009-domain-packages.md`): §1 placement by URL owner, §2 rule of two,
  §3 import direction, §7 admin is one domain, and OW-3 "anything shared code needs must
  itself be shared".
- `AGENTS.md`: #7 says promote instead of adding an allowlist line — that assumes a real
  second consumer. #9 covers asset slots.

## Counting

- Domains are the entries of `UI_DOMAINS` in `app/shared/server/domains.ts`. `app/server.ts`
  is root, not a domain. Tests, `e2e/` and `scripts/` don't count.
- Code files: match the import path, `['/]name\.(ts|mjs)['"]`. Client imports are URL-tree
  relative, so `./x.mjs` from `app/admin/js/` can be `app/shared/js/x.mjs`.
- Views, partials and mail templates: match the quoted name, `['"]name['"]`. Quotes can be
  single or double. The call (`include`, `render*`, `renderMailTemplate`,
  `readMailTemplate`) may sit on the line above.
- Script tags: `"/js/name.mjs"`.
- Prompts (`shared/server/prompts/*_vN.md`) are loaded by folder scan. Count the callers of
  `getPrompt` for that family.
- Repeated file names — resolve the full path: `db.ts`, `routes.ts`, `teammate-reminder.ts`,
  `unsubscribe.ts`, `first-month-share.ts`, `roi.mjs`, `nav-progress.mjs`.
- A consumer reached only through a composition root (`register-domains.ts`,
  `cron/cron-jobs.ts`, `messaging/sms-hooks.ts`) is not a second domain.
- `scripts/check-import-boundaries.mjs` checks server imports only. Client code, templates and
  render calls are yours to check.

## Documented homes → JUSTIFIED

- Mail templates in `shared/server/messaging/templates/`, the only folder `load-template.mjs`
  reads.
- Pure isomorphic `.mjs` (runs in node and the browser) in `app/shared/*.mjs`, the only served
  slot (AGENTS.md #9).
- Feeds S3 helpers in `shared/server/s3.ts`, and `app/feeds/` owning `/admin/feeds`
  (`docs/incoming-data-feeds/incoming-data-feed-formal-spec.md` §9).
- Digest senders with no domain, in `shared/server/digests/` (ADR-009 OW-3).
- Platform plumbing at the `shared/server/` flat root (router, db, auth, render…).

## Open → NEEDS-ANSWER

- New assistant engine code in `shared/server/assistant/`. ADR-014 §3 would move it to
  `app/assistant/`, but ADR-014 is still Proposed.

## Examples

MISPLACED:
- f0a5817a moved the teammate reminder, its cap and `recipients.ts` into
  `shared/server/messaging/` for an assistant tool that never imported them. Dealer is still
  the only consumer. Promote in the PR that adds the second consumer.
- 7c8e7a84 deleted the issue-photo callers. That left `shared/js/photo-upload.mjs` with one
  consumer, `admin/js/admin-dealership-documents.mjs`, so the file goes to `app/admin/js/`.
- `shared/server/photo-lite-ready-notify.ts`: all 3 importers are admin, and it imports only
  shared code, so it goes to `app/admin/`.

JUSTIFIED:
- 931cb596 `shared/server/client-ip.ts` replaced private copies in root, `cs` and `marketing`.
- 3b3eb390 kept the Photo Lite status labels domain-local
  (`app/photo-lite/photo-lite-status-labels.mjs`): proximity beats promotion.
