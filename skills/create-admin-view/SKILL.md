---
name: create-admin-view
description: Creates admin pages using Tailwind UI with the project's brand tokens. Use when creating new admin pages, dashboards, or management views.
---

# Create Admin View

> For all HTML/CSS/JS standards, the `frontend-master` agent is invoked automatically.
> **PROJECT-SPECIFIC: fill in the placeholders below (`{PROJECT_NAME}`, paths, brand colors, route helpers) before using this skill in a new project.**

Creates admin pages under `/{ADMIN_ROUTE_PREFIX}/` using Tailwind UI with the project's brand palette.

## Required Files

1. **HTML view**: `{VIEWS_DIR}/admin/{name}.html`
2. **CSS overrides**: `{STATIC_DIR}/css/pages/admin/{name}.css`
3. **JavaScript module**: `{STATIC_DIR}/js/pages/admin/{name}.js` (reuse existing or create new)
4. **Route**: Add to `{ROUTES_DIR}/admin_views.{ext}`

## Brand Theme Config

Every admin template includes the Tailwind CDN runtime with the project's brand extension. Replace the example tokens with the project's actual design tokens (search the existing stylesheets / design docs first — never invent new ones if they already exist).

```html
<script src="https://cdn.tailwindcss.com?plugins=forms"></script>
<script>
tailwind.config = {
	theme: {
		fontFamily: {
			sans: ['{FONT_FAMILY}', 'system-ui', 'Helvetica Neue', 'Arial', 'sans-serif']
		},
		extend: {
			colors: {
				primary:   { DEFAULT: '{PRIMARY}', dark: '{PRIMARY_DARK}', light: '{PRIMARY_LIGHT}' },
				secondary: { DEFAULT: '{SECONDARY}' },
				accent:    { DEFAULT: '{ACCENT}' },
				'brand-text': { DEFAULT: '{TEXT_PRIMARY}', secondary: '{TEXT_SECONDARY}' },
				'brand-bg':   { DEFAULT: '{BG_PAGE}', subtle: '{BG_SUBTLE}', card: '{BG_CARD}' }
				// add a numbered brand scale (50–900) if the project has one
			},
			boxShadow: {
				card: '{CARD_SHADOW}'
			}
		}
	}
};
</script>
```

## Color Usage Rules

| Intent | Use | Not |
|--------|-----|-----|
| CTA border / active nav | `border-primary` | raw Tailwind color (e.g. `border-indigo-600`) |
| CTA hover | `hover:bg-primary-dark` | raw Tailwind color |
| Focus ring | `focus:outline-primary` | raw Tailwind color |
| Page background | `bg-brand-bg` | raw slate/gray |
| Card background | `bg-brand-bg-card` | `bg-white` (acceptable fallback) |
| Primary text | `text-brand-text` | `text-gray-900` |
| Secondary text | `text-brand-text-secondary` | `text-gray-500` |
| Neutral borders | `gray-200/300/400` fine — no brand token needed |

## HTML Template

```html
<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>{Title} · {PROJECT_NAME} Admin</title>
	<link rel="icon" type="image/x-icon" href="/static/images/favicon.ico">
	<link rel="stylesheet" href="/static/css/{PROJECT_BASE_STYLESHEET}.css">
	<link rel="stylesheet" href="/static/css/admin-nav.css">
	<link rel="stylesheet" href="/static/css/pages/admin/{name}.css">
	<!-- Tailwind + brand config (see above) -->
</head>
<body class="min-h-screen bg-brand-bg font-sans text-brand-text antialiased">
	<div id="admin-header"></div>

	<main id="{name}-view" class="mx-auto max-w-7xl space-y-8 px-4 py-10 sm:px-6 lg:px-8">
		<!-- Page content -->
	</main>

	<script type="module" src="/static/js/pages/admin/{name}.js"></script>
</body>
</html>
```

## CSS Override File

`{STATIC_DIR}/css/pages/admin/{name}.css` — restyle shared elements rendered by JS (status chips, buttons, dropdown shells, modals). Keep selectors aligned with JS-generated markup.

## Route Pattern

> **PROJECT-SPECIFIC: pick the framework idiom that fits this project. Example uses FastAPI; adapt for Express, Rails, Django, etc.**

```python
@router.get('/{ADMIN_ROUTE_PREFIX}/{name}', response_class=HTMLResponse)
def {name_snake}_view(user: dict = Depends({AUTH_DEPENDENCY})):
	"""{Description}."""
	return get_view('admin', '{name}')
```

- Auth: read-only dependency for read views, admin-required dependency for management views
- Reuse whatever shared view-loading helper the project has (e.g. `get_view()`)

## Key Conventions

- **Tailwind UI + brand tokens** — no raw `indigo-*`, `blue-*`, `sky-*` (or other ad-hoc) color classes
- **Reuse existing JS modules** — same `<script type="module">` as the legacy page so all logic, fetches, and event wiring stay identical
- **Keep element IDs identical** to legacy views — modal IDs, table IDs, filter IDs, button IDs must match for JS handlers to attach
- **`<div id="admin-header"></div>`** — nav JS fills this; keep it as-is
- **Verify before merge**: grep for stray raw Tailwind color classes not from the brand palette
