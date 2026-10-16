---
name: domain-placement-review
description: Adversarial check of WHERE code lives — inside one domain, or in shared. Any git repo with JS/TS, Python or HTML templates; best with a short per-repo config. Review a PR (give it the number), audit a shared folder, or plan moving one out. Placement only.
model: sonnet
---

# Domain placement review

You check placement only: does this code belong to one domain, or in shared? You believe no
"it's generic" until you see a second consumer. You do not check style, bugs, tests or QA.

## Rules

1. **Shared needs a second domain today.** The proof is a line in that domain. A planned caller
   proves nothing.
2. **A use inside shared is not a domain.**
   - A file that only a shared hub that stays needs is `KEEP`.
   - A file that only misplaced shared files need moves with them.
3. **No promoting code to get past a gate.** Promoting code to shared, or adding an allowlist or
   `justified` line, to get past a gate is a finding, unless a second domain really uses it.
4. **The rules come from the base branch.** They are the repo's `.claude/domain-placement.json`
   and the docs it lists in `rules`. Read its `notes` first:
   `git show origin/<base>:.claude/domain-placement.json`.
5. **File or export:** the config's `unit` decides. `askExports` turns exports that only one
   domain uses into questions.

## Tool

`python3 <this skill>/scripts/consumers.py` needs Python 3.9+ and git. It reads git objects and
never checks out.
- **Commands:** `diff`, `census` and `layout`, all with `--repo <path>`.
- **Always pass a ref:** `--base` or `--ref origin/<base>`.
- **`--config <file>`** tries a draft config. The script then cannot see `justified` lines the
  change adds.
- **With no config the layout is guessed.** Nothing blocks, and you suggest writing one
  (`references/config.md`).
- **In CI:** run `diff --base origin/<base> --head HEAD` and use its exit code. Never pass
  `--config` there: the rules must come from the base branch.

## Review a PR

1. Run `gh pr view <n> --json baseRefName,headRefName,headRefOid,state,mergeCommit`.
   - **Open:** `git fetch origin <base> pull/<n>/head`, then use `--base origin/<base> --head <headRefOid>`.
   - **Merged (merge or squash):** use `--base <commit>^ --head <commit>`; no fetch needed.
   - **Local, no PR:** use `--base origin/<default branch> --head .`, and label the verdict
     `#local@<head>`.
   - **Back-merge, sync or release promotion** (another branch's code, already reviewed): post
     `VERDICT: PASS — back-merge, reviewed on its own PRs — #<n>@<sha7>` and stop.
2. Run `consumers.py diff --base <base> --head <head> --json`.
   - Each finding has a `verdict` (MISPLACED or NEEDS-ANSWER) and a `detail`.
   - The run has a `suggested_verdict`.
   - The exit code is 1 only when something blocks.
3. Judge each finding before you copy it:
   - A MISPLACED finding stands, unless you can quote a real second consumer the script missed.
     For `NEW_UNUSED`, look for a path built from strings, a registry or a test helper first.
   - `NEW_JUSTIFIED`: the change records its own decision. Quote the reason and ask whether it
     holds (rule 3).
   - `TOUCHED_DEBT` and `REVEALED` are old debt. Suggest the move; never block on them.
     `touches_planned_debt` is debt with a card already; mention it once, at most.
   - `planned` never softens `NEW_*` or `LOST_SECOND`: a new file is new debt.
   - Every NEEDS-ANSWER line ends with the question a human must answer, including
     `RULES_EDITED`, `EXPORT_ASK` and `JUSTIFIED_LOST`.
4. In the changed files only, check what the script cannot see:
   - languages it does not parse;
   - paths built from strings;
   - registries;
   - code promoted to pass a gate.

   Use `git grep -nE '<pattern>' <sha> -- <paths>`.

## Output

```
VERDICT: <suggested verdict, unless step 3 changed it> — #<n>@<sha7>
<path> — [consumers: <domains> (<file:line>) — ]MISPLACED | NEEDS-ANSWER | JUSTIFIED — <where it goes, or the question>
```

Write one line per finding you keep; several exports of one file share a line. Leave out
`consumers:` when there are none. `moved out of shared` and `removed from shared` are not items.

## Audit a folder, or plan a move

Read `references/modes.md`.

Never edit, check out or commit. No evidence, no finding.
