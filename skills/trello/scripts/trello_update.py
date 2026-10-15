#!/usr/bin/env python3
"""Trello card update CLI — for tracking progress on existing cards.

Lives in claude-configs (skills/trello/scripts/) and is symlinked into
~/.claude/skills/trello, so it works from any repo. Handles UPDATES: moving cards, comments, checklists,
labels, due dates, custom fields, assignees and description edits. Creating a
card is the /trello-task skill's job, not this script's.

Standard library only — no venv, no pip install. `python3 trello_update.py` is
the whole setup, on any Python 3.10+.

Credentials are personal: each person uses their own Trello key and token, kept
in ~/.config/trello/credentials (never in a repo). Run
`python3 trello_update.py setup` for how to create it.

Usage:
    python3 trello_update.py <subcommand> [args]

Run with no args for the subcommand list.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = "https://api.trello.com/1"


def _read_env_file(path: Path) -> dict[str, str]:
    """Minimal .env reader. Deliberately not python-dotenv: this script is
    vendored so a teammate can run it with zero installs, and the only thing we
    need from dotenv is KEY=VALUE."""
    values: dict[str, str] = {}
    try:
        text = path.read_text()
    except OSError:
        return values
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


# Personal Trello credentials, one file per machine. Lookup order: process env,
# then this file. It may also set TRELLO_BOARD_ID to change the default board.
CREDENTIALS_FILE = Path(
    os.getenv("TRELLO_CREDENTIALS_FILE") or Path.home() / ".config" / "trello" / "credentials"
).expanduser()
_ENV = _read_env_file(CREDENTIALS_FILE)
CLI = "python3 ~/.claude/skills/trello/scripts/trello_update.py"

SETUP_HELP = f"""\
Trello credentials missing. Each person uses their OWN key and token; every write
lands under the token owner's name on boards the whole team watches.

STEP 1 - get an API key (once). Log in to trello.com as yourself, then:
  1. Open https://trello.com/power-ups/admin
  2. Click "New" (top right). If it asks for a Workspace, pick yours.
  3. Fill the form: App name "Claude Trello CLI", your Workspace, your email
     (in "Email" and "Support contact"), your name as "Author". Leave
     "Iframe connector URL" empty. Click "Create".
  4. On the next page click "Generate a new API key". Copy the "API key".

STEP 2 - get a token. On that same page, to the right of the API key, click the
  "Token" link ("...you can manually generate a Token"). Trello asks to let the
  app use your account: scroll down and click "Allow". Copy the long token it
  shows (it starts with ATTA).

STEP 3 - save both. Paste them in place of <key> and <token>:
  mkdir -p {CREDENTIALS_FILE.parent}
  printf 'TRELLO_API_KEY=%s\\nTRELLO_TOKEN=%s\\n' '<key>' '<token>' > {CREDENTIALS_FILE}
  chmod 600 {CREDENTIALS_FILE}

STEP 4 - pick your default board. List the boards your token can see:
  {CLI} boards

{CREDENTIALS_FILE} lives outside every repo, so it works from any checkout and
can never be committed. Never paste a token into a repo or a chat."""


def board_help(boards: list[dict] | None = None) -> str:
    """How to choose a board, with the exact commands for this person's boards."""
    lines = ["Your boards (name, short id, workspace):"]
    for b in boards or []:
        ws = (b.get("organization") or {}).get("displayName") or "personal"
        lines.append(f"  {b['name']:<40} {b['shortLink']}   {ws}")
    if not boards:
        lines.append(f"  (run: {CLI} boards)")
    f = CREDENTIALS_FILE
    lines += ["", "Set your DEFAULT board (used when you don't name one). Run the line for the one you want:"]
    for b in boards or [{"shortLink": "<short id>", "name": "<board name>"}]:
        lines.append(f"  # {b['name']}")
        lines.append(f"  grep -v '^TRELLO_BOARD_ID=' {f} > {f}.tmp; echo 'TRELLO_BOARD_ID={b['shortLink']}' >> {f}.tmp; "
                     f"mv {f}.tmp {f}; chmod 600 {f}")
    sample = (boards or [{"shortLink": "<short id>", "name": "<board name>"}])[0]
    lines += [
        "",
        "Use ANOTHER board for one command, by short id or by name (any unique part):",
        f"  TRELLO_BOARD={sample['shortLink']} {CLI} board",
        f"  TRELLO_BOARD='{sample['name']}' {CLI} board",
    ]
    return "\n".join(lines)


