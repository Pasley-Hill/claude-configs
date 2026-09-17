---
name: tailwind-plus-app-ui
description: Build application UI from the licensed Tailwind Plus (Tailwind UI) Application UI v4 HTML component library installed on this machine — for vanilla HTML/CSS/JS apps with no JS framework. Use this whenever the user wants an app screen or any part of one: dashboard, admin page, settings screen, internal tool, data table, form layout, modal, drawer, sidebar, navbar, tabs, stats row, empty state, command palette, page header, pagination, dropdown, badge, alert. Use it whenever Tailwind, Tailwind UI, Tailwind Plus, Tailwind components, or application-ui-v4 is mentioned, even in passing. Use it before hand-writing Tailwind markup for an app screen — the licensed components almost certainly already cover it, and writing markup from memory throws away work the user paid for.
---

# Tailwind Plus Application UI v4

A licensed library of 364 production HTML components — application shells,
tables, forms, overlays, navigation — built for Tailwind CSS v4 with
`@tailwindplus/elements` for interactivity. The user paid for it and builds
plain HTML/CSS/JS apps with it.

**The components are not bundled with this skill.** They are licensed, so this
skill ships only the index and the tooling; the download lives on the machine.
Resolution order for the library root:

1. `--root` passed to `tpui.py`
2. `$TAILWIND_PLUS_UI`
3. `~/repos/application-ui-v4`

Confirm it is there before doing anything else:

```bash
python3 scripts/tpui.py list
```

If that errors, the library isn't installed or isn't where the skill expects.
Ask the user where their Tailwind Plus Application UI v4 download is, then use
`--root <path>` for the session and suggest they make it permanent:

```bash
echo 'export TAILWIND_PLUS_UI=/path/to/application-ui-v4' >> ~/.bashrc
```

Don't work around a missing library by writing the markup from memory — that
produces exactly the generic output this skill exists to prevent. Say it's
missing and ask.

The root is the folder containing `html/` (and usually `react/` and `vue/`).
Components live under `html/`; ignore the framework folders unless the project
actually uses that framework. All component paths below are relative to `html/`.

**Helper:** `scripts/tpui.py` in this skill directory — `list`, `search`,
`show`, `requires`, `new`.

## The one rule that matters

Read the component file and paste its markup. Do not write Tailwind Plus-looking
markup from memory.

Each file encodes things you will not reproduce by hand: Tailwind v4 syntax
(`size-6`, `inset-ring-1`, `outline-1 -outline-offset-1`, `text-sm/6`), a
complete second palette of `dark:` variants, `sr-only` labels and ARIA wiring,
the mobile/desktop split, and transition states (`data-closed:`, `data-enter:`)
that the web components drive. Markup written from memory looks approximately
right and is wrong in all of those ways — which is exactly the difference the
user paid for.

Copy verbatim, then edit the copy: content, colors, and the bits the comments
tell you to choose between.

## Workflow

**1. Find out what the project already has.** Existing Tailwind build? Brand
tokens in `@theme`? A page already built this way to match? Read one before
writing a new one — matching the house style beats matching the library.
`references/setup.md` has the detection commands and what each answer means.

**2. Pick a shell, unless you are adding to an existing page.**

```bash
python3 scripts/tpui.py list application-shells
python3 scripts/tpui.py new application-shells/sidebar/03-sidebar-with-header.html \
    --out views/dashboard.html --title "Dashboard · Acme"
```

`new` writes a complete document: doctype, the `<html>`/`<body>` classes that
shell requires, stylesheet link, the elements script, and the shell markup.

Which shell: **sidebar** for an app with more than ~5 destinations (persistent
nav, best for dense tools), **stacked** for a handful of top-level sections or a
marketing-adjacent app, **multi-column** when a screen needs a third rail
(filters, activity, detail). Dark variants exist for each.

**3. Fill the content slot with components, top to bottom.** A page is normally
a page heading, then sections, then overlays at the end of `<body>`:

```bash
python3 scripts/tpui.py list data-display/stats      # see every variant first
python3 scripts/tpui.py show data-display/stats/01-with-trending.html
```

Paste each one into the `<!-- Your content -->` slot in document order. Overlays
(`overlays/*`) go as siblings at the very end of `<body>`, not nested in the
content — they are `popover`/`<dialog>` elements and position themselves.

**Pick the variant that carries the information, not the first one listed.**
Each category is a set of variants, numbered roughly plainest-first. Listing the
category and picking `01-simple` is the single easiest way to produce a page
that is technically correct Tailwind Plus and still looks thinner than something
hand-written — because the hand-written version would have added the trend line,
the avatar, the sub-label, the footer count, without thinking about it.

So ask what the screen needs to *say*, then find the variant that says it:

| The screen needs… | Reach for |
|---|---|
| a metric that moved | `data-display/stats/01-with-trending` (delta + direction), not `02-simple` |
| a metric with a category icon | `data-display/stats/04-with-brand-icon` |
| rows about people | `lists/tables/09-with-avatars-and-multiline-content` — avatar, name, secondary line |
| rows with a totals line | `lists/tables/15-with-summary-rows` |
| a table on phones | `lists/tables/07-with-stacked-columns-on-mobile` or `08-with-hidden-columns-on-mobile`; the plain table just overflows sideways |
| more rows than fit | a `navigation/pagination/*` footer under the table |
| a list with actions per row | `lists/stacked-lists/05-with-inline-links-and-actions-menu` |
| identity in the page header | `headings/page-headings/08-with-avatar-and-actions` or `13-with-logo-meta-and-actions` |

Two things the shells give you that are easy to leave empty: the **logo slot**
at the top of every sidebar and navbar (point it at the project's mark — a bare
text wordmark where a lockup belongs is the most visible tell that a page is
half-finished), and the **user block** pinned at the bottom of the sidebar.

