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
┌──────────────────────────────────────────────────────────────────────┐
│  Data       read (records, merged headers) • find • write • append   │
│             batch-write • clear   + compare-and-set --expect, --verify│
│  Tabs       list • add • delete • rename • duplicate • move • title  │
│  Structure  freeze • resize • merge • insert • delete                │
│  Styling    format • format-header • borders • banding • validation  │
│             conditional-format • note • copy-format                  │
│  Layout     table: values + header + formats + filter in one batch   │
│  Inspect    info • inspect • revisions • export (pdf/png/csv/xlsx)   │
│  Escape     batch-update (raw requests, A1 ranges and #hex allowed)  │
└──────────────────────────────────────────────────────────────────────┘
```

One Python file, no dependencies: it uses `google-auth` if it is installed, and otherwise signs the service-account token with `cryptography` or the `openssl` CLI.

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
python3 scripts/gsheets.py --help      # no install step
```

---

## Quick start

One-time: share the target Sheet with your service account as **Editor**, and save its key at `~/.config/gdoc-sync/sa-key.json`. Alternatively, point `$GOOGLE_SA_KEY` at it, or pass `--sa-key`.

```bash
gsheets() { python3 ~/path/to/claude-skills/skills/gsheets/scripts/gsheets.py "$@"; }
ID=1tRMIvLQ...your_id...

gsheets info  $ID                                   # title, owner, last editor, tabs
gsheets read  $ID "Sheet1!A1:D20"                   # JSON 2D array
gsheets table $ID --tab Sheet1 --csv data.csv --filter --banding --auto-width
```

`ID` is the long token in the URL: `https://docs.google.com/spreadsheets/d/<ID>/edit`.

---

## Commands

Run `gsheets <command> --help` for the flags. [scripts/README.md](scripts/README.md) has the full reference, and [reference/batch-update.md](reference/batch-update.md) is the raw-request cookbook (charts, validation, pivots, gradients, Tables, RTL).

---

## Recipes

### "Make this Sheet look professional", in one atomic call

```bash
gsheets table $ID --tab Review --replace --csv data.csv \
  --filter --banding --wrap --col-format "D:E=#,##0.00" --widths 160,90,240,100,100
```

### Change one cell in a Sheet other people edit

```bash
gsheets find  $ID --tab Access --col A --value "Dana Levi"          # → row 14
gsheets read  $ID "Access!F14" > before.json
gsheets write $ID "Access!F14" --values-json '[["Admin"]]' --expect @before.json   # exit 3 if F14 changed
```

### CSV-driven review Sheet with pass/fail highlighting

```bash
gsheets write $ID --range "Review!A1" --csv fixtures.csv
gsheets format-header $ID --tab Review --bg "#0b8043" --fg "#ffffff" --filter
gsheets conditional-format $ID --range "Review!D2:D" \
  --condition TEXT_EQ --value "fail" --bg "#fce8e6" --fg "#b71c1c"
gsheets conditional-format $ID --range "Review!D2:D" \
  --condition TEXT_EQ --value "pass" --bg "#e6f4ea" --fg "#137333"
```

### Multi-tab dashboard with formulas

```bash
gsheets add-tab          $ID --title Summary --index 0 --color "#1a73e8"
gsheets add-tab          $ID --title Raw     --index 1                  
gsheets write            $ID --range "Raw!A1" --csv raw.csv             
gsheets format-header    $ID --tab Raw --filter                         
gsheets write            $ID --range "Summary!A1" \
  --values-json '[["KPI","Value"],["MRR","=SUM(Raw!C:C)"]]'                          
gsheets format-header    $ID --tab Summary                              
```

The `=SUM(Raw!C:C)` evaluates because `--value-input-option` defaults to `USER_ENTERED` (Sheets parses the value as a user typing would).

---

## Auth

First match wins: `--sa-key PATH`, then `$GOOGLE_SA_KEY`, then `~/.config/gdoc-sync/sa-key.json`, then gcloud ADC. A service account is the recommended route: it works headless, never hits a consent screen, and one key serves gsheets, gdoc-sync and gslides-sync. A service account can't create files, so create the Sheet in the UI and share it.

Full setup, including the "This app is blocked" workaround for ADC and the org-policy-blocks-key-creation case: [reference/auth-setup.md](reference/auth-setup.md).

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
| Charts / pivots / protected ranges / named ranges | No wrappers. Use `batch-update` with raw JSON; see [reference/batch-update.md](reference/batch-update.md). |

---

## Dependencies

- **Python 3.9+**, stdlib only (`urllib.request`)
- Service-account signing uses whichever is present: `google-auth` (+ `requests`), `cryptography`, or the `openssl` CLI
- `export --format png` needs `pdftoppm` (poppler) or macOS `sips`
- gcloud ADC auth (fallback) needs the `gcloud` CLI on PATH

---

## Related skills

- [gdoc-sync](../gdoc-sync) — Markdown → Google Docs.
- [gslides-sync](../gslides-sync) — `.pptx` → Google Slides.

One service account works for all three; just enable each API in its project.

## License

MIT — see [LICENSE](../../LICENSE).
