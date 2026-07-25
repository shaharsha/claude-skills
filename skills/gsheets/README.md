# gsheets

A comprehensive Python CLI over the **Google Sheets API v4**: write data, manage tabs, style headers, freeze rows, set column widths, add filters, apply conditional formatting and banding — or drop to a raw `batchUpdate` escape hatch for anything more exotic. Works as a standalone CLI and as an agent skill.

Part of [shaharsha/claude-skills](../..). MIT.

Sister skill to [gdoc-sync](../gdoc-sync) (Markdown → Google Docs) and [gslides-sync](../gslides-sync) (`.pptx` → Google Slides). Same service-account auth model; same retry semantics; different surface.

---

## Why

The Google Sheets web UI is great for humans. For programmatic workflows — pushing a CSV nightly into a stakeholder review Sheet, generating a multi-tab dashboard, applying consistent header styling across N Sheets — the UI is the wrong abstraction. The Sheets API does the right thing, but its `batchUpdate` endpoint exposes ~60 request types with a `userEnteredFormat.textFormat.fields`-mask convention that nobody enjoys writing by hand.

`gsheets.py` is one Python file wrapping the common 90% of those request types as named subcommands, with a `batch-update` escape hatch for the long tail.

## What it does

```
┌──────────────────────────────────────────────────────────────────┐
│  Data       read • write • append • clear                        │
│  Tabs       list • add • delete • rename • duplicate             │
│  Structure  freeze • resize-cols • resize-rows • merge • insert  │
│  Styling    format • format-header • borders • banding           │
│             conditional-format                                   │
│  Filter     add-filter • clear-filter • sort                     │
│  Escape     batch-update (raw Sheets batchUpdate requests[])     │
└──────────────────────────────────────────────────────────────────┘
```

One stdlib-only Python script. Optional `google-auth` for service-account auth (recommended).

---

## Install

### Claude Code

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install documents-and-decks@shaharsha-skills
```

Or install the whole monorepo:

```bash
/plugin install shaharsha-skills@shaharsha-skills
```

### Standalone CLI

```bash
git clone https://github.com/shaharsha/claude-skills.git
cd claude-skills/skills/gsheets
pip install google-auth        # for --sa-key auth (recommended)
./scripts/gsheets.py --help
```

---

## Quick start

One-time: share the target Sheet with your service account as **Editor** (right-click → Share → paste SA email).

```bash
SPREADSHEET_ID=1tRMIvLQ...your_id...

# Inspect what we're about to touch
./scripts/gsheets.py info $SPREADSHEET_ID --sa-key ~/sa.json

# Write data + style the header + auto-fit columns
./scripts/gsheets.py write $SPREADSHEET_ID \
  --range "Sheet1!A1" --csv data.csv --sa-key ~/sa.json

./scripts/gsheets.py format-header $SPREADSHEET_ID \
  --tab Sheet1 --bg "#1a73e8" --fg "#ffffff" --filter --sa-key ~/sa.json

./scripts/gsheets.py resize-cols $SPREADSHEET_ID \
  --tab Sheet1 --cols A:Z --auto --sa-key ~/sa.json
```

`SPREADSHEET_ID` is the long token in the URL: `https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`.

---

## Commands

For full per-subcommand flags, run `./scripts/gsheets.py <cmd> --help`.

```
Data           read           --range
               write          --range --values-json|--csv|--values-stdin [--value-input-option]
               append         --range --values-json|--csv [--insert-data-option]
               clear          --range

Tabs           list-tabs
               add-tab        --title [--rows --cols --index --color]
               delete-tab     --title
               rename-tab     --from --to
               duplicate-tab  --from --to [--index]

Structure      freeze         --tab [--rows N --cols N]
               resize-cols    --tab --cols A:C  (--width N | --auto)
               resize-rows    --tab --rows 1:3  (--height N | --auto)
               merge          --range [--merge-type MERGE_ALL|MERGE_COLUMNS|MERGE_ROWS]
               unmerge        --range
               insert-rows / delete-rows  --tab --rows 5:7
               insert-cols / delete-cols  --tab --cols B:D

