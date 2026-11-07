# Auth setup

Two supported auth paths for `sync-gslides.py`. Pick one and do the setup once. Service account is strongly recommended.

If you already use [`gdoc-sync`](../../gdoc-sync) with a service account, **the same SA works** — skip to step 2 (enable Slides API), then step 5 (share the target Slides).

## Path A: Service account (recommended)

One-time setup, ~5 minutes. Reliable, scriptable, doesn't hit Google's OAuth consent screen at all.

### 1. Create (or reuse) a Google Cloud project

Open [console.cloud.google.com](https://console.cloud.google.com/), pick or create a project. Note the **project ID**. A personal "sandbox" project is fine — there's no cost.

### 2. Enable the Drive and Slides APIs

Both are required. Enable them in your project:

- [Google Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)
- [Google Slides API](https://console.cloud.google.com/apis/library/slides.googleapis.com)

Click **Enable** on each page. Takes a few seconds to propagate — if the first sync fails with `"API not used... disabled"`, wait 1-3 minutes and retry.

### 3. Create a service account

[Cloud Console → IAM & Admin → Service Accounts → Create service account](https://console.cloud.google.com/iam-admin/serviceaccounts).

- **Name**: anything (e.g., `gslides-sync` — or reuse your existing `gdoc-sync` SA)
- **Grant access**: no project-level roles needed — the SA only needs per-Slides access, which you grant by sharing the file in step 5.

### 4. Download the SA key

On the service account's **Keys** tab: **Add Key → Create new key → JSON**. A file like `my-project-abc123.json` downloads. Keep it somewhere safe; the private key inside is sensitive. Note the SA's email — it looks like `gslides-sync@my-project.iam.gserviceaccount.com`.

### 5. Share the target Slides with the SA

Open the Google Slides, click **Share**, paste the SA email as **Editor**. Uncheck "Notify people" (the SA has no inbox). Hit Send.

**You must repeat this step for every Slides you want to sync** — the SA gets per-file permissions, not org-wide access.

### 6. Put the key where the scripts look for it

```bash
mkdir -p ~/.config/gdoc-sync && mv ~/Downloads/my-project-abc123.json ~/.config/gdoc-sync/sa-key.json
chmod 600 ~/.config/gdoc-sync/sa-key.json
```

Key lookup, first match wins: `--sa-key PATH`, then `$GOOGLE_SA_KEY`, then `~/.config/gdoc-sync/sa-key.json`, then gcloud ADC (Path B). The same key serves gdoc-sync, gslides-sync and gsheets.

Nothing needs installing. The script uses `google-auth` when it is importable, and otherwise signs the token with `cryptography` or the `openssl` CLI, so a bare `python3` works. `uv run scripts/sync-gslides.py …` also works.

### 7. Run

```bash
python3 scripts/sync-gslides.py deck.pptx --pres-id PRES_ID
```

### What a service account can't do

A service account has **no Drive storage**, so it can't create files: new Docs, decks, uploads and copies all fail with `403 storageQuotaExceeded`. It *can* overwrite files it has been given access to, and it can create folders. Create the target deck in the UI and share it. When a workflow has to create files, such as narrating-pptx's narration videos, keep them in a shared drive where the service account is a Content Manager. Or drag them in once by hand, and let later runs overwrite them in place.

## Path B: gcloud ADC (fallback)

Works but friction-heavy because Google blocks sensitive OAuth scopes (Drive write) on the default gcloud client.

### Standard attempt

```bash
gcloud auth application-default login
```

This gets a token with `cloud-platform` scope, which **does not include Drive write or Slides write**. You'll see `403 Forbidden` on the first PATCH.

### Attempt 2 — explicit scopes

```bash
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/presentations,https://www.googleapis.com/auth/cloud-platform
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
  --scopes=https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/presentations,https://www.googleapis.com/auth/cloud-platform
```

Consent screen now shows *your* app name and won't be blocked.

### Once authenticated

```bash
python3 scripts/sync-gslides.py deck.pptx --pres-id PRES_ID     # no key file found, so ADC is used
```

The script runs `gcloud auth application-default print-access-token --scopes=…`. With user credentials, `--scopes` only works for scopes granted at `login`, so log in with them (attempt 2 or 3). Another option is to impersonate a service account: `gcloud auth application-default login --impersonate-service-account=SA_EMAIL --scopes=…`.

### Token expiration

gcloud ADC tokens refresh automatically while the refresh token is valid. Re-run `gcloud auth application-default login` if you see `Reauthentication failed` or `400 Bad Request: invalid_grant`.

## Which should you pick?

| Criterion | Service account | gcloud ADC |
|---|---|---|
| Stable over time | ✅ | ❌ (tokens expire, consent screen changes) |
| Works in CI / headless | ✅ | ❌ (needs interactive login) |
| Per-Slides access control | ✅ (share with SA email) | ✅ (uses your personal access) |
| Audit trail | Shows as "service account" | Shows as you |
| Setup time | ~5 min one-time | ~2 min but may fail on Google's policy |
| Shareable with teammates | ✅ (hand them the JSON) | ❌ (each person auths themselves) |

**Default: service account.** Fall back to ADC only if the SA path is blocked for some reason (e.g., your org's GCP doesn't allow SA key downloads).
