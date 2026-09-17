# Theming Tailwind Plus components

Every component ships indigo as the accent and a full set of `dark:` variants.
Roughly 7,400 indigo class occurrences live across the library, so how you
rebrand matters more than it looks.

## Which shades the library actually uses

| Shade | Uses | Typical role |
|---|---|---|
| 50 / 100 / 200 / 300 | ~515 | soft fills, text on dark brand surfaces |
| 400 | 795 | accent text/icons in dark mode |
| 500 | 2396 | primary fill in dark mode, focus outlines |
| 600 | 3232 | primary fill and accent text in light mode |
| 700 | 208 | hover on the 600 fill |
| 800 / 900 / 950 | 220 | brand sidebar backgrounds |

The light/dark pairing is consistent: **600 in light, 500 in dark** for fills;
**600 in light, 400 in dark** for accent text. Preserve that pairing whatever
you rename things to, or dark mode loses contrast.

## Approach 1 — remap the indigo scale (default)

Tailwind v4 utilities read their values from theme variables, so redefining the
indigo ramp retints every component at once and lets you paste component markup
in verbatim, forever. No find-and-replace, no drift when you copy the next
component next month.

```css
/* app.css */
@import "tailwindcss";

@theme {
	/* Brand ramp mapped onto the scale Tailwind Plus already uses. */
	--color-indigo-50:  #f2f7f8;
	--color-indigo-100: #d9edf0;
	--color-indigo-200: #b3dbe1;
	--color-indigo-300: #7cc2cd;
	--color-indigo-400: #3fa3b4;
	--color-indigo-500: #1f8a9c;   /* dark-mode fill  */
	--color-indigo-600: #0e8a99;   /* light-mode fill */
	--color-indigo-700: #0b6e7a;   /* hover on 600    */
	--color-indigo-800: #0a5a64;
	--color-indigo-900: #0a4a52;
	--color-indigo-950: #063137;
}
```

Fill in all eleven steps. Half a ramp gives you a page that is brand-coloured in
places and indigo in others, which reads as a bug.

If you only have one brand hex, generate the ramp by holding hue and chroma and
walking lightness — `oklch()` makes this easy and is fully supported in v4:

```css
@theme {
	--brand-h: 191;             /* hue of your brand colour */
	--color-indigo-600: oklch(0.55 0.09 var(--brand-h));
	--color-indigo-500: oklch(0.62 0.09 var(--brand-h));
	/* …and so on */
}
```

Say out loud in a comment that indigo now means "brand", so the next person
doesn't think the page is unthemed.

## Approach 2 — semantic tokens

Better when the project already has named tokens (`--color-brand`,
`--color-night`) or when several accents coexist. Define the tokens, then
rewrite the accent classes as you paste each component:

```css
@theme {
	--color-brand: #0e8a99;
	--color-brand-hover: #0b6e7a;
	--color-brand-on-dark: #1fc3d8;
	--color-brand-fg: #ffffff;
}
```

| Component class | Becomes |
|---|---|
| `bg-indigo-600` | `bg-brand` |
| `hover:bg-indigo-500` / `hover:bg-indigo-700` | `hover:bg-brand-hover` |
| `text-indigo-600` | `text-brand` |
| `dark:bg-indigo-500`, `dark:text-indigo-400` | `dark:bg-brand-on-dark`, `dark:text-brand-on-dark` |
| `outline-indigo-600` / `dark:outline-indigo-500` | `outline-brand` / `dark:outline-brand-on-dark` |

Use an existing project token if one already exists — grep the stylesheet for
`@theme` before inventing a name. Two tokens meaning the same colour is the
thing that actually rots a design system.

Leave the neutrals alone. `gray-*`, `green-*` for success, `red-*` for danger
and `yellow-*` for warning are load-bearing across alerts, badges and form
errors; retinting them makes states unreadable.

## Dark mode

Components carry `dark:` on every surface, so dark mode works for free under
`prefers-color-scheme`. Two other cases:

**Class-toggled dark mode** — add the variant, then toggle `.dark` on `<html>`:

```css
@custom-variant dark (&:where(.dark, .dark *));
```

**No dark mode at all** — some apps pick light or dark per surface instead. The
`dark:` classes are then inert, and stripping them from thousands of lines buys
you nothing but merge pain. Leave them, and pick the shell that already matches
the surface you want (`02-simple-dark-sidebar.html` for a permanently dark app).

## Typography

The library assumes Tailwind's default `font-sans`. To change it globally:

```css
@theme {
	--font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
}
```

Keep the `text-sm/6`, `text-xs/6` line-height pairings from the components —
they are tuned to the spacing in the markup, and overriding them is how a
carefully spaced table starts looking cramped.

## Checking your work

```bash
grep -o 'indigo-[0-9]*' page.html | sort | uniq -c   # expect none under approach 2
grep -c 'dark:' page.html                             # dark variants survived the edit
```
