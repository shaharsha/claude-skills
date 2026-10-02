# Dashboard / Web UI mockup template

**Default model:** `gpt-image-2.5-sunburst` at `quality=max` (the script default) at custom resolutions up to 2560×1440. Best text rendering for dense tables, KPI cards, chart axis labels, and layout/hierarchy is where 2.5 improved most. Don't drop to `high` for dense text: on 2.5 it is only about old gpt-image-2 `medium`. For 4K retina masters (3840×2160), Sunburst still works, but OpenAI labels everything above 2560×1440 "experimental". Explore layouts with `gpt-image-2.5-flare` at `medium` (`--draft`). Use Gemini Pro 4K only if the dashboard has a prominent photoreal hero image embedded.

## Required inputs

- Product name + what it tracks
- Layout regions (sidebar / header / KPI cards / charts / tables)
- Real metric values to render (don't use Lorem Ipsum / placeholder numbers)
- Color palette (primary brand color + neutral grays as hex)
- Font family direction (Inter / system sans / etc.)
- Dark mode or light mode

## GPT Image 2.5 variant (labeled, shipped-product language) — DEFAULT

```
BACKGROUND: A shipped, production-grade web dashboard UI.

SUBJECT: "[PRODUCT NAME]" [WHAT IT IS], [LIGHT / DARK MODE].

DETAILS:
- Left sidebar [SIDEBAR WIDTH]: [LOGO AT TOP], [NAV ITEMS WITH ICONS, mark active item].
- Top header: [SEARCH / BELL / AVATAR / OTHER].
- KPI cards top-row (N across):
  - Card 1: "[METRIC]" value "[REAL NUMBER]" trend "[+X.X%]"
  - Card 2: ...
  - Card 3: ...
- [CHART DESCRIPTION — title, axes with real labels, plausible data shape].
- [TABLE DESCRIPTION — columns, N rows with realistic values].

Style: [SPECIFIC — e.g., "modern flat design, 1px light-gray dividers,
subtle soft shadows on cards, 8px rounded corners, Inter font family"].
Color: primary [HEX], neutral grays [HEX] and [HEX], accents [HEX].

CONSTRAINTS: Realistic content, no Lorem Ipsum. Render all text exactly
as specified above (verbatim), each string exactly once. No other text.
No watermark. [ASPECT RATIO].
```

**Run with:** `--size 2560x1440` (standard hi-fi) or `--size 3840x2160` (4K master, experimental). For portrait aspect like mobile dashboards, use `1024x1536`. Sunburst `max` is the default, so no `--quality` flag. Draft with `--draft` at the same size, then promote the chosen layout with a Sunburst `max` edit (`--ref dashboard-draft.png`, same `--size`, promote prompt from [../reference/openai-gpt-image.md](../reference/openai-gpt-image.md)). The script prints the actual cost per call.

## Filled example — analytics dashboard

**Brief:** "MetricsCo" SaaS analytics dashboard. Overview screen with active users / MRR / uptime KPIs, a weekly traffic chart, customer table.

**GPT Image 2.5 prompt:**
```
BACKGROUND: A shipped, production-grade web dashboard UI.

SUBJECT: "MetricsCo" SaaS analytics dashboard, light mode.

DETAILS:
- Left sidebar 240px wide: "MetricsCo" wordmark at top, 6 nav items
  (Overview active, Users, Revenue, Reports, Integrations, Settings),
  each with a clean line icon.
- Top header: search bar with placeholder "Search customers, events...";
  notification bell with small red dot; circular avatar showing "JD".
- KPI cards top-row (3 across):
  - Card 1: "Active Users" value "12,847" trend "+8.2% this week"
  - Card 2: "Monthly Recurring Revenue" value "$284K" trend "+12.4% MoM"
  - Card 3: "Uptime" value "99.94%" trend "30-day SLA met"
- A large multi-line chart titled "Weekly Traffic", x-axis Mon-Sun,
  y-axis 1.2k-4.8k, two lines (this week vs last week).
- A 5-row data table with columns: Customer, Plan, MRR, Status, Last
  Active. Rows show "Acme Corp / Enterprise / $4,200 / Active / 2 hours
  ago" and four similar realistic SaaS rows.

Style: modern flat design, white background, 1px light-gray dividers,
subtle soft shadows on cards, 8px rounded corners, Inter font family.
Primary #0B5FFF, neutral grays #F5F7FA and #1A1F36.

CONSTRAINTS: Realistic content, no Lorem Ipsum. Render all text exactly
as specified above (verbatim), each string exactly once. No other text.
No watermark. 16:9 aspect.
```

**Run with:** `--size 2560x1440` (Sunburst `max`, the default).

## Hebrew / RTL dashboard — default is direct

GPT Image 2.5 handles RTL dashboards directly (Hebrew rendered correctly on Sunburst `high`/`max` and Flare `medium` in a 2026-10-02 test). Still check every label letter by letter - final forms ם ן ץ ף ך especially. Specify RTL layout + quote Hebrew strings:

```
[Standard prompt]. The entire UI is in Hebrew, right-to-left: sidebar on
the right, content area on the left. Nav item labels quoted:
"סקירה" (Overview, active), "משתמשים", "הכנסות", "דוחות", "אינטגרציות",
"הגדרות". Heebo font. All KPI metrics in Hebrew. Each quoted label appears
exactly once; no other text.
```

See [../reference/hebrew-rtl.md](../reference/hebrew-rtl.md) for nuances.

## Tips

- **Don't try to fit too many regions.** A 6-region dashboard (sidebar + header + 3 KPI cards + chart + table + footer) is still the upper limit even on Sunburst. More regions, and each label degrades.
- **Real numbers matter.** "12,847" is far more believable than "12,000" or "X,XXX." Specify them.
- **Specify font family.** "Inter," "system sans-serif," "Helvetica Neue" all render distinctly.
- **For dark mode**, specify the background hex (e.g., `#0F1419`) and surface hex (e.g., `#1A1F2E`) explicitly.
- **Above 2560×1440** OpenAI calls 2.5 output "experimental" and results are more variable - if a pass doesn't land, reroll once before rewriting the prompt.
