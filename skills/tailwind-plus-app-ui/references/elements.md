# @tailwindplus/elements

Tailwind Plus v4 components ship their interactivity as framework-free web
components in one script. Load it once per page, near the top of `<head>`:

```html
<script src="https://cdn.jsdelivr.net/npm/@tailwindplus/elements@1" type="module"></script>
```

Or `npm i @tailwindplus/elements` and `import '@tailwindplus/elements'` from your
bundle. The library is licensed the same as the components.

These elements handle focus trapping, keyboard navigation, ARIA wiring, scroll
locking and anchor positioning. Hand-rolling any of that costs you a day and
lands worse, so keep the `el-*` markup instead of rewriting it as `onclick`
handlers — that is the single most common way a Tailwind Plus page gets
downgraded.

## Opening and closing things: `command` / `commandfor`

Native HTML invoker commands. The button names a target by id and an action;
no JavaScript of yours is involved.

```html
<button type="button" command="show-modal" commandfor="sidebar">Open</button>
<button type="button" command="close"      commandfor="sidebar">Close</button>
<button type="button" command="--toggle"   commandfor="mobile-menu">Menu</button>
```

- `show-modal` / `close` — for a native `<dialog>` (used by `el-dialog`, drawers, modals).
- `--toggle` — custom command, used by `el-disclosure`.

To open or close from your own JS, call the native API on the target:
`document.getElementById('sidebar').showModal()` / `.close()`.

## Elements, and the markup shape each expects

**`el-dialog`** wraps a native `<dialog id="…">`. Inside it, `el-dialog-backdrop`
is the dimmer and `el-dialog-panel` is the animated panel. Used by application
shell mobile sidebars, `overlays/modal-dialogs/*` and `overlays/drawers/*`.

**`el-dropdown`** wraps a trigger `<button>` plus an `el-menu`. The menu needs
both `popover` and `anchor="bottom end"` (any `top|bottom|left|right` +
`start|end|center`). Gap is set with the `[--anchor-gap:--spacing(2)]` class.

**`el-select`** is a styled replacement for `<select>`. It takes `name` and
`value`, submits with a form like a native control, and contains a trigger
`<button>` holding `el-selectedcontent`, then `el-options` (`popover` +
`anchor`) holding `el-option value="…"` children. `w-(--button-width)` on
`el-options` makes the list match the trigger width.

**`el-autocomplete`** is the combobox: an `<input>` plus `el-options` /
`el-option`. Filtering as you type is built in — you supply the full option
list in the markup. `w-(--input-width)` matches the input width.

**`el-disclosure id="…" hidden`** is a show/hide region driven by
`command="--toggle"`. Mobile navs use it. Keep the `hidden` attribute — the
element manages it.

**`el-tab-group`** with `el-tab-list` (buttons) and `el-tab-panels` (divs).
Selection is exposed as `aria-selected`, which the classes style via
`aria-selected:`. Note most of `navigation/tabs/*` are plain links, not this.

**`el-command-palette`** with `el-command-list`, `el-command-group`,
`el-command-preview for="…"`, `el-no-results` and `el-defaults` (what shows
before any query). Lives in `navigation/command-palettes/*`.

**`el-popover`** — an anchored popover panel, same `popover` + `anchor` pattern
as `el-menu`.

## Styling states

The elements set attributes; Tailwind v4 variants read them. Keep these classes
when you copy markup — dropping them is what makes a panel appear with no
transition or a checkmark show on every row.

| Variant | Fires when |
|---|---|
| `data-closed:` | element is closed (start/end of the transition) |
| `data-enter:` / `data-leave:` | during the opening / closing transition |
| `data-open:` | element is open |
| `aria-selected:` | selected option or tab |
| `group-aria-selected/option:` | on a child of a selected `el-option` |
| `in-aria-expanded:` / `not-in-aria-expanded:` | inside an expanded/collapsed control (hamburger↔X icon swap) |
| `starting:` | native `@starting-style`, used by toasts |

`transition-discrete` is required alongside `transition` on popovers, because
they animate between `display: none` and `display: block`.

## What still needs your own JavaScript

The elements cover open/close/select/filter. Everything else is yours:

- Inserting and removing toasts into the `overlays/notifications` live region.
- Sorting, filtering and paginating table rows.
- Fetching data and rendering rows; form submit and validation.
- Marking the current nav item (set the "Current" classes server-side or on load).
- Anything in `data-display/calendars` beyond the static grid.