`tpui.py list <category>` before you choose costs one command and is the
difference between a page that looks bought and a page that looks built.

**4. Make it the project's, not the library's.** Three passes, all of which
matter more than they sound:

- *Content* — every string, number, name and image in these files is filler.
  Replace it with the real thing, or with realistic domain data if the real
  thing isn't available yet. A dashboard still saying "Tom Cook" and
  "Heroicons" reads as unfinished no matter how good the layout is.
- *Colour* — the library is indigo. Retint it to the project's brand
  (`references/theming.md`). Leave neutrals and the green/red/yellow state
  colours alone.
- *Behaviour* — wire the current nav item, the form targets, the data.

**5. Look at it in a browser.** Build the CSS, serve the project over HTTP, and
screenshot the page — reading the markup back does not tell you that a table
overflows on a phone or that a logo slot is empty.

```bash
npm run build:css                       # a page the build never scanned has no styles
python3 -m http.server 8000 -d public   # serve the real project; file:// blocks ES modules
chromium --headless --disable-gpu --hide-scrollbars --virtual-time-budget=15000 \
    --window-size=1440,1400 --screenshot=/tmp/page.png http://127.0.0.1:8000/index.html
```

Then read the PNG. Check it at `--window-size=420,900` too, and in light mode —
headless Chromium reports `prefers-color-scheme: dark` by default and ignores
`--force-prefers-color-scheme`, so pass `--blink-settings=preferredColorScheme=1`
to see the light theme.

Serve and screenshot the real files. Inlining the CSS or rewriting asset paths
to make a "self-contained" copy hides the very breakage you are looking for.

## Placeholder checklist

These strings ship in the components. Grep for them before you call a page done;
each one left behind is a visible tell.

```bash
grep -nE 'Tom Cook|Your Company|Lindsay Walton|Front-end Developer|lindsay.walton@|Heroicons|Workcation|Tailwind Labs|example\.com|images\.unsplash\.com|tailwindcss\.com/plus-assets|href="#"' page.html
```

- `tailwindcss.com/plus-assets/img/logos/mark.svg` — the logo, twice per shell
  (a `dark:hidden` light version and a `not-dark:hidden` dark one). Point both
  at the project's mark, or drop one if the mark works on both backgrounds.
- `images.unsplash.com/...` avatars — real user photos, or use
  `elements/avatars/08-circular-avatars-with-placeholder-initials.html`.
- `href="#"` — every link. Dead links in a shipped nav are a bug, not a stub.
- The people, companies and dollar amounts in tables and lists.

## Icons

Icons are inline Heroicons SVGs marked `data-slot="icon"`. Sizes are conventional:
`size-6` with `stroke-width="1.5"` on 24×24 outline icons (nav, headers),
`size-5` on 20×20 solid icons (buttons, inline).

Need a different icon: take the `<svg>` from another component in the library
that uses it (`tpui.py search <concept>`), or copy the path data from
heroicons.com. Do not hand-write path data — a wrong `d` attribute renders as a
scribble and is tedious to debug.

## Current / active states

Components document their state classes in an HTML comment right above the
element:

```html
<!-- Current: "bg-gray-50 text-indigo-600", Default: "text-gray-700 hover:..." -->
```

Apply the Current classes to the active item, Default to the rest, add
`aria-current="page"`, and delete the comment — it is instructions to you, not
documentation for the project.

## Category map

50 categories under `html/`. `tpui.py search` is usually faster than browsing;
`references/catalog.md` lists every file if you want the whole shape at once.

| Area | Categories |
|---|---|
| Page frame | `application-shells/` sidebar · stacked · multi-column |
| Headings | `headings/` page-headings · card-headings · section-headings |
| Data | `lists/` tables · stacked-lists · grid-lists · feeds<br>`data-display/` stats · description-lists · calendars |
| Forms | `forms/` form-layouts · input-groups · select-menus · comboboxes · checkboxes · radio-groups · toggles · textareas · action-panels · sign-in-forms |
| Navigation | `navigation/` navbars · sidebar-navigation · vertical-navigation · breadcrumbs · tabs · pagination · progress-bars · command-palettes |
| Overlays | `overlays/` modal-dialogs · drawers · notifications |
| Feedback | `feedback/` alerts · empty-states |
| Small parts | `elements/` buttons · button-groups · badges · avatars · dropdowns |
| Layout | `layout/` cards · containers · list-containers · media-objects · dividers |
| Whole pages | `page-examples/` home-screens · detail-screens · settings-screens |

`page-examples/` are complete assembled pages. When a request matches one
("build me a settings page"), start there instead of composing from parts — it
is already a worked example of how these pieces fit together.

## Interactivity

Dropdowns, modals, drawers, selects, comboboxes, disclosures, tabs and command
palettes are driven by `@tailwindplus/elements` custom elements (`el-dropdown`,
`el-dialog`, `el-select`, …) plus native `command`/`commandfor` buttons. Keep
that markup rather than replacing it with your own click handlers — it already
does focus trapping, keyboard nav, ARIA and anchored positioning.

Read `references/elements.md` before editing any `el-*` markup or when a
component's interactive part needs to change.

Your own JS still handles: data fetching and rendering, table sort/filter,
form submission, and inserting toasts into the notification live region.

## References

- `references/setup.md` — detecting or creating the Tailwind v4 build; the v3
  Play CDN trap; page skeleton; file layout. Read when starting a project or
  when styles aren't applying.
- `references/theming.md` — rebranding off indigo, dark mode, fonts. Read
  before the colour pass.
- `references/elements.md` — the `@tailwindplus/elements` API and state
  variants. Read when touching interactive components.
- `references/catalog.md` — all 364 components by category.
