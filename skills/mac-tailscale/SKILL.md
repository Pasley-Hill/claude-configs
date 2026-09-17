---
name: mac-tailscale
description: >
  SSH into Christopher's MacBook Pro over Tailscale and run tools there (az CLI,
  Graph/SharePoint, Azure Functions). Use when the user says ssh to the mac,
  MacBook, Tailscale Mac, run az on the Mac, OneDrive/SharePoint ProjectOne,
  Azure Functions from the Mac, or otherwise needs files/CLIs that live on
  christophers-macbook-pro-2 rather than this Linux box.
---

# Mac via Tailscale

Reach `christophers-macbook-pro-2` from this Linux machine over Tailscale. Do **not**
use the local Linux `az` when the user asked for the Mac.

## Connection

| | |
|---|---|
| Tailscale name | `christophers-macbook-pro-2` |
| MagicDNS | `christophers-macbook-pro-2.tail198da4.ts.net` |
| Tailscale IPv4 | `100.100.126.8` |
| SSH user | `christopherhill` |
| Identity | `~/.ssh/id_ed25519` (`chill@omarchy`) |
| Remote home | `/Users/christopherhill` |
| Default remote shell | **zsh** |

```bash
ssh -o BatchMode=yes -o ConnectTimeout=15 -i ~/.ssh/id_ed25519 \
  christopherhill@100.100.126.8 'export PATH=/opt/homebrew/bin:$PATH; <cmd>'
```

Prefer the IP (host key already in `known_hosts`). MagicDNS works if that host key
is present. `crhill@…` and `chill@…` are wrong users.

If `Permission denied (publickey)`: Mac `~/.ssh/authorized_keys` is missing this
box's `id_ed25519.pub`. Stop and say so. Do not try passwords.

`tailscale status` to confirm the Mac is online (`active` / `direct`).

## Remote command rules

- Remote login shell is zsh. Unquoted `===`, globs, and some `bash -lc` one-liners
  fail. Quote the whole remote script. Prepend Homebrew PATH every time — non-
  interactive shells do **not** have `/opt/homebrew/bin`.
- Homebrew CLIs of interest:
  - `/opt/homebrew/bin/az` (2.90.0)
  - `/opt/homebrew/bin/gh`
  - `/opt/homebrew/bin/python3`
- `func` (Azure Functions Core Tools) is **not** installed.

## az on the Mac

Logged in as `chill@trilogycares.com`. Tenant
`c69f3959-6c81-4ee5-9053-cd8f16b0fc8a`. Account list shows only
`N/A(tenant level account)` — **no ARM subscription**. So:

| Works | Does not work |
|---|---|
| Microsoft Graph via `az rest` | `az functionapp list`, `az group list`, storage ARM |
| SharePoint / M365 drives | Deploying Function Apps until a real subscription is set |

```bash
export PATH=/opt/homebrew/bin:$PATH
az account show
az rest --method get --uri "https://graph.microsoft.com/v1.0/me"
```

If Graph/az auth errors: tell the user to run `az login` **on the Mac** and stop.

### SharePoint / "OneDrive" Project One

No local OneDrive client (CloudStorage is Dropbox only). M365 files are SharePoint.

- Hostname: `trilogyhealthsolutions.sharepoint.com`
- Site: https://trilogyhealthsolutions.sharepoint.com/sites/projectone
- Site id: `trilogyhealthsolutions.sharepoint.com,07dba173-2ff9-4588-9495-cb4826fc97d8,55f05135-503e-44be-99db-1db88d92b022`
- Personal `/me/drive` is empty. Use the site drive.

```bash
SITE='trilogyhealthsolutions.sharepoint.com,07dba173-2ff9-4588-9495-cb4826fc97d8,55f05135-503e-44be-99db-1db88d92b022'
az rest --method get --uri "https://graph.microsoft.com/v1.0/sites/${SITE}/drive/root/children"
```

Graph **search** (`/search/query`) is 403 (`User.ReadWrite.All` only). Paginate
`/drive/root/delta` and sort locally for "new files".

Get a token on the Mac if you need `curl`/python against Graph:

```bash
az account get-access-token --resource https://graph.microsoft.com --query accessToken -o tsv
```

Do not leave tokens on disk.

### Azure Functions

`az functionapp *` ARM calls fail today (`SubscriptionNotFound`). Need
`az account list` to show a real subscription, then
`az account set --subscription <id>`.

Once a subscription exists:

```bash
az functionapp list -o table
az functionapp function list --name <app> --resource-group <rg> -o table
az functionapp keys list --name <app> --resource-group <rg>
az functionapp log tail --name <app> --resource-group <rg>
az functionapp deployment source config-zip --name <app> --resource-group <rg> --src <zip>
```

Do not install `func` unless asked.

## Other useful Mac paths

- Code: `/Users/christopherhill/code-2026/project-one` (and `project-one-feat-*` siblings)
- CloudStorage: `/Users/christopherhill/Library/CloudStorage/Dropbox` only

## Auth / key notes

This Linux pubkey (must be in Mac `authorized_keys`):

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIItP2nO1/AxCEecbK1eOlJfC0C9r6BSBo3LPErQObHP1 chill@omarchy
```
