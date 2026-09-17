# Project setup for Tailwind Plus v4 in a plain HTML/CSS/JS app

## First: work out what the project already has

```bash
grep -rn "cdn.tailwindcss.com\|@tailwindcss/browser\|@import \"tailwindcss\"\|tailwindplus/elements" \
     --include=*.html --include=*.css --include=*.json . | grep -v node_modules | head
grep -rn "@theme" --include=*.css . | grep -v node_modules | head
```

- Found an `@import "tailwindcss"` stylesheet → v4 build exists. Add your page to
  its `@source` coverage and use its tokens. Nothing else to set up.
- Found `cdn.tailwindcss.com` → that is the **v3** Play CDN and it cannot compile
  these components. See the warning below before doing anything else.
- Found nothing → set up a v4 build (Option A) or the browser build for a
  throwaway mockup (Option B).

## The v3 Play CDN trap

`https://cdn.tailwindcss.com` is Tailwind **3**. Application UI v4 markup uses
v4-only syntax on nearly every line: `size-6`, `text-sm/6`, `inset-ring-1`,
`outline-1 -outline-offset-1`, `bg-white/10`, `data-closed:`, `not-dark:hidden`,
`in-aria-expanded:`, `w-(--button-width)`, `[--anchor-gap:--spacing(2)]`,
`transition-discrete`, `starting:`.

Under v3 those classes silently produce nothing. The page renders — unstyled
boxes, no dark mode, popovers with no transition — and looks like the component
is broken rather than the toolchain. If you find that script tag on a page you
are touching, say so and migrate the page to a v4 build; don't paste v4
components next to it and hope.

## Option A — Tailwind v4 CLI build (default for anything real)

```bash
npm i -D tailwindcss @tailwindcss/cli
npm i @tailwindplus/elements        # or use the CDN script tag
```

`src/app.css`:

```css
@import "tailwindcss";

/* Tailwind scans files it can reach from this stylesheet. Anything outside that
   tree — server-rendered templates, JS that builds class strings — must be
   listed, or its classes are dropped from the build. */
@source "../views/**/*.html";
@source "../js/**/*.js";

@theme {
	/* brand tokens — see references/theming.md */
}
```

`package.json`:

```json
{
	"scripts": {
		"build:css": "tailwindcss -i src/app.css -o public/css/app.css --minify",
		"watch:css": "tailwindcss -i src/app.css -o public/css/app.css --watch"
	}
}
```

Then `<link rel="stylesheet" href="/css/app.css" />` in the page.

The failure you will actually hit: a class used only in a template the build
never scanned. Symptom is one component styled and its neighbour bare. Fix is an
`@source` line, not more classes.

## Option B — browser build (mockups and one-off demos)

```html
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
```

Compiles in the browser, so there is a flash of unstyled content and a real
runtime cost. Fine for something you are about to show someone; move to Option A
before it ships. Theme it inline:

```html
<style type="text/tailwindcss">
	@theme { --color-indigo-600: #0e8a99; }
</style>
```

## Page skeleton

Application shells need height classes on the root elements; the component file
says which in its header comment, and `tpui.py requires <path>` prints them.
`tpui.py new` writes the whole skeleton for you.

```html
<!doctype html>
<html lang="en" class="h-full bg-white dark:bg-gray-900">
	<head>
		<meta charset="utf-8" />
		<meta name="viewport" content="width=device-width, initial-scale=1" />
		<title>…</title>
		<link rel="stylesheet" href="/css/app.css" />
		<script src="https://cdn.jsdelivr.net/npm/@tailwindplus/elements@1" type="module"></script>
	</head>
	<body class="h-full">
		<!-- shell -->
		<script type="module" src="/js/pages/dashboard.js"></script>
	</body>
</html>
```

Skip the height classes and a sidebar shell collapses to content height, leaving
a short stub of sidebar down the left. It is the most common "why does this look
wrong" with these shells.

## Suggested layout for a no-framework app

```
src/app.css              Tailwind entry: @import, @source, @theme
public/css/app.css       build output (gitignore it)
views/  or  public/      the HTML pages
public/js/pages/*.js     one ES module per page, <script type="module">
```

`@tailwindplus/elements` is a module, so load it with `type="module"`. Your own
page modules can be plain `<script type="module" src="…">` at the end of
`<body>`; they run after parse, so no `DOMContentLoaded` wrapper is needed.
