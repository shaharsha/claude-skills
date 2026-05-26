# Auth setup

Two supported auth paths for `gsheets.py`. Service account is strongly recommended for the same reasons as `gdoc-sync`: stable over time, works in CI, doesn't hit Google's "this app is blocked" consent screen, and is sharable with teammates by handing them the JSON.

## Path A: Service account (recommended)

One-time setup, ~5 minutes.

### 1. Create (or reuse) a Google Cloud project

[console.cloud.google.com](https://console.cloud.google.com/) → pick or create a project. A personal "sandbox" project is fine — there's no cost. Note the **project ID**.

**Org-policy caveat:** if your org disables SA key creation (the constraint `iam.disableServiceAccountKeyCreation`), you'll see `Key creation is not allowed on this service account` in step 4. The fix is to use a **personal-Google-Cloud project** (gmail.com account, not an org account) where org policies don't apply. The SA only needs per-Sheet access (granted by sharing in step 5), so it doesn't need to live in the same project that owns the Sheet.

### 2. Enable the Sheets and Drive APIs

Both required. Sheets API for the main operations, Drive API for the `info` subcommand's metadata lookup (owner, modified time, `canEdit`).

- [Google Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com)
- [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)

Click **Enable** on each. Propagation takes a few seconds — if your first call returns `API has not been used in project... or it is disabled`, wait 1-3 minutes.

### 3. Create a service account

[Cloud Console → IAM & Admin → Service Accounts → Create service account](https://console.cloud.google.com/iam-admin/serviceaccounts).

- **Name**: anything (e.g. `gsheets-sync`)
- **Grant access**: no project-level roles needed. The SA gets per-Sheet permissions via sharing in step 5.

### 4. Download the SA key

On the service account's **Keys** tab: **Add Key → Create new key → JSON**. A file like `my-project-abc123.json` downloads. Note the SA's email — it looks like `gsheets-sync@my-project.iam.gserviceaccount.com`.

The private key inside the JSON is sensitive. Keep it out of git (add `*.json` next to it to a `.gitignore`) and out of public Slack channels.

### 5. Share each target Sheet with the SA

Open the Sheet in your browser → **Share** → paste the SA email → set permission to **Editor** → uncheck "Notify people" (it's a robot, no inbox) → **Share**.

**Repeat for every Sheet you want the SA to touch.** The SA gets per-file access, not org-wide access.

### 6. Install the Python dep

```bash
pip install google-auth
```

(Optional alternative: `pip install cryptography` — the script will mint JWTs itself without `google-auth`.)

### 7. Run

```bash
scripts/gsheets.py info <SPREADSHEET_ID> --sa-key /path/to/sa-key.json
```

If you see the spreadsheet's name and tabs, you're set.

## Path B: gcloud ADC (fallback)

Works for one-off use but Google blocks the Drive scope on the default gcloud OAuth client, which leads to friction.

### Standard attempt

```bash
gcloud auth application-default login
```

Default cloud-platform scope **does not include Sheets/Drive write**. You'll get `403 Forbidden — Request had insufficient authentication scopes` on the first call.

### Attempt 2 — explicit scopes

```bash
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive
```

The browser opens a consent screen. If Google shows **"This app is blocked"**, that's Google's sensitive-scope policy applied to the default gcloud OAuth client. Move to attempt 3.

### Attempt 3 — your own OAuth client

Bypass the block with an OAuth client you own.

1. [Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials) in a project you own
2. **Create Credentials → OAuth client ID → Desktop app**
3. **Download JSON** (filename: `client_secret_*.json`)
4. Run:

```bash
gcloud auth application-default login \
  --client-id-file=/path/to/client_secret_*.json \
  --scopes=https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive
```

The consent screen now shows *your* app name and won't be blocked.

### Attempt 4 — impersonate a service account

If you already have an SA (e.g., org policy blocks key downloads but permits SA creation), you can ADC-impersonate it without a key file. Grant your user `roles/iam.serviceAccountTokenCreator` on the SA, then:

```bash
gcloud auth application-default login \
  --impersonate-service-account=gsheets-sync@my-project.iam.gserviceaccount.com \
  --scopes=https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive
```

This was the path the `ginger-agent-demo` project ended up on when SA key downloads were org-blocked.

### Once authenticated

```bash
scripts/gsheets.py info <SPREADSHEET_ID>     # no --sa-key
```

The script calls `gcloud auth application-default print-access-token --scopes=...` internally. The explicit `--scopes` flag is critical — without it, the printed token defaults to cloud-platform-only and Sheets calls 403 even though ADC was configured with the right scopes. Already encoded in the script; mentioning here in case you debug.

### Token expiration

gcloud ADC tokens last ~1 hour and refresh automatically while the refresh token is valid. Re-run `gcloud auth application-default login` if you see `Reauthentication failed` or `invalid_grant`.

## Which should you pick?

| Criterion | Service account | gcloud ADC |
|---|---|---|
| Stable over time | ✅ | ❌ (tokens expire, consent screen changes, "app blocked" surfaces) |
| Works in CI / headless | ✅ | ❌ (needs interactive login) |
| Per-Sheet access control | ✅ (share with SA email) | ✅ (uses your personal access) |
| Audit trail | Shows as "service account" | Shows as you |
| Setup time | ~5 min one-time | ~2 min on the lucky path, hours when "app blocked" hits |
| Shareable with teammates | ✅ (hand them the JSON) | ❌ (each person auths themselves) |
| Affected by `iam.disableServiceAccountKeyCreation` org policy | Yes — use personal-Cloud project | No |

**Default: service account.** Use ADC only when SA setup is blocked end-to-end.

## Required scopes

The script asks for both, always:

- `https://www.googleapis.com/auth/spreadsheets` — Sheets API operations
- `https://www.googleapis.com/auth/drive` — Drive metadata lookup (for `info`)

If you'd prefer least-privilege, you can swap `drive` for `drive.file` (access only to files the app has been opened with) — but `drive.file` is unreliable for SA-based access since the SA doesn't "open" files in any UI sense. Use full `drive` scope unless you have a specific reason not to.

## Diagnosing 403s

In order of likelihood:

1. **Sheet not shared with SA.** Open the Sheet, click Share, confirm the SA email shows as Editor. `cat sa-key.json | jq -r .client_email` to double-check which SA you're sharing with.
2. **API not enabled.** Visit the [Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com) and [Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com) pages in the SA's project. If just enabled, wait 1-3 minutes.
3. **Using gcloud ADC without explicit scopes.** Re-login with `--scopes=...spreadsheets,...drive`.
4. **Sharing with a different SA.** The SA in your key JSON's `client_email` must exactly match the email you shared the Sheet with — typos go unnoticed because Drive accepts arbitrary email shares.
5. **Org policy blocking external sharing.** Some Google Workspace orgs disable external-user sharing — the SA might count as external. Check with your Workspace admin.

## Diagnosing 404s

Almost always: **the SA can't see the file**. This is identical to a 403 in user-experience terms, but Drive returns 404 specifically when the caller lacks even read access. Re-share the Sheet with the SA email and the 404 should become a 200.
