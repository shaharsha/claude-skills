# Proton Pass CLI — Full Command Reference

Source: https://protonpass.github.io/pass-cli/

## Authentication

```bash
pass-cli login                    # Interactive login
pass-cli login --password-file p  # Non-interactive
pass-cli test                     # Test connection
pass-cli info                     # Show account info
pass-cli logout                   # End session
```

## Vault Management

```bash
pass-cli vault list                           # List all vaults
pass-cli vault list --output json             # JSON output
pass-cli vault create --name "My Vault"       # Create vault
```

## Item Management

### List
```bash
pass-cli item list [VAULT_NAME]               # List items
pass-cli item list "MyVault" --output json    # JSON output
pass-cli item list --share-id SHARE_ID        # By share ID
```

Note: `--share-id` and vault name are mutually exclusive.

### Create Login
```bash
pass-cli item create login [OPTIONS]
```

| Flag | Description |
|------|-------------|
| `--vault-name NAME` | Target vault |
| `--title TITLE` | Item title |
| `--username USER` | Username |
| `--email EMAIL` | Email address |
| `--password PASS` | Password (plain text) |
| `--generate-password "len,upper,symbols"` | Generate random password (e.g. `"20,true,true"`) |
| `--generate-passphrase "word_count"` | Generate passphrase (e.g. `"5"`) |
| `--url URL` | Associated URL |
| `--get-template` | Print JSON template to stdout |
| `--from-template FILE` | Create from JSON template file |

Template JSON format:
```json
{
  "title": "Item Title",
  "username": "user",
  "email": "user@example.com",
  "password": "secret",
  "urls": ["https://example.com"]
}
```

### Create SSH Key
```bash
# Generate new key
pass-cli item create ssh-key generate \
  --vault-name "Vault" --title "My Key" \
  --key-type ed25519   # or rsa2048, rsa4096

# Import existing key
pass-cli item create ssh-key import \
  --vault-name "Vault" --title "My Key" \
  --private-key-file ~/.ssh/id_ed25519
```

Passphrase can be set via `PROTON_PASS_SSH_KEY_PASSWORD` env var.

### View
```bash
# By title
pass-cli item view --title "Item" --vault-name "Vault"

# By item ID
pass-cli item view --item-id ITEM_ID --share-id SHARE_ID

# By secret reference URI (returns specific field)
pass-cli item view "pass://Vault/Item/password"
pass-cli item view "pass://SHARE_ID/ITEM_ID/field"
```

### Update
```bash
pass-cli item update \
  --vault-name "Vault" --title "Item" \
  --field password=new_value \
  --field username=new_user \
  --field note="Updated note"
```

Supported fields: `title`, `username`, `password`, `email`, `url`, `note`.
Custom fields are created dynamically. Cannot modify `time` or `totp` fields.

### Delete
```bash
pass-cli item delete --share-id SHARE_ID --item-id ITEM_ID
```
Requires both `--share-id` and `--item-id`. Action is **irreversible**.

### TOTP
```bash
pass-cli item totp --title "Item" --vault-name "Vault"
```

### Share
```bash
pass-cli item share \
  --share-id SHARE_ID --item-id ITEM_ID \
  email@example.com --role viewer  # viewer (default), editor, manager
```

### Aliases
```bash
pass-cli item alias create --prefix myalias  # Create masked email
```

### Attachments
```bash
pass-cli item attachment download \
  --share-id SHARE_ID --item-id ITEM_ID
```

## Secret References

URI format: `pass://vault-identifier/item-identifier/field-name`

- Vault identifier: vault name or share ID
- Item identifier: item title or item ID
- Field name: `username`, `password`, `email`, `url`, `note`, `totp`, or custom field name

All three components are **required**. Field names are **case-sensitive**.

### Inject (template files)
```bash
# Template file uses {{ pass://Vault/Item/field }} syntax
pass-cli inject template.env
pass-cli inject --in-file template.env --out-file resolved.env
```

### Run (environment variables)
```bash
pass-cli run -- env DB_PASS="pass://Vault/Item/password" ./my-app
```

## Password Generation

```bash
# Standalone password generation
pass-cli password generate --length 20 --uppercase --symbols
pass-cli password passphrase --words 5

# Password strength analysis
pass-cli password analyze "my-password-here"
```

## SSH Agent

```bash
pass-cli ssh-agent start --share-id SHARE_ID
```

## Settings

```bash
pass-cli settings                              # Show current settings
pass-cli settings --default-vault "MyVault"    # Set default vault
pass-cli settings --default-output json        # Set default output format
```

## Useful Patterns

### Store a new API key
```bash
pass-cli item create login \
  --vault-name "MyVault" \
  --title "Service - API Key" \
  --username "account-id" \
  --password "the-api-key" \
  --url "https://service.com"
```

### Retrieve a password silently
```bash
pass-cli item view "pass://MyVault/Service/password"
```

### Batch inject secrets into .env
```bash
# .env.template:
# DATABASE_URL={{ pass://MyVault/PostgreSQL/password }}
# API_KEY={{ pass://MyVault/API Key/password }}
pass-cli inject .env.template > .env
```
