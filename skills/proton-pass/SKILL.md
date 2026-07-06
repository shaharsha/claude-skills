---
name: proton-pass
description: "Manage secrets and credentials using Proton Pass CLI (pass-cli). Use when the user asks to store, retrieve, list, or manage passwords, API keys, secrets, or credentials in Proton Pass. Also triggers when the user mentions Proton Pass, pass-cli, vault management, or saving/looking up secrets."
allowed-tools: Bash(pass-cli *), Bash(/opt/homebrew/bin/pass-cli *)
---

# Proton Pass CLI — Credential Management

Binary: `/opt/homebrew/bin/pass-cli`

## Quick Reference

### Check connection
```bash
pass-cli test
```

### List vaults
```bash
pass-cli vault list
```

### List items in a vault
```bash
pass-cli item list "MyVault"
pass-cli item list "MyVault" --output json
```

### View an item
```bash
# By title
pass-cli item view --title "My Item" --vault-name "MyVault"
# By URI (returns specific field)
pass-cli item view "pass://MyVault/My Item/password"
```

### Create a login item
```bash
pass-cli item create login \
  --vault-name "MyVault" \
  --title "Service Name" \
  --username "user" \
  --password "secret" \
  --url "https://example.com"
```

### Create with generated password
```bash
# Random: length,uppercase,symbols
pass-cli item create login \
  --vault-name "MyVault" \
  --title "New Service" \
  --username "user" \
  --generate-password="20,true,true"

# Passphrase: word_count
pass-cli item create login \
  --vault-name "MyVault" \
  --title "New Service" \
  --username "user" \
  --generate-passphrase="5"
```

### Update an item
```bash
pass-cli item update \
  --vault-name "MyVault" \
  --title "Service Name" \
  --field password=new_secret \
  --field username=new_user
```

### Delete an item
```bash
pass-cli item delete --share-id SHARE_ID --item-id ITEM_ID
```

## Secret References

URI format: `pass://vault/item/field`

Common fields: `username`, `password`, `email`, `url`, `note`, `totp`

### Inject secrets into a template file
```bash
# template.env contains: DB_PASS={{ pass://MyVault/My DB/password }}
pass-cli inject template.env
```

### Run a command with secrets as env vars
```bash
pass-cli run -- env DB_PASS="pass://MyVault/My DB/password" my-command
```

> **Gotcha (verify resolution):** the `run -- env X="pass://…"` form has been
> observed to pass the **literal `pass://…` URI** as the value instead of the
> resolved secret (e.g. a 78-byte URI reached the program as the "password",
> causing an auth failure that looks like a wrong credential). When correctness
> matters, resolve explicitly with command substitution and sanity-check the
> length before use:
> ```bash
> SECRET="$(pass-cli item view 'pass://MyVault/My DB/password')"
> [ ${#SECRET} -gt 0 ] || { echo "secret did not resolve"; exit 1; }
> ```

## Security Guidelines

1. **Never print passwords in chat output.** Use `item view` only to verify items exist, not to display secrets.
2. **Prefer `inject` and `run`** for programmatic use — they resolve secrets without exposing them in shell history.
3. **Use `--generate-password` or `--generate-passphrase`** when creating new credentials instead of inline passwords.
4. **Always specify `--vault-name`** to avoid accidentally storing in the wrong vault.

## Detailed Command Reference

For full command documentation including all flags, template formats, SSH key management, TOTP, sharing, and aliases, see [references/commands.md](references/commands.md).
