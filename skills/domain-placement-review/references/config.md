# Placement config

Each repo describes its own layout in `.claude/domain-placement.json`, on its default branch.
The skill and `scripts/consumers.py` read it from the base ref of a change, so a PR cannot loosen
its own rules. With no file the script guesses the layout. While it guesses, no finding blocks.

## Write one in five minutes

1. Run `python3 scripts/consumers.py layout --repo <repo>`. Copy its `effective` block into
   `.claude/domain-placement.json`.
2. Fix `shared` and `domains`, using the section below.
3. Run `census --repo <repo> --ref HEAD --all` and read it with the symptom table at the end.
   Every `SHARED` row should really be shared, and every `NONE` row really unused.

## Pick your domains

A **domain** is the code that one team or one product surface owns, the unit that should own its
helpers. It is not a technical layer. Three common shapes:

| Shape | Example tree | Config |
|---|---|---|
| Feature folders | `app/admin/…`, `app/dealer/…`, `app/shared/…` | `"shared": ["app/shared"], "domains": ["app/*"]` |
| Next.js app router | `src/app/admin/…`, `src/lib/…`, `src/components/…` | `"shared": ["src/lib", "src/components"], "domains": ["src/app/*"]` |
| Layers (Python or MVC) | `routes/billing.py`, `services/billing_service.py`, `utils/…` | `"shared": ["utils"], "moduleDomains": true`, so both billing files are domain `billing` |

When folders don't say it, name the domain from the path with a regex:
`"domains": [{"regex": "^src/(?P<domain>[a-z-]+)/"}]`.

## Fields

| Field | Default | What it does |
|---|---|---|
| `shared` | required | Folders that hold shared code. Everything under them is in the census. |
| `domains` | `[]` | Glob strings name folders (`"app/*"`: `app/admin/x.ts` is `admin`). `{"regex": "…(?P<domain>…)…"}` names a domain from the path. |
| `moduleDomains` | `false` | A file no other rule covers becomes a domain named after the file, without layer suffixes (`_service`, `-routes`, …). For layered layouts. |
| `notDomains` | `[]` | Folders that are neither a domain nor shared, such as generated code. They are not counted. |
| `ignore` | tests, e2e, scripts, docs, fixtures, migrations, vendor, build output | More globs to skip. They add to the defaults. A test never counts as a consumer. |
| `include` | `[]` | Globs that override `ignore`, as in `"include": ["scripts/**"]` when scripts are real code. |
| `roots` | `[]` | The app's entry points (globs), such as `src/main.ts` or `backend/main.py`. A shared file that only they reach is `ROOT`. |
| `compositionRoots` | `[]` | Shared files that wire domains together, such as a route registry or a cron table. They do not count as consumers. |
| `urlRoots` | `{}` | URL prefix → folders served under it, as in `{"/js/": ["app/*/js", "app/shared/js"]}`. Client imports and `<script src>` resolve through it. |
| `references` | `[]` | Uses by name instead of by import. Each entry has `targets` (a glob of files) and `pattern`, a regex with `{stem}` or `{name}`. Optional: `strip`, a regex removed from the stem, such as `_v\\d+$`; and `in`, a glob limiting where to look. Point `targets` at the domains' template folders too, so a partial moved out of shared still links to the domains that include it. |
| `aliases` | `{}` | Import aliases, as in `{"@shared/*": ["app/shared/*"]}`. `compilerOptions.paths` in `tsconfig.json` or `jsconfig.json` is read too. |
| `justified` | `[]` | `{"path": glob, "why": text}`. The documented homes and platform files: shared on purpose, with a reason. Only list a file the census would otherwise call SINGLE, NONE or ROOT. Its row keeps `would_be`, and a diff asks `JUSTIFIED_LOST` when that gets worse. A PR that adds a line turns its own block into a question for the reviewer. |
| `planned` | `[]` | `{"path": glob, "ticket": text, "to": text}`. Decided moves of today's debt. The row says "planned in <ticket>: <to>" instead of a generic hint, and nothing blocks on it. `census --ticket <ticket>` prints one card's worklist; an entry that matches no file means the move is done. |
| `unit` | `"file"` | `"export"` also checks every export of a shared file. One that only one domain uses blocks (`EXPORT`). |
| `askExports` | `false` | With `unit: "file"`, one question per shared file a change touches (`EXPORT_ASK`), listing exports exactly one domain uses that are new or just lost a user. Exports only tests use, TypeScript types, and exports that were already single-consumer stay quiet. |
| `pythonRoots` | `[""]` | Folders where absolute Python imports start, as in `["backend"]` for `from utils.x import y` inside `backend/`. |
| `basenameFallback` | `false` | If a relative import does not resolve, match it to the one file with the same name. On when guessing. |
| `scanExtensions` | `[]` | More file types to scan for `references`. |
| `rules` | `[]` | The repo's docs on placement. The reviewer quotes them, and a change that edits them gets a question. |
| `notes` | `[]` | Plain-text guidance for the reviewer: how this repo counts, and what is still open. |
| `examples` | `[]` | `{"commit", "verdict", "why"}`: real calls used to calibrate the reviewer. |

The parser reads JS/TS, Python and HTML-like templates. Other languages (Dart, Go, Ruby, …) are
listed as "not parsed" and need a human check.

## Examples

Feature folders with templates included by name, and client code served flat at `/static/`:

```json
{
	"shared": ["src/common"],
	"domains": ["src/*"],
	"notDomains": ["src/generated"],
	"roots": ["src/main.ts"],
	"compositionRoots": ["src/common/routes.ts"],
	"urlRoots": {"/static/": ["src/*/client", "src/common/client"]},
	"references": [
		{"targets": "src/*/views/*.njk", "pattern": "\\binclude\\s*\\(\\s*['\"]{stem}(?:\\.njk)?['\"]"}
	],
	"justified": [
		{"path": "src/common/db.ts", "why": "platform: one pool for the whole app"},
		{"path": "src/common/mail/templates/**", "why": "the only folder the mailer reads"}
	],
	"rules": ["docs/architecture.md"]
}
```

A layered Python service with its code under `backend/`:

```json
{
	"shared": ["backend/utils"],
	"moduleDomains": true,
	"pythonRoots": ["backend"],
	"roots": ["backend/main.py"],
	"notDomains": ["backend/models"],
	"justified": [{"path": "backend/utils/logging_config.py", "why": "platform: every module logs through it"}]
}
```

## Symptoms

| You see | Usually | Fix |
|---|---|---|
| Many `NONE` rows in Python | Imports start below the repo root | Set `pythonRoots`. |
| Many `NONE` rows for templates or client JS | They are used by name or by URL | Add `references` or `urlRoots`. |
| Every `SINGLE` row names the same domain | The domain glob is too shallow, as with `src/*` in a Next app | Use the deeper folder, `src/app/*`. |
| Layers (`routes`, `services`) show up as domains | A layered layout | Use `moduleDomains: true` and drop the folder glob. |
| `not counted: N ignored` covers real code | A default ignore matched it | Add it to `include`. |
| A known hub makes every file it touches `KEEP` | Fine: rule 2 | If the hub itself is misplaced, list it in `justified` with the reason or move it. |
