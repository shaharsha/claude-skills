# Auth setup

Two supported auth paths for `sync-gdoc.py`. Pick one and do the setup once. Service account is strongly recommended.

## Path A: Service account (recommended)

One-time setup, ~5 minutes. Reliable, scriptable, doesn't hit Google's OAuth consent screen at all.

### 1. Create (or reuse) a Google Cloud project

Open [console.cloud.google.com](https://console.cloud.google.com/), pick or create a project. Note the **project ID** (e.g., `my-gdoc-sync-471234`). A personal "sandbox" project is fine — there's no cost.

### 2. Enable the Drive and Docs APIs

Both are required. Enable them in your project:

- [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)
- [Google Docs API](https://console.cloud.google.com/apis/library/docs.googleapis.com)

Click **Enable** on each page. Takes a few seconds to propagate — if the first sync fails with `"API not used... disabled"`, wait 1-3 minutes and retry.

### 3. Create a service account

[Cloud Console → IAM & Admin → Service Accounts → Create service account](https://console.cloud.google.com/iam-admin/serviceaccounts).

- **Name**: anything (e.g., `gdoc-sync`)
- **Grant access**: no project-level roles needed — the SA only needs per-Doc access, which you grant by sharing the Doc in step 5.

### 4. Download the SA key

On the service account's **Keys** tab: **Add Key → Create new key → JSON**. A file like `my-project-abc123.json` downloads. Keep it somewhere safe; the private key inside is sensitive. Note the SA's email — it looks like `gdoc-sync@my-project.iam.gserviceaccount.com`.

### 5. Share the target Doc with the SA

Open the Google Doc, click **Share**, paste the SA email as **Editor**. Uncheck "Notify people" (the SA has no inbox). Hit Send.

**You must repeat this step for every Doc you want to sync** — the SA gets per-Doc permissions, not org-wide access.

### 6. Install the Python dep

```bash
pip install google-auth
```

### 7. Run

```bash
./sync-gdoc.py file.md --doc-id DOC_ID --sa-key /path/to/my-project-abc123.json
```

## Path B: gcloud ADC (fallback)

Works but friction-heavy because Google blocks sensitive OAuth scopes (Drive write) on the default gcloud client.

### Standard attempt

```bash
gcloud auth application-default login
```

This gets a token with `cloud-platform` scope, which **does not include Drive write**. You'll see `403 Forbidden` on the first PATCH.

### Attempt 2 — explicit scopes

```bash
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/documents,https://www.googleapis.com/auth/cloud-platform
```

If Google shows **"This app is blocked"** on the consent screen — that's the Google-wide sensitive-scopes policy. Move to attempt 3.

### Attempt 3 — your own OAuth client

Bypass Google's block by using an OAuth client you control.

1. [Cloud Console → APIs & Services → Credentials](https://console.cloud.google.com/apis/credentials) in any project you own
2. **Create Credentials → OAuth client ID → Desktop app**
3. **Download JSON** (filename will be `client_secret_*.json`)
4. Run:

```bash
gcloud auth application-default login \
  --client-id-file=/path/to/client_secret_*.json \
  --scopes=https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/documents,https://www.googleapis.com/auth/cloud-platform
```

Consent screen now shows *your* app name and won't be blocked.

### Once authenticated

```bash
./sync-gdoc.py file.md --doc-id DOC_ID
```

(no `--sa-key` — script falls back to `gcloud auth application-default print-access-token`.)

### Token expiration

gcloud ADC tokens refresh automatically while the refresh token is valid. Re-run `gcloud auth application-default login` if you see `Reauthentication failed` or `400 Bad Request: invalid_grant`.

## Which should you pick?

| Criterion | Service account | gcloud ADC |
|---|---|---|
| Stable over time | ✅ | ❌ (tokens expire, consent screen changes) |
| Works in CI / headless | ✅ | ❌ (needs interactive login) |
| Per-Doc access control | ✅ (share with SA email) | ✅ (uses your personal access) |
| Audit trail | Shows as "service account" | Shows as you |
| Setup time | ~5 min one-time | ~2 min but may fail on Google's policy |
| Shareable with teammates | ✅ (hand them the JSON) | ❌ (each person auths themselves) |

**Default: service account.** Fall back to ADC only if the SA path is blocked for some reason (e.g., your org's GCP doesn't allow SA key downloads).