Styling        format         --range [--bg --fg --bold --italic --font-size --font
                                       --align --valign --wrap --number-format]
               format-header  --tab [--bg --fg --filter]
               borders        --range [--all | --top --bottom --left --right --inner]
                              [--style SOLID|DOTTED|DASHED|... --color #hex]
               banding        --range [--header-bg --first-bg --second-bg --footer-bg]
               conditional-format --range
                              [--condition <TYPE> --value V [--bg --fg --bold]]
                              | [--rule @rule.json]

Filter/sort    add-filter     --range
               clear-filter   --tab
               sort           --range --by "B:desc,C:asc"

Escape         batch-update   --requests @requests.json (or inline JSON)
Meta           info           (safe dry-run probe)
```

See [scripts/README.md](scripts/README.md) for the full flag reference and [reference/batch-update.md](reference/batch-update.md) for the escape-hatch cookbook (charts, data validation, pivots, gradients, RTL, hyperlinks, …).

---

## Recipes

### "Make this Sheet look professional"

```bash
ID=1tRMIvLQ...
SA=~/sa.json

./scripts/gsheets.py write           $ID --range "Review!A1" --csv data.csv          --sa-key $SA
./scripts/gsheets.py format-header   $ID --tab Review --filter                       --sa-key $SA
./scripts/gsheets.py resize-cols     $ID --tab Review --cols A:Z --auto              --sa-key $SA
./scripts/gsheets.py banding         $ID --range "Review!A1:Z"                       --sa-key $SA
```

### CSV-driven review Sheet with pass/fail highlighting

```bash
./scripts/gsheets.py write $ID --range "Review!A1" --csv fixtures.csv --sa-key $SA
./scripts/gsheets.py format-header $ID --tab Review --bg "#0b8043" --fg "#ffffff" --filter --sa-key $SA
./scripts/gsheets.py conditional-format $ID --range "Review!D2:D" \
  --condition TEXT_EQ --value "fail" --bg "#fce8e6" --fg "#b71c1c" --sa-key $SA
./scripts/gsheets.py conditional-format $ID --range "Review!D2:D" \
  --condition TEXT_EQ --value "pass" --bg "#e6f4ea" --fg "#137333" --sa-key $SA
```

### Multi-tab dashboard with formulas

```bash
./scripts/gsheets.py add-tab          $ID --title Summary --index 0 --color "#1a73e8" --sa-key $SA
./scripts/gsheets.py add-tab          $ID --title Raw     --index 1                   --sa-key $SA
./scripts/gsheets.py write            $ID --range "Raw!A1" --csv raw.csv              --sa-key $SA
./scripts/gsheets.py format-header    $ID --tab Raw --filter                          --sa-key $SA
./scripts/gsheets.py write            $ID --range "Summary!A1" \
  --values-json '[["KPI","Value"],["MRR","=SUM(Raw!C:C)"]]'                           --sa-key $SA
./scripts/gsheets.py format-header    $ID --tab Summary                               --sa-key $SA
```

The `=SUM(Raw!C:C)` evaluates because `--value-input-option` defaults to `USER_ENTERED` (Sheets parses the value as a user typing would).

---

## Auth

Two paths, recommendation: **service account**.

| Path | Flag | When |
|---|---|---|
| Service account | `--sa-key /path/to/sa.json` | Default. Works in CI, no consent-screen friction, shareable. |
| gcloud ADC | *(no flag)* | Fallback. `gcloud auth application-default login --scopes=https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive` first. May hit Google's "this app is blocked" policy for the default OAuth client. |

Full setup including the "app blocked" workaround, the org-policy-blocks-key-creation case, and SA impersonation: [reference/auth-setup.md](reference/auth-setup.md).

---

## Best-practice color palettes

Sensible defaults baked into `format-header` and `banding`. All WCAG-AA contrast against white text:

| Vibe | Header bg | Header fg | Banding second-row |
|---|---|---|---|
| Google blue (default) | `#1a73e8` | `#ffffff` | `#f1f3f4` |
| Forest green | `#0b8043` | `#ffffff` | `#e6f4ea` |
| Warm amber | `#f9ab00` | `#202124` | `#fef7e0` |
| Deep slate | `#202124` | `#ffffff` | `#f8f9fa` |
| Muted teal | `#129eaf` | `#ffffff` | `#e0f7fa` |

---

## When NOT to use

| Scenario | Use instead |
|---|---|
| Sync Markdown to a Google Doc | [gdoc-sync](../gdoc-sync) |
| Sync `.pptx` to Google Slides | [gslides-sync](../gslides-sync) |
| Real-time bidirectional sync | Build a proper integration (Apps Script trigger + webhook). |
| Heavy analysis on Sheet contents | Pull with `read`, analyze in pandas / DuckDB, write back results. |
| Charts / pivots / data validation lists / protected ranges | First-class wrappers not provided — use `batch-update` with raw JSON. See [reference/batch-update.md](reference/batch-update.md). |

---

## Dependencies

- **Python 3.9+** — stdlib only for HTTP (uses `urllib.request`)
- For `--sa-key` auth: `pip install google-auth` (preferred) or `pip install cryptography` (fallback — JWT minted manually)
- For gcloud ADC auth: `gcloud` CLI on PATH

---

## Related skills

- [gdoc-sync](../gdoc-sync) — Markdown → Google Docs.
- [gslides-sync](../gslides-sync) — `.pptx` → Google Slides.

One service account works for all three; just enable each API in its project.

## License

MIT — see [LICENSE](../../LICENSE).
