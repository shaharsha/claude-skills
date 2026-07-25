# proton-pass

Manage credentials and secrets from the CLI via **Proton Pass** (`pass-cli`): list vaults and items, view / create / update / delete logins, generate random passwords or passphrases, and resolve `pass://vault/item/field` secret references into template files or a command's environment — with never-print-secrets guardrails baked in.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

Handing an agent access to a password manager is useful and slightly alarming, and the alarming part isn't hypothetical: the default way to get a secret is to *print* it, and printed secrets end up in transcripts, scrollback, and shell history. So this skill's job is as much about **how not to touch secrets** as about the commands.

It also carries one gotcha that produces a bug you'd otherwise misdiagnose for an hour:

> `pass-cli run -- env X="pass://…"` has been observed passing the **literal `pass://…` URI** through as the value instead of the resolved secret.

A 78-byte URI arrives at the program as "the password". The auth failure that follows looks exactly like a wrong credential, so you go and rotate a key that was never wrong.

## What it does

```
Proton Pass vaults ──pass-cli──▶ list / view / create / update / delete items
                                              │
                                    generate password | passphrase
                                              │
        pass://vault/item/field ──┬──▶ inject  → fills {{ … }} in a template file
                                  └──▶ run     → resolves into a command's env
```

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install utilities@shaharsha-skills
```

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/proton-pass" ~/.claude/skills/proton-pass
```

## Requirements

- **`pass-cli`** — the Proton Pass CLI, signed in. The skill assumes the Homebrew path `/opt/homebrew/bin/pass-cli`; adjust for your install.
- `pass-cli test` should succeed before anything else.

## Quick start

```bash
pass-cli test                                    # check connection
pass-cli vault list
pass-cli item list "MyVault" --output json

# view a single field by URI
pass-cli item view "pass://MyVault/My Item/password"

# create a login with a generated password (length,uppercase,symbols)
pass-cli item create login --vault-name "MyVault" --title "New Service" \
  --username "user" --generate-password="20,true,true"

# ...or a passphrase (word count)
pass-cli item create login --vault-name "MyVault" --title "New Service" \
  --username "user" --generate-passphrase="5"

pass-cli item update --vault-name "MyVault" --title "Service Name" \
  --field password=new_secret

# fill {{ pass://MyVault/My DB/password }} in a template
pass-cli inject template.env
```

Common fields on a login item: `username`, `password`, `email`, `url`, `note`, `totp`.

## Security guardrails

These are the skill's operating rules, not suggestions:

1. **Never print passwords to chat output.** Use `item view` to confirm an item *exists*, not to display its secret.
2. **Prefer `inject` and `run`** for programmatic use — they resolve secrets without putting them in shell history.
3. **Use `--generate-password` / `--generate-passphrase`** when creating credentials, instead of inventing one inline.
4. **Always pass `--vault-name`** so a secret can't land in the wrong vault.

## Gotchas

- **`run -- env X="pass://…"` may not resolve.** When correctness matters, resolve explicitly and sanity-check the length before use:

  ```bash
  SECRET="$(pass-cli item view 'pass://MyVault/My DB/password')"
  [ ${#SECRET} -gt 0 ] || { echo "secret did not resolve"; exit 1; }
  ```

  A length check catches the literal-URI case immediately — a `pass://` string is long and obviously not your key.
- **`item delete` takes IDs, not titles** (`--share-id` + `--item-id`), so a delete is a two-step: find the IDs with `item list --output json`, then delete. That asymmetry is deliberate friction; don't paper over it.
- **A vault name with spaces needs quoting** everywhere it appears, including inside a `pass://` URI.

## What's in the box

`references/commands.md` has the full command surface — every flag, template formats, SSH key management, TOTP, sharing, and aliases.

## Caveats

- macOS / Homebrew binary path is assumed throughout; the commands themselves are platform-neutral.
- This skill manages secrets; it doesn't audit them. It won't tell you a credential is weak, shared, or overdue for rotation.

## License

MIT — see [LICENSE](../../LICENSE).
