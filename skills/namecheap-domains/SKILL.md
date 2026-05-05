---
name: namecheap-domains
description: "Check domain availability against the Namecheap API — single domain, batch up to 50 at once, or multi-TLD sweeps of a base name. Use when the user asks whether a specific domain is available/taken/free, wants to brainstorm and screen candidate names for a product/company/project, sweeps one name across TLDs like .com/.io/.ai/.dev/.co, or asks about premium pricing and EAP fees. Triggers on 'is X.com available', 'is X taken', 'check these domains', 'find me an available .ai', 'is this domain free', 'domain availability', 'check namecheap', 'what .io names are free', 'brainstorm domain names'. Returns available/taken per domain with premium pricing flags; auto-chunks lists larger than 50 across batches."
allowed-tools: Bash(python3 ~/.claude/skills/namecheap-domains/scripts/check.py*), Bash(python3 scripts/check.py*), Read
---

# Namecheap Domains

Screens domain availability via the Namecheap `namecheap.domains.check`
API. Wraps a single Python script — no dependencies beyond the stdlib.

## The three jobs

1. **Check explicit domains** the user named (`foo.com bar.ai baz.io`).
2. **Sweep one base name across TLDs** (`myproduct` across `.com/.io/.ai/.dev/.co`).
3. **Screen brainstormed candidates** — when the user asks for help
   finding a name, *generate the candidates yourself first*, then run
   them through the checker. Prefer one batched call over many small ones.

## Quick start

```bash
# explicit domains
python3 ~/.claude/skills/namecheap-domains/scripts/check.py foo.com bar.ai

# TLD sweep of a single base name
python3 ~/.claude/skills/namecheap-domains/scripts/check.py \
  --base myproduct --tlds com,io,ai,dev,co,app

# screen a brainstormed list, show only what's free
python3 ~/.claude/skills/namecheap-domains/scripts/check.py \
  --file /tmp/candidates.txt --available-only

# machine-readable
python3 ~/.claude/skills/namecheap-domains/scripts/check.py foo.com --json
```

## Decision tree

| User asks… | Do |
|---|---|
| "is `foo.com` available?" | one-shot: `check.py foo.com` |
| "check these 5 domains" | pass all as positional args — one batched API call |
| "find an available `.ai` name for X" | brainstorm 15–30 candidates, write to `/tmp/candidates.txt`, run with `--file --available-only` |
| "is `myname` free anywhere?" | `--base myname --tlds com,io,ai,dev,co,app,xyz` |
| "check 80 domains" | pass them all — script auto-chunks at 50 per API call |
| needs structured output for downstream use | add `--json` |

## Always prefer batching

The Namecheap API accepts up to **50 domains per request** (hard cap —
51+ returns `"Only 50 domains are allowed in a single check command"`).
The script chunks automatically, so pass domains in bulk rather than
looping one-at-a-time. A 30-domain sweep is one HTTP call, not thirty.

## Output format

Default (text):

```
AVAILABLE  brugfdjiujhrg.ai
taken      google.com
AVAILABLE  coolname.io [premium $2999.00]
AVAILABLE  newtld.app [EAP +$1000.00]
```

- `AVAILABLE` / `taken` — the headline signal
- `[premium $N]` — Namecheap flagged it as a premium registration; the
  price shown is Namecheap's, not the registry's wholesale
- `[EAP +$N]` — Early Access Program fee on top of normal registration
  (applies to newly-launched TLDs in their first ~60 days)

JSON (via `--json`) adds `icann_fee`, `premium_price`, and `eap_fee`
numeric fields for programmatic consumption.

## Credentials

The script resolves credentials in this order:

1. Env vars `NAMECHEAP_API_USER` + `NAMECHEAP_API_KEY` + `NAMECHEAP_CLIENT_IP`.
2. A `## Namecheap` section in `~/.claude/projects/-Users-shaharshavit/memory/api-keys.md`
   (the user's global credentials file).

If neither source resolves all three, the script exits with a clear
error. Do not hardcode keys anywhere in the skill.

The API user's **whitelisted IP must match** the IP the request
originates from. If you see `Invalid request IP`, the user's public IP
has changed — tell them to update the whitelist in the Namecheap API
dashboard and the value in their `api-keys.md`.

## Caveats & gotchas

- **Availability ≠ registerable at list price.** A domain marked
  `AVAILABLE` with `[premium $N]` means Namecheap will sell it, but at
  the premium price shown — often hundreds to thousands of dollars.
  Surface the premium flag in any summary you give the user.
- **EAP windows** (newly-launched TLDs) tack on a fee that drops over
  weeks. The script reports `EapFee`; mention it if non-zero.
- **ccTLDs with registration restrictions** (`.ai`, `.io`, `.co` are
  fine; `.de`, `.fr`, `.it` often need residency). Namecheap returns
  availability but not eligibility — flag this to the user for
  restricted TLDs.
- **Don't confuse "available" with "unused"**. A dropped domain may be
  in a registry grace period; re-check after 30–60 days if the user is
  tracking a specific target.
- **Rate-limit hygiene**: Namecheap's documented limit is 50 calls per
  minute per IP. A 50-domain batch counts as one call — another reason
  to batch.
