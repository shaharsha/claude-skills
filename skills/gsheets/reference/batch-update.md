# `batch-update` cookbook — raw `requests[]` JSON

Templates for operations the wrapper subcommands don't cover. Each is a complete request you can drop into a file and run with:

```bash
gsheets batch-update <SPREADSHEET_ID> --requests @template.json
```

Or inline (small ones):

```bash
gsheets batch-update <ID> --requests '[{"unmergeAllCells": {"sheetId": 0}}]'
```

**Always look up the numeric `sheetId` first** — most requests need it, not the title:

```bash
gsheets list-tabs <ID>
```

In the examples below, `SHEET_ID` is a placeholder for the integer from that output.

## Index

1. [Data validation (dropdown)](#1-data-validation-dropdown)
2. [Protected range](#2-protected-range)
3. [Named range](#3-named-range)
4. [Chart — column chart](#4-chart--column-chart)
5. [Pivot table](#5-pivot-table)
6. [Color-scale conditional formatting (gradient)](#6-color-scale-conditional-formatting-gradient)
7. [Delete a conditional format rule](#7-delete-a-conditional-format-rule)
8. [Filter view (per-user saved filter)](#8-filter-view-per-user-saved-filter)
9. [Set right-to-left direction on a tab](#9-set-right-to-left-direction-on-a-tab)
10. [Hyperlink in a cell](#10-hyperlink-in-a-cell)
11. [Add a note (comment) to a cell](#11-add-a-note-comment-to-a-cell)
12. [Multiple requests in one atomic batch](#12-multiple-requests-in-one-atomic-batch)

---

## 1. Data validation (dropdown)

Adds a dropdown to a range, restricting values to a list.

```json
[
  {
    "setDataValidation": {
      "range": {
        "sheetId": SHEET_ID,
        "startRowIndex": 1,
        "startColumnIndex": 3,
        "endColumnIndex": 4
      },
      "rule": {
        "condition": {
          "type": "ONE_OF_LIST",
          "values": [
            {"userEnteredValue": "pending"},
            {"userEnteredValue": "approved"},
            {"userEnteredValue": "rejected"}
          ]
        },
        "showCustomUi": true,
        "strict": true
      }
    }
  }
]
```

`showCustomUi: true` renders the dropdown chip. `strict: true` blocks invalid entries.

For dropdown values from another range, use `ONE_OF_RANGE`:

```json
"condition": {
  "type": "ONE_OF_RANGE",
  "values": [{"userEnteredValue": "=Lookups!A2:A100"}]
}
```

## 2. Protected range

Lock cells against editing. Optionally allow named editors.

```json
[
  {
    "addProtectedRange": {
      "protectedRange": {
        "range": {
          "sheetId": SHEET_ID,
          "startRowIndex": 0,
          "endRowIndex": 1
        },
        "description": "Header row — do not edit",
        "warningOnly": false,
        "editors": {
          "users": ["owner@example.com"]
        }
      }
    }
  }
]
```

`warningOnly: true` shows a "Are you sure?" prompt but allows the edit. `false` blocks non-editors entirely.

## 3. Named range

```json
[
  {
    "addNamedRange": {
      "namedRange": {
        "name": "SalesData",
        "range": {
          "sheetId": SHEET_ID,
          "startRowIndex": 1,
          "endRowIndex": 1000,
          "startColumnIndex": 0,
          "endColumnIndex": 5
        }
      }
    }
  }
]
```

After this, formulas elsewhere can reference `SalesData` instead of `Sheet1!A2:E1000`.

## 4. Chart — column chart

```json
[
  {
    "addChart": {
      "chart": {
        "spec": {
          "title": "Monthly revenue",
          "basicChart": {
            "chartType": "COLUMN",
            "legendPosition": "BOTTOM_LEGEND",
            "axis": [
              {"position": "BOTTOM_AXIS", "title": "Month"},
              {"position": "LEFT_AXIS",   "title": "Revenue (USD)"}
            ],
            "domains": [
              {"domain": {"sourceRange": {"sources": [{
                "sheetId": SHEET_ID,
                "startRowIndex": 0, "endRowIndex": 13,
                "startColumnIndex": 0, "endColumnIndex": 1
              }]}}}
            ],
            "series": [
              {"series": {"sourceRange": {"sources": [{
                "sheetId": SHEET_ID,
                "startRowIndex": 0, "endRowIndex": 13,
                "startColumnIndex": 1, "endColumnIndex": 2
              }]}}, "targetAxis": "LEFT_AXIS"}
            ],
            "headerCount": 1
          }
        },
        "position": {
          "overlayPosition": {
            "anchorCell": {"sheetId": SHEET_ID, "rowIndex": 14, "columnIndex": 0},
            "widthPixels": 600,
            "heightPixels": 400
          }
        }
      }
    }
  }
]
```

Other `chartType` values: `LINE`, `AREA`, `BAR`, `PIE` (uses `pieChart` not `basicChart`), `SCATTER`, `COMBO`.

## 5. Pivot table

Pivot tables live inside a `updateCells` request — you write a single cell whose `userEnteredValue` is empty but whose `pivotTable` populates the area downward.

```json
[
  {
    "updateCells": {
      "rows": [{
        "values": [{
          "pivotTable": {
            "source": {
              "sheetId": SHEET_ID,
              "startRowIndex": 0,
              "startColumnIndex": 0,
              "endColumnIndex": 5
            },
            "rows": [{"sourceColumnOffset": 0, "showTotals": true, "sortOrder": "ASCENDING"}],
            "columns": [{"sourceColumnOffset": 1, "showTotals": true, "sortOrder": "ASCENDING"}],
            "values": [{"summarizeFunction": "SUM", "sourceColumnOffset": 3}]
          }
        }]
      }],
      "start": {"sheetId": TARGET_SHEET_ID, "rowIndex": 0, "columnIndex": 0},
      "fields": "pivotTable"
    }
  }
]
```

`sourceColumnOffset` is 0-indexed within the source range.

## 6. Color-scale conditional formatting (gradient)

```json
[
  {
    "addConditionalFormatRule": {
      "index": 0,
      "rule": {
        "ranges": [{
          "sheetId": SHEET_ID,
          "startRowIndex": 1,
          "startColumnIndex": 4, "endColumnIndex": 5
        }],
        "gradientRule": {
          "minpoint": {
            "type": "MIN",
            "colorStyle": {"rgbColor": {"red": 0.98, "green": 0.94, "blue": 0.94}}
          },
          "midpoint": {
            "type": "PERCENTILE", "value": "50",
            "colorStyle": {"rgbColor": {"red": 0.98, "green": 0.73, "blue": 0.41}}
          },
          "maxpoint": {
            "type": "MAX",
            "colorStyle": {"rgbColor": {"red": 0.85, "green": 0.20, "blue": 0.20}}
          }
        }
      }
    }
  }
]
```

`type` for each point: `MIN` / `MAX` / `NUMBER` / `PERCENT` / `PERCENTILE`. `value` is required for non-MIN/MAX types.

## 7. Delete a conditional format rule

Rules are indexed per-sheet, starting at 0. To delete the second rule on a sheet:

```json
[
  {"deleteConditionalFormatRule": {"sheetId": SHEET_ID, "index": 1}}
]
```

Deleting rule N shifts later rules down — if you're deleting multiple, work from highest index downward.

## 8. Filter view (per-user saved filter)

Filter *views* don't block others from seeing the unfiltered sheet, unlike basic filters.

```json
[
  {
    "addFilterView": {
      "filter": {
        "title": "My open tasks",
        "range": {
          "sheetId": SHEET_ID,
          "startRowIndex": 0, "endRowIndex": 1000,
          "startColumnIndex": 0, "endColumnIndex": 6
        },
        "criteria": {
          "4": {
            "hiddenValues": ["done", "cancelled"]
          }
        }
      }
    }
  }
]
```

Criteria keys are column indices as strings. `hiddenValues` filters those values OUT.

## 9. Set right-to-left direction on a tab

For Hebrew / Arabic data:

```json
[
  {
    "updateSheetProperties": {
      "properties": {"sheetId": SHEET_ID, "rightToLeft": true},
      "fields": "rightToLeft"
    }
  }
]
```

This swaps the column order in the UI (A is rightmost). Cell content's internal bidi rendering is automatic.

## 10. Hyperlink in a cell

The easiest path is a `HYPERLINK` formula via `values.update` (not batchUpdate):

```bash
gsheets write $ID --range "Sheet1!A1" --values-json '[["=HYPERLINK(\"https://example.com\",\"Click me\")"]]'
```

With `--value-input-option USER_ENTERED` (the default), Sheets evaluates the formula and you get a clickable link.

To embed a rich-text link in a cell that ALSO has plain text, use `updateCells` with `userEnteredFormat.textFormat.link`:

```json
[
  {
    "updateCells": {
      "rows": [{
        "values": [{
          "userEnteredValue": {"stringValue": "Click me"},
          "textFormatRuns": [
            {"startIndex": 0, "format": {"link": {"uri": "https://example.com"}, "underline": true, "foregroundColor": {"red": 0.07, "green": 0.45, "blue": 0.91}}}
          ]
        }]
      }],
      "start": {"sheetId": SHEET_ID, "rowIndex": 0, "columnIndex": 0},
      "fields": "userEnteredValue,textFormatRuns"
    }
  }
]
```

## 11. Add a note (comment) to a cell

Sheets distinguishes **notes** (yellow corner badge, attached to a cell) from **comments** (chat threads). Notes are easy; comments require the Drive Comments API.

```json
[
  {
    "updateCells": {
      "rows": [{
        "values": [{"note": "Asaf flagged this for review on 2026-05-12"}]
      }],
      "start": {"sheetId": SHEET_ID, "rowIndex": 4, "columnIndex": 2},
      "fields": "note"
    }
  }
]
```

## 12. Multiple requests in one atomic batch

The `batchUpdate` endpoint is atomic. Bundle related ops:

```json
[
  {"addSheet": {"properties": {"title": "Q3 Review"}}},
  {
    "updateSheetProperties": {
      "properties": {"sheetId": <ID_FROM_PREV_REPLY>, "gridProperties": {"frozenRowCount": 1}},
      "fields": "gridProperties.frozenRowCount"
    }
  }
]
```

⚠ **You can't reference the new sheet's ID in a subsequent request inside the same batch** — the API doesn't expose request-result chaining. Either do it in two batches, OR pre-compute a sheetId yourself in the `addSheet` properties (Sheets accepts user-supplied integer IDs as long as they don't collide):

```json
[
  {"addSheet": {"properties": {"sheetId": 9999, "title": "Q3 Review"}}},
  {"updateSheetProperties": {
    "properties": {"sheetId": 9999, "gridProperties": {"frozenRowCount": 1}},
    "fields": "gridProperties.frozenRowCount"
  }}
]
```

This is the canonical trick for "create + configure in one shot."

---

## Further reading

- [batchUpdate Request reference](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/request) — the full enum of ~60 request types
- [Samples by task](https://developers.google.com/sheets/api/samples) — Google's own cookbook
- [GridRange](https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/other#GridRange) — the half-open-interval coordinate format