_BOARD_OVERRIDE = os.getenv("TRELLO_BOARD", "").strip()
BOARD_ID = os.getenv("TRELLO_BOARD_ID") or _ENV.get("TRELLO_BOARD_ID") or ""
AUTH = {
    "key": os.getenv("TRELLO_API_KEY") or _ENV.get("TRELLO_API_KEY", ""),
    "token": os.getenv("TRELLO_TOKEN") or _ENV.get("TRELLO_TOKEN", ""),
}

EFFORT_FIELD_NAME = "Effort (1-10)"
PRIORITY_FIELD_NAME = "Priority"


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def _request(method: str, path: str, params: dict | None = None,
             json_body: dict | None = None, retries: int = 3,
             missing_ok: bool = False):
    merged = {**AUTH, **(params or {})}
    url = f"{BASE_URL}{path}?{urllib.parse.urlencode(merged)}"
    body = json.dumps(json_body).encode() if json_body is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"

    for _ in range(retries):
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                text = resp.read().decode()
            return json.loads(text) if text.strip() else {}
        except urllib.error.HTTPError as err:
            if err.code == 429:
                wait = int(err.headers.get("Retry-After", 10) or 10)
                print(f"  rate limited, waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            if missing_ok and err.code in (400, 404):
                return None
            detail = err.read().decode(errors="replace")[:300]
            die(f"{method} {path} -> {err.code}: {detail}")
        except urllib.error.URLError as err:
            die(f"{method} {path} -> {err.reason}")
    die(f"{method} {path} failed after {retries} attempts")


def get(path, params=None, missing_ok=False):
    return _request("GET", path, params, missing_ok=missing_ok)


def put(path, params=None, json_body=None):
    return _request("PUT", path, params, json_body)


def post(path, params=None, json_body=None):
    return _request("POST", path, params, json_body)


def delete(path, params=None):
    return _request("DELETE", path, params)


def die(msg: str, code: int = 1):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


def my_boards() -> list[dict]:
    return get("/members/me/boards", {"filter": "open", "fields": "name,shortLink",
                                      "organization": "true",
                                      "organization_fields": "displayName"})


def require_board():
    """Pick the board for this command: TRELLO_BOARD (short id or name), else the
    TRELLO_BOARD_ID default. With neither, explain how to set one and stop."""
    global BOARD_ID
    if _BOARD_OVERRIDE:
        boards = my_boards()
        n = _BOARD_OVERRIDE.lower()
        hits = ([b for b in boards if n in (b["shortLink"].lower(), b["id"])]
                or [b for b in boards if b["name"].lower() == n]
                or [b for b in boards if n in b["name"].lower()])
        if len(hits) != 1:
            why = "matches several boards" if hits else "matches none of your boards"
            die(f"TRELLO_BOARD='{_BOARD_OVERRIDE}' {why}.\n\n" + board_help(hits or boards))
        BOARD_ID = hits[0]["shortLink"]
    elif not BOARD_ID:
        die("No Trello board chosen.\n\n" + board_help(my_boards()))


# --------------------------------------------------------------------------
# Board lookups (by name, never hardcoded ids)
# --------------------------------------------------------------------------
def board_lists(include_closed: bool = False) -> list[dict]:
    lists = get(f"/boards/{BOARD_ID}/lists",
                {"filter": "all", "fields": "name,closed,pos"})
    return lists if include_closed else [l for l in lists if not l["closed"]]


def board_labels() -> list[dict]:
    return get(f"/boards/{BOARD_ID}/labels", {"fields": "name,color", "limit": "1000"})


def board_members() -> list[dict]:
    return get(f"/boards/{BOARD_ID}/members", {"fields": "fullName,username"})


def board_custom_fields() -> list[dict]:
    return get(f"/boards/{BOARD_ID}/customFields")


def _fuzzy_one(items: list[dict], needle: str, key: str, kind: str) -> dict:
    """Resolve a name to exactly one item: exact (ci) > startswith > substring."""
    n = needle.strip().lower()
    exact = [i for i in items if (i.get(key) or "").lower() == n]
    if len(exact) == 1:
        return exact[0]
    starts = [i for i in items if (i.get(key) or "").lower().startswith(n)]
    if len(starts) == 1:
        return starts[0]
    subs = [i for i in items if n in (i.get(key) or "").lower()]
    if len(subs) == 1:
        return subs[0]
    pool = exact or starts or subs
    if not pool:
        names = ", ".join(sorted((i.get(key) or "?") for i in items))
        die(f"No {kind} matching '{needle}'. Available: {names}")
    names = ", ".join((i.get(key) or "?") for i in pool)
    die(f"'{needle}' is ambiguous for {kind} — matches: {names}")


def resolve_list(name: str) -> dict:
    return _fuzzy_one(board_lists(include_closed=True), name, "name", "list")


def resolve_label(name: str) -> dict:
    return _fuzzy_one(board_labels(), name, "name", "label")


def resolve_member(name: str) -> dict:
    members = board_members()
    n = name.strip().lstrip("@").lower()
    for m in members:
        if m["username"].lower() == n:
            return m
    return _fuzzy_one(members, name, "fullName", "member")


def resolve_custom_field(name: str) -> dict:
    return _fuzzy_one(board_custom_fields(), name, "name", "custom field")


# --------------------------------------------------------------------------
# Card resolution — accepts card id, short link, #123, or name substring
# --------------------------------------------------------------------------
CARD_FIELDS = ("name,desc,idList,idMembers,labels,idShort,shortUrl,shortLink,"
               "due,dueComplete,closed,dateLastActivity")


def _all_cards(include_closed: bool = False) -> list[dict]:
    path = f"/boards/{BOARD_ID}/cards/{'all' if include_closed else 'open'}"
    return get(path, {"fields": CARD_FIELDS})


def resolve_card(ref: str, include_closed: bool = True) -> dict:
    """Resolve a card reference to a single card dict."""
    ref = ref.strip()

    # Full URL -> extract shortLink
    if ref.startswith("http"):
        parts = [p for p in ref.split("/") if p]
        for i, p in enumerate(parts):
            if p == "c" and i + 1 < len(parts):
                ref = parts[i + 1]
                break

    # 24-char hex object id: fetch directly
    bare = ref.lstrip("#")
    if len(bare) == 24 and all(c in "0123456789abcdef" for c in bare.lower()):
        return get(f"/cards/{bare}", {"fields": CARD_FIELDS})

    # 8 alphanumeric chars might be a shortLink, or just an 8-letter word from a
    # card name ("checkout"). Try it as a shortLink; if Trello has no such card,
    # fall through to the name search below instead of failing.
    if len(bare) == 8 and bare.isalnum() and not bare.isdigit():
        card = get(f"/cards/{bare}", {"fields": CARD_FIELDS}, missing_ok=True)
        if card:
            return card

    cards = _all_cards(include_closed=include_closed)

    # Numeric -> short id (#123)
    if bare.isdigit():
        hits = [c for c in cards if str(c["idShort"]) == bare]
        if len(hits) == 1:
            return hits[0]
        if not hits:
            die(f"No card with short id #{bare} on this board")

    # Name match
    n = ref.lower()
    exact = [c for c in cards if c["name"].lower() == n]
    if len(exact) == 1:
        return exact[0]
    subs = [c for c in cards if n in c["name"].lower()]
    if len(subs) == 1:
        return subs[0]
    pool = exact or subs
    if not pool:
        die(f"No card matching '{ref}'. Try: trello_update.py search <term>")
    listing = "\n".join(f"  #{c['idShort']}  {c['name']}" for c in pool[:15])
    die(f"'{ref}' matches {len(pool)} cards — be more specific:\n{listing}")


# --------------------------------------------------------------------------
# Display helpers
# --------------------------------------------------------------------------
def _list_name_map() -> dict:
    return {l["id"]: l["name"] for l in board_lists(include_closed=True)}


def _member_name_map() -> dict:
    return {m["id"]: m["fullName"] for m in board_members()}


def card_line(card: dict, lmap: dict, mmap: dict) -> str:
    labels = ", ".join(l["name"] for l in card.get("labels", []) if l.get("name"))
    who = ", ".join(mmap.get(i, i[:6]) for i in card.get("idMembers", []))
    bits = [f"[{lmap.get(card['idList'], '?')}]"]
    if who:
        bits.append(f"@{who}")
    if labels:
        bits.append(f"({labels})")
    if card.get("due"):
        flag = "done" if card.get("dueComplete") else "due"
        bits.append(f"{flag} {card['due'][:10]}")
    if card.get("closed"):
        bits.append("ARCHIVED")
    return f"#{card['idShort']}  {card['name']}  " + "  ".join(bits)


def card_custom_values(card_id: str) -> dict:
    """Return {field_name: readable_value} for a card."""
    fields = {f["id"]: f for f in board_custom_fields()}
    items = get(f"/cards/{card_id}/customFieldItems")
    out = {}
    for it in items:
        f = fields.get(it["idCustomField"])
        if not f:
            continue
        if it.get("idValue"):
            opt = next((o for o in f.get("options", [])
                        if o["id"] == it["idValue"]), None)
            out[f["name"]] = opt["value"].get("text") if opt else it["idValue"]
        elif it.get("value"):
            out[f["name"]] = next(iter(it["value"].values()))
    return out


# --------------------------------------------------------------------------
# Subcommands
# --------------------------------------------------------------------------
def cmd_setup(args):
    """Walk through whatever is missing: credentials, then a default board."""
    if not (AUTH["key"] and AUTH["token"]):
        print(SETUP_HELP)
        return
    src = "process env" if os.getenv("TRELLO_TOKEN") else CREDENTIALS_FILE
    me = get("/members/me", {"fields": "fullName,username"})
    print(f"Credentials OK ({src}): {me['fullName']} @{me['username']}")
    if not BOARD_ID:
        print("No default board yet.\n")
        print(board_help(my_boards()))
        return
    board = get(f"/boards/{BOARD_ID}", {"fields": "name"})
    print(f"Default board: {board['name']} ({BOARD_ID})\n")
    print(board_help(my_boards()))


def cmd_boards(args):
    """Every open board the token can see, and how to pick one."""
    boards = my_boards()
    print(board_help(boards))
    if BOARD_ID:
        name = next((b["name"] for b in boards if BOARD_ID in (b["shortLink"], b["id"])), "?")
        print(f"\nCurrent default: {name} ({BOARD_ID})")


def cmd_board(args):
    lmap_lists = board_lists(include_closed=True)
    print("LISTS:")
    for l in lmap_lists:
        print(f"  {l['name']}{'  (archived)' if l['closed'] else ''}")
    print("\nLABELS:")
    for l in board_labels():
        if l.get("name"):
            print(f"  {l['name']}  ({l['color']})")
    print("\nMEMBERS:")
    for m in board_members():
        print(f"  {m['fullName']}  @{m['username']}")
    print("\nCUSTOM FIELDS:")
    for f in board_custom_fields():
        opts = [o["value"].get("text") for o in f.get("options", [])]
        extra = f"  options: {', '.join(opts)}" if opts else ""
        print(f"  {f['name']}  ({f['type']}){extra}")


def cmd_search(args):
    cards = _all_cards(include_closed=args.archived)
    lmap, mmap = _list_name_map(), _member_name_map()
    q = args.query.lower().lstrip("#")
    hits = [c for c in cards
            if q in c["name"].lower() or q in (c.get("desc") or "").lower()
            or str(c["idShort"]) == q]
    if args.list:
        target = resolve_list(args.list)
        hits = [c for c in hits if c["idList"] == target["id"]]
    if not hits:
        print(f"No cards matching '{args.query}'")
        return
    for c in hits:
        print(card_line(c, lmap, mmap))


def cmd_list(args):
    lmap, mmap = _list_name_map(), _member_name_map()
    cards = _all_cards()
    targets = [resolve_list(args.name)] if args.name else board_lists()
    for tl in targets:
        in_list = [c for c in cards if c["idList"] == tl["id"]]
        print(f"\n=== {tl['name']} ({len(in_list)}) ===")
        for c in in_list:
            print("  " + card_line(c, lmap, mmap))


def cmd_mine(args):
    me = get("/members/me", {"fields": "id,fullName"})
    lmap, mmap = _list_name_map(), _member_name_map()
    cards = [c for c in _all_cards() if me["id"] in c.get("idMembers", [])]
    print(f"Cards assigned to {me['fullName']} ({len(cards)}):")
    for l in board_lists():
        group = [c for c in cards if c["idList"] == l["id"]]
        if group:
            print(f"\n=== {l['name']} ===")
            for c in group:
                print("  " + card_line(c, lmap, mmap))


def cmd_show(args):
    card = resolve_card(args.card)
    lmap, mmap = _list_name_map(), _member_name_map()
    print(f"#{card['idShort']}  {card['name']}")
    print(f"URL:      {card.get('shortUrl')}")
    print(f"List:     {lmap.get(card['idList'], '?')}")
    labels = ", ".join(l["name"] for l in card.get("labels", []) if l.get("name"))
    print(f"Labels:   {labels or '-'}")
    who = ", ".join(mmap.get(i, i) for i in card.get("idMembers", []))
    print(f"Members:  {who or '-'}")
    due = card.get("due")
    print(f"Due:      {due[:10] if due else '-'}"
          f"{'  (complete)' if card.get('dueComplete') else ''}")
    for k, v in card_custom_values(card["id"]).items():
        print(f"{k+':':<10}{v}")
    print(f"\n--- Description ---\n{card.get('desc') or '(empty)'}")

    checklists = get(f"/cards/{card['id']}/checklists",
                     {"fields": "name", "checkItem_fields": "name,state,pos"})
    if checklists:
        print("\n--- Checklists ---")
        for cl in checklists:
            items = sorted(cl.get("checkItems", []), key=lambda i: i["pos"])
            done = sum(1 for i in items if i["state"] == "complete")
            print(f"\n{cl['name']}  ({done}/{len(items)})")
            for i in items:
                box = "x" if i["state"] == "complete" else " "
                print(f"  [{box}] {i['name']}")

    comments = get(f"/cards/{card['id']}/actions",
                   {"filter": "commentCard", "limit": str(args.comments)})
    if comments:
        print("\n--- Recent comments ---")
        for a in comments:
            who = a["memberCreator"]["fullName"]
            print(f"\n[{a['date'][:16].replace('T', ' ')}] {who}:")
            print("  " + a["data"]["text"].replace("\n", "\n  "))


def cmd_move(args):
    card = resolve_card(args.card)
    target = resolve_list(args.to)
    if target.get("closed"):
        die(f"list '{target['name']}' is archived — pick an open one "
            f"(trello_update.py board)")
    params = {"idList": target["id"]}
    if args.top:
        params["pos"] = "top"
    elif args.bottom:
        params["pos"] = "bottom"
    put(f"/cards/{card['id']}", params)
    print(f"Moved #{card['idShort']} '{card['name']}' -> {target['name']}")
    if args.comment:
        post(f"/cards/{card['id']}/actions/comments", {"text": args.comment})
        print(f"Commented: {args.comment}")


def cmd_comment(args):
    card = resolve_card(args.card)
    text = args.text
    post(f"/cards/{card['id']}/actions/comments", {"text": text})
    print(f"Commented on #{card['idShort']} '{card['name']}':\n{text}")


def cmd_desc(args):
    card = resolve_card(args.card)
    current = card.get("desc") or ""
    if args.append:
        new = (current.rstrip() + "\n\n" + args.append).strip()
    elif args.set is not None:
        new = args.set
    else:
        die("pass --set or --append")
    put(f"/cards/{card['id']}", {"desc": new})
    print(f"Updated description on #{card['idShort']} '{card['name']}'")


def cmd_check(args):
    """Tick / untick checklist items by substring match."""
    card = resolve_card(args.card)
    checklists = get(f"/cards/{card['id']}/checklists",
                     {"fields": "name", "checkItem_fields": "name,state"})
    state = "complete" if args.action == "check" else "incomplete"
    matches = []
    for cl in checklists:
        for it in cl.get("checkItems", []):
            if args.item.lower() in it["name"].lower():
                matches.append((cl, it))
    if not matches:
        die(f"No checklist item matching '{args.item}' on #{card['idShort']}")
    if len(matches) > 1 and not args.all:
        listing = "\n".join(f"  [{cl['name']}] {it['name']}" for cl, it in matches)
        die(f"'{args.item}' matches {len(matches)} items (use --all to do every one):\n{listing}")
    for cl, it in matches:
        put(f"/cards/{card['id']}/checkItem/{it['id']}", {"state": state})
        print(f"{'[x]' if state == 'complete' else '[ ]'} {it['name']}  ({cl['name']})")


def cmd_checklist_add(args):
    card = resolve_card(args.card)
    checklists = get(f"/cards/{card['id']}/checklists", {"fields": "name"})
    if args.checklist:
        cl = next((c for c in checklists
                   if args.checklist.lower() in c["name"].lower()), None)
        if not cl:
            cl = post("/checklists", {"idCard": card["id"], "name": args.checklist})
            print(f"Created checklist '{cl['name']}'")
    elif checklists:
        cl = checklists[0]
    else:
        cl = post("/checklists", {"idCard": card["id"], "name": "Progress"})
        print(f"Created checklist '{cl['name']}'")
    for item in args.items:
        post(f"/checklists/{cl['id']}/checkItems",
             {"name": item, "checked": "true" if args.checked else "false", "pos": "bottom"})
        print(f"  + {item}")
    print(f"Added {len(args.items)} item(s) to '{cl['name']}' on #{card['idShort']}")


def cmd_label(args):
    card = resolve_card(args.card)
    for name in args.add or []:
        lbl = resolve_label(name)
        post(f"/cards/{card['id']}/idLabels", {"value": lbl["id"]})
        print(f"+ label {lbl['name']}")
    for name in args.remove or []:
        lbl = resolve_label(name)
        delete(f"/cards/{card['id']}/idLabels/{lbl['id']}")
        print(f"- label {lbl['name']}")
    print(f"Labels updated on #{card['idShort']} '{card['name']}'")


def cmd_assign(args):
    card = resolve_card(args.card)
    for name in args.add or []:
        m = resolve_member(name)
        post(f"/cards/{card['id']}/idMembers", {"value": m["id"]})
        print(f"+ {m['fullName']}")
    for name in args.remove or []:
        m = resolve_member(name)
        delete(f"/cards/{card['id']}/idMembers/{m['id']}")
        print(f"- {m['fullName']}")
    print(f"Members updated on #{card['idShort']} '{card['name']}'")


def cmd_due(args):
    card = resolve_card(args.card)
    params = {}
    if args.date:
        params["due"] = "null" if args.date.lower() in ("clear", "none") else args.date
    if args.complete:
        params["dueComplete"] = "true"
    if args.incomplete:
        params["dueComplete"] = "false"
    if not params:
        die("pass a date, 'clear', --complete, or --incomplete")
    put(f"/cards/{card['id']}", params)
    print(f"Due updated on #{card['idShort']} '{card['name']}': {params}")


def cmd_field(args):
    card = resolve_card(args.card)
    if args.effort is not None:
        f = resolve_custom_field(EFFORT_FIELD_NAME)
        put(f"/cards/{card['id']}/customField/{f['id']}/item",
            json_body={"value": {"number": str(args.effort)}})
        print(f"Effort = {args.effort}")
    if args.priority:
        f = resolve_custom_field(PRIORITY_FIELD_NAME)
        opt = next((o for o in f.get("options", [])
                    if o["value"].get("text", "").lower() == args.priority.lower()), None)
        if not opt:
            opts = ", ".join(o["value"].get("text") for o in f.get("options", []))
            die(f"Priority '{args.priority}' not valid. Options: {opts}")
        put(f"/cards/{card['id']}/customField/{f['id']}/item",
            json_body={"idValue": opt["id"]})
        print(f"Priority = {opt['value']['text']}")
    if args.effort is None and not args.priority:
        die("pass --effort and/or --priority")
    print(f"Custom fields updated on #{card['idShort']} '{card['name']}'")


def _set_effort(card_id: str, effort: int) -> str:
    f = resolve_custom_field(EFFORT_FIELD_NAME)
    put(f"/cards/{card_id}/customField/{f['id']}/item",
        json_body={"value": {"number": str(effort)}})
    return str(effort)


def _set_priority(card_id: str, priority: str) -> str:
    f = resolve_custom_field(PRIORITY_FIELD_NAME)
    opt = next((o for o in f.get("options", [])
                if o["value"].get("text", "").lower() == priority.lower()), None)
    if not opt:
        opts = ", ".join(o["value"].get("text") for o in f.get("options", []))
        die(f"Priority '{priority}' not valid. Options: {opts}")
    put(f"/cards/{card_id}/customField/{f['id']}/item",
        json_body={"idValue": opt["id"]})
    return opt["value"]["text"]


def cmd_create(args):
    """Create a card, with its labels, due date and custom fields, in one pass.

    Every id is resolved BY NAME against the board being written to. That is the
    whole point of doing this here instead of hand-rolling REST calls: both
    boards carry an "Effort (1-10)" and a "Priority" field with the same names
    and DIFFERENT ids, so a hardcoded id silently writes nothing.
    """
    target = resolve_list(args.list)
    if target.get("closed"):
        die(f"list '{target['name']}' is archived — pick an open one "
            f"(trello_update.py board)")

    label_ids = [resolve_label(n)["id"] for n in (args.label or [])]

    desc = args.desc
    if desc == "-":
        desc = sys.stdin.read()

    params = {"idList": target["id"], "name": args.name, "pos": "top"}
    if desc:
        params["desc"] = desc
    if label_ids:
        params["idLabels"] = ",".join(label_ids)
    if args.due:
        params["due"] = args.due

    card = post("/cards", params)

    effort = _set_effort(card["id"], args.effort) if args.effort is not None else "-"
    priority = _set_priority(card["id"], args.priority) if args.priority else "-"

    if args.assign:
        for who in args.assign:
            m = resolve_member(who)
            post(f"/cards/{card['id']}/idMembers", {"value": m["id"]})

    board = get(f"/boards/{BOARD_ID}", {"fields": "name"})
    print(f"Created #{card['idShort']}  {card['name']}")
    print(f"URL:      {card.get('shortUrl')}")
    print(f"Board:    {board.get('name')} ({BOARD_ID})")
    print(f"List:     {target['name']}")
    print(f"Labels:   {', '.join(n for n in (args.label or [])) or '-'}")
    print(f"Effort:   {effort}")
    print(f"Priority: {priority}")
    print(f"Due:      {(args.due or '-')[:10]}")


def cmd_archive(args):
    card = resolve_card(args.card)
    put(f"/cards/{card['id']}", {"closed": "false" if args.unarchive else "true"})
    verb = "Unarchived" if args.unarchive else "Archived"
    print(f"{verb} #{card['idShort']} '{card['name']}'")


def cmd_wip(args):
    lmap, mmap = _list_name_map(), _member_name_map()
    cards = _all_cards()
    for lname in ("In-progress", "QA & Testing"):
        tl = next((l for l in board_lists() if l["name"] == lname), None)
        if not tl:
            continue
        group = [c for c in cards if c["idList"] == tl["id"]]
        print(f"\n=== {lname} ({len(group)}) ===")
        for c in group:
            print("  " + card_line(c, lmap, mmap))


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="trello_update.py",
        description="Update existing Trello cards (progress tracking).")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("setup", help="step-by-step: get a token, save it, pick a default board")
    s.set_defaults(func=cmd_setup)

    s = sub.add_parser("boards", help="list your boards and how to switch between them")
    s.set_defaults(func=cmd_boards)

    s = sub.add_parser("board", help="dump lists, labels, members, custom fields")
    s.set_defaults(func=cmd_board)

    s = sub.add_parser("search", help="find cards by name/desc/short-id")
    s.add_argument("query")
    s.add_argument("--list", help="restrict to a list")
    s.add_argument("--archived", action="store_true", help="include archived cards")
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("cards", help="show cards in a list (or every list)")
    s.add_argument("name", nargs="?", help="list name; omit for all lists")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("mine", help="cards assigned to me, grouped by list")
    s.set_defaults(func=cmd_mine)

    s = sub.add_parser("wip", help="In-progress + QA & Testing overview")
    s.set_defaults(func=cmd_wip)

    s = sub.add_parser("show", help="full card detail incl. checklists + comments")
    s.add_argument("card")
    s.add_argument("--comments", type=int, default=10)
    s.set_defaults(func=cmd_show)

    s = sub.add_parser("create", help="create a card (see the trello-task skill)")
    s.add_argument("name", help="card title")
    s.add_argument("--list", required=True, help="target list name")
    s.add_argument("--desc", help="card body; '-' reads it from stdin")
    s.add_argument("--label", action="append", help="label name (repeatable)")
    s.add_argument("--effort", type=int, help="Effort (1-10)")
    s.add_argument("--priority", help="Highest|High|Medium|Low|Lowest|Not sure")
    s.add_argument("--due", help="ISO 8601, e.g. 2026-09-24")
    s.add_argument("--assign", action="append", help="member name or @username")
    s.set_defaults(func=cmd_create)

    s = sub.add_parser("move", help="move a card to another list")
    s.add_argument("card")
    s.add_argument("to", help="target list name")
    s.add_argument("--comment", help="also post this comment")
    s.add_argument("--top", action="store_true")
    s.add_argument("--bottom", action="store_true")
    s.set_defaults(func=cmd_move)

    s = sub.add_parser("comment", help="post a progress comment")
    s.add_argument("card")
    s.add_argument("text")
    s.set_defaults(func=cmd_comment)

    s = sub.add_parser("desc", help="set or append to the description")
    s.add_argument("card")
    s.add_argument("--set")
    s.add_argument("--append")
    s.set_defaults(func=cmd_desc)

    s = sub.add_parser("check", help="tick a checklist item by substring")
    s.add_argument("card")
    s.add_argument("item")
    s.add_argument("--all", action="store_true", help="apply to every match")
    s.set_defaults(func=cmd_check, action="check")

    s = sub.add_parser("uncheck", help="untick a checklist item by substring")
    s.add_argument("card")
    s.add_argument("item")
    s.add_argument("--all", action="store_true")
    s.set_defaults(func=cmd_check, action="uncheck")

    s = sub.add_parser("add-items", help="add checklist items")
    s.add_argument("card")
    s.add_argument("items", nargs="+")
    s.add_argument("--checklist", help="checklist name (created if missing)")
    s.add_argument("--checked", action="store_true", help="add pre-ticked")
    s.set_defaults(func=cmd_checklist_add)

    s = sub.add_parser("label", help="add/remove labels")
    s.add_argument("card")
    s.add_argument("--add", action="append")
    s.add_argument("--remove", action="append")
    s.set_defaults(func=cmd_label)

    s = sub.add_parser("assign", help="add/remove members")
    s.add_argument("card")
    s.add_argument("--add", action="append")
    s.add_argument("--remove", action="append")
    s.set_defaults(func=cmd_assign)

    s = sub.add_parser("due", help="set/clear due date or toggle completion")
    s.add_argument("card")
    s.add_argument("date", nargs="?", help="YYYY-MM-DD, ISO 8601, or 'clear'")
    s.add_argument("--complete", action="store_true")
    s.add_argument("--incomplete", action="store_true")
    s.set_defaults(func=cmd_due)

    s = sub.add_parser("field", help="set Effort / Priority custom fields")
    s.add_argument("card")
    s.add_argument("--effort", type=int)
    s.add_argument("--priority")
    s.set_defaults(func=cmd_field)

    s = sub.add_parser("archive", help="archive (or --unarchive) a card")
    s.add_argument("card")
    s.add_argument("--unarchive", action="store_true")
    s.set_defaults(func=cmd_archive)

    return p


def main():
    args = build_parser().parse_args()
    if not (AUTH["key"] and AUTH["token"]) and args.cmd != "setup":
        die(SETUP_HELP)
    if args.cmd not in ("setup", "boards"):
        require_board()
    args.func(args)


if __name__ == "__main__":
    main()
