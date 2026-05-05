# namecheap-domains — a Claude Code skill

Check domain availability against the Namecheap API — single domain, batch up to 50 at once, or multi-TLD sweeps of a base name. Packaged as both a standalone CLI and a [Claude Code](https://claude.com/claude-code) skill.

---

## Why

Namecheap exposes a `namecheap.domains.check` command that returns live availability for up to 50 domains in a single request. The API is XML-over-HTTP, IP-whitelisted, and rate-limited — enough friction that people default to `whois` loops or the Namecheap web UI instead. This skill wraps the API in a stdlib-only Python script so Claude (or you) can:

- verify a specific domain is free before pitching a product name,
- sweep one base name across `.com/.io/.ai/.dev/.co/.app/.xyz` in one call,
- screen dozens of brainstormed candidates in a single batch,
- flag premium / EAP (early-access) pricing surprises before a user falls in love with a name.

## What it does

```
domains  ──batch up to 50──▶  Namecheap API  ──parse XML──▶  available / taken
                                                              + premium price
                                                              + EAP fee
```

Auto-chunks any list larger than 50 (the API's hard cap — `51+` returns `"Only 50 domains are allowed in a single check command"`). No runtime dependencies beyond CPython stdlib.

## Quick start

```bash
git clone https://github.com/shaharsha/claude-skill-namecheap-domains.git
cd claude-skill-namecheap-domains

export NAMECHEAP_API_USER=your-username
export NAMECHEAP_API_KEY=your-api-key
export NAMECHEAP_CLIENT_IP=your-whitelisted-public-ip

# explicit domains
scripts/check.py foo.com bar.ai baz.io

# TLD sweep
scripts/check.py --base myproduct --tlds com,io,ai,dev,co,app

# screen a brainstormed list, show only what's free
scripts/check.py --file candidates.txt --available-only

# JSON for downstream tooling
scripts/check.py foo.com bar.ai --json
```

## Setup (one-time)

1. **Get Namecheap API access.** Sign in → Profile → Tools → "Namecheap API Access" → enable. You'll get an API key.
2. **Whitelist your public IP.** Same settings page — add the IP your requests will originate from. If your IP changes, you'll get `Invalid request IP`; update the whitelist.
3. **Export credentials** (env vars, `.env` file, or — if you use Claude Code — a `## Namecheap` block in `~/.claude/projects/<project>/memory/api-keys.md` following the pattern documented in your global `CLAUDE.md`).

## Installing as a Claude Code skill

```bash
git clone https://github.com/shaharsha/claude-skill-namecheap-domains.git \
  ~/.claude/skills/namecheap-domains
```

Restart Claude Code (or `/agents`) and the skill will register. Invoke it by:

- asking naturally: "is `brugfdjiujhrg.ai` available?", "find me an available `.io` domain for my AI startup", "check these 12 domains"
- explicitly: `/namecheap-domains`

The skill's `allowed-tools` is scoped to the exact script path, so no extra permission prompts once installed.

## Flags

| Flag | Default | Description |
|---|---|---|
| `domains...` | — | Positional — one or more explicit domains |
| `--file <path>` | — | Read one domain per line from a file (blank lines skipped) |
| `--base <name>` | — | Base name (repeatable) to combine with `--tlds` |
| `--tlds <csv>` | — | Comma-separated TLDs for `--base`, e.g. `com,io,ai` |
| `--available-only` | off | Print only available domains |
| `--json` | off | Emit JSON with full pricing fields instead of text |

## Output

Default (text):

```
AVAILABLE  brugfdjiujhrg.ai
taken      google.com
AVAILABLE  coolname.io [premium $2999.00]
AVAILABLE  newtld.app [EAP +$1000.00]
```

`--json`:

```json
[
  {
    "domain": "brugfdjiujhrg.ai",
    "available": true,
    "premium": false,
    "premium_price": 0.0,
    "icann_fee": 0.0,
    "eap_fee": 0.0
  }
]
```

## Caveats

- **Availability ≠ registerable at list price.** A domain marked `AVAILABLE` with `[premium $N]` means Namecheap will sell it, but at the premium price shown (often hundreds to thousands of dollars).
- **EAP windows** (newly-launched TLDs) tack on a fee that drops over weeks. The script reports `EapFee`; factor it into your budget.
- **ccTLDs with residency requirements** (`.de`, `.fr`, `.it`, ...) may appear available but reject registration. Namecheap's check returns availability, not eligibility.
- **Rate limit** is 50 calls/minute/IP. A 50-domain batch is one call — batch, don't loop.

## Credentials file fallback (optional)

If env vars are unset, the script will read a `## Namecheap` section from `~/.claude/projects/-Users-shaharshavit/memory/api-keys.md` (the author's convention). Change `CREDS_FILE` at the top of [scripts/check.py](scripts/check.py) or just use env vars.

## License

MIT.
