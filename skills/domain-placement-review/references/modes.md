# Audit and move plan

## Read a census line

```
<STATUS> <path> — consumers: <domain> (<file:line> [via <x>]) — <what to do>
```

- `admin (app/admin/x.ts:12)` → that line uses the file.
- `… via app/shared/y.ts` → admin uses `y.ts`, and `y.ts` uses this file. `y.ts` is misplaced
  too, so they move together.
- `… via app/shared/render.ts:renderLegal` → only that export of a shared hub reaches this file,
  and only admin calls it.

| Status | Meaning | What to say |
|---|---|---|
| `SINGLE` | One domain uses it. | Move it to `move_to`, with what it travels with. If a line says "first decide where X goes", X has no domain: settle X first. |
| `NONE` | No domain uses it. | If a composition root wires it, ask which domain owns the job. If nothing does, it may be dead code. |
| `ROOT` | Only the app's entry point reaches it. | List it in `justified` as platform, or move it. |
| `KEEP` | A shared file that stays needs it. | It stays. Name the file that keeps it. |
| `SHARED` | Two or more domains use it. | Nothing to do. |
| `JUSTIFIED` | Listed in the config, with a reason. | Nothing to do, unless the reason no longer holds. "(without this line: SINGLE)" says what it would be. |

## Audit a shared folder

1. Run `consumers.py census --ref origin/<base> [--scope <folder, file or glob>]`.
   - `--ticket <ticket>` keeps only the rows a `planned` entry gives to that card: its worklist.
   - `--strict` exits 1 while any SINGLE, NONE or ROOT row is left. Use it for "zero violations".
2. Copy its `AUDIT:` line and every `WARNING:` line.
3. Then copy one line per file that is not `SHARED` or `JUSTIFIED`. Add a question where a line
   needs a human.

## Plan a move out of shared

1. Run `census --ref origin/<base> --scope <folder> --all`.
   - `SHARED`, `KEEP` and `JUSTIFIED` files stay. Say whether the folder can be emptied. If it
     cannot, name each file that stays and the line that keeps it.
   - Every `SINGLE` file moves to its `move_to`, with what it travels with.
2. After the move, run `diff --base origin/<base> --head .`. It must report nothing blocking.
   - `CROSS` means a moved file still has a user in another domain.
   - `UPWARD` means shared code still imports the moved file.
   - `CLASH` means two files now answer to the same URL.
