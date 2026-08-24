# TOR-750 — implementation plan: **option (B), bundle `ChartView`, delete the kit's renderer**

Spec: `docs/superpowers/specs/2026-08-24-tor750-page-kit-charts-design.md`.
Builder: **Full-Stack Builder** (frontend + build wiring). `[V]` marks a Verifier gate.

**The fork is RULED and is not re-opened here.** `/adjudicate`, 2026-08-24, on TOR-750:
**(B) — bundle `ChartView` into the page kit and delete the kit's second renderer.** Option (A) and
the parity golden it required are **deleted**, not deferred; the reasons are recorded in the spec
(*What we are NOT building*, items 1–2) so that this plan does not carry a dead alternative.

**Provenance labels.** `[lane, 2ac44d42]` = re-derived first-party at
`origin/develop = 2ac44d42a180ba2fcf68313d9a78eb31ba300b32` on 2026-08-24. `[ruling]` = measured by
`/adjudicate` in the TOR-750 comment. `[TOR-785]` = measured by the blast-radius lane from the
published S3 bytes. `[relayed — 9cf4a350]` = a predecessor figure carried forward and **not**
re-derived; the ruling verified that none of the 10 commits `9cf4a350..2ac44d42` touches
`frontend/src/{charts,pagekit}`, `.claude/skills/torque-page-kit`,
`scripts/{build_page,lint_page}.py`, `tests/test_page_kit.py` or `frontend/vite.pagekit.config.ts`,
so those figures are current.

---

## 0 · Measured current state

### 0.1 The two implementations, set-compared

`frontend/src/charts/ChartView.tsx` — **820** lines, **21** recharts symbols.
`frontend/src/pagekit/entry.tsx` — **177** lines, **11** recharts symbols. `[lane, 2ac44d42]`

Computed by parsing each `import { … } from 'recharts'` block and taking set operations — never
transcribed:

```
intersection    8   Area Bar CartesianGrid Line ResponsiveContainer Tooltip XAxis YAxis
ChartView ONLY 13   Cell ComposedChart ErrorBar Label LabelList Legend Pie PieChart
                    ReferenceArea ReferenceDot ReferenceLine Scatter ScatterChart
PAGEKIT ONLY    3   AreaChart BarChart LineChart
```

**"11 of 21" reads as a subset and is not one.** `ChartView` draws every cartesian kind through one
`ComposedChart`; the kit uses three per-kind containers `ChartView` never imports. The two lanes
therefore mount structurally different recharts roots (`.recharts-line-chart` vs
`.recharts-composed-chart`), which is one more reason a parity golden was the wrong instrument.

### 0.2 The two `ChartSpec` types are different types — why (A) was unimplementable

| | `frontend/src/charts/spec.ts` | `frontend/src/pagekit/entry.tsx` |
| - | - | - |
| data shape | long — `series[].data: Point[]` | wide — `data: Row[]`, `Record<string, string\|number\|null>` |
| `ChartSpec` fields | **17** | 6 (`data series xKey format height stacked`) |
| `ChartSeries` fields | **15** | 4 (`key label emphasis nature`) |
| kinds | 7 | 3 (`lineChart` `barChart` `areaChart`) |

`[lane, 2ac44d42]` — field lists parsed from the artifact. `ChartSpec` =
`id kind orientation height stacking bar_layout x y y2 point_fields series reference_lines
reference_bands annotations legend tooltip heatmap`; `ChartSeries` =
`id name mark axis emphasis nature curve stack_group fill_to error value_labels tooltip markers
connect_gaps data`.

**There is no common input a golden could feed to both sides.** That is the finding that killed (A):
its precondition — port the kit onto the DSL type — is most of (B)'s work, with a second renderer
still standing at the end. Retained here as the *record of a settled decision*, not as an option.

### 0.3 🔴 The committed bundle is STALE — and (B) does NOT fix this

```
committed  .claude/skills/torque-page-kit/assets/vendor/torque-charts.js
           584,770 bytes  sha256 3350a022a68aca8cea446ea81adc5f27315b51cc59f0bc4a28ccc33a6dba7313
rebuilt    npx vite build --config vite.pagekit.config.ts --outDir <scratch> --emptyOutDir
           586,046 bytes  sha256 427505086f84d60b101ef503345d6e182371c1f1c3dfe6bb4311c8f0f56a0584
```

`[ruling — reproduced first-party through the repo's own config with only `--outDir` overridden;
`git status` confirmed the committed path untouched]`

Provenance, reproduced identically by two seats: the bundle and `entry.tsx` were last committed at
**`06fd73e8` (2026-07-30)**; `frontend/src/charts/theme.ts` last moved at `4ecb9b85` and
`frontend/src/charts/format.ts` at `a09fb3cf`, **both 2026-08-17** `[ruling]`.

**Against the house golden `frontend/src/charts/__fixtures__/format.fixture.json` (106 rows):**

| bundle | rows disagreeing with the golden |
| - | - |
| **committed** (built 2026-07-30) | **59 of 106** |
| fresh rebuild at HEAD | **0 of 106** ← green control: the probe can report agreement |

`[relayed — 9cf4a350, and independently reproduced by TOR-785 §5.2 with the same two figures]`

The 59 split into three classes `[relayed — 9cf4a350; the 34/8/17 split was NOT re-derived by either
later seat]`: **34 THROW** on tokens that did not exist on 2026-07-30
(`num3 num4 num0_plain usd_compact0 num_compact0 num4_signed x3_signed usd_si0 num_si0`, numeric
`year`); **8 return `—`** (`year` / `year_month` on date-string input); **17 return a DIFFERENT
NUMBER** — TOR-224's d3-vs-`Intl` divergences, e.g. `usd2 52.805` → golden `$52.80` / bundle
`$52.81`; `pct1 0.1235` → `12.3%` / `12.4%`; `x1 1.15` → `1.1×` / `1.2×`.

🔴 **THE LIVE BLAST RADIUS IS NOW MEASURED, AND IT DOES NOT CLOSE THIS TASK** `[TOR-785]`. From the
published S3 bytes, pinned to each recorded `s3_version_id`, `sha256`-matched against
`page_versions.manifest_sha`: 5 published artifacts on dev; the only real client's is
`loora/historical` v1. Of **4,684** plotted values across 14 charts plus **70** y-axis tick labels,
**7 differ** — all on `#chart-spaghetti`'s `vintage median` series, all **hover-only** (that figure
sets `dot={false}` and has no data labels), and `page_pointers` has `loora/historical` at
`serve_mode='legacy'`, so the artifact is **not served to anyone** and is reachable only through
*Version history → Preview*. Direction: the authored page reads one hundredth **higher** than the
builder page of the same slot.

> **Consequence for this plan, and it is the ruling's correction C1:** **(B) does not remove this
> class.** `frontend/vite.pagekit.config.ts:29-30` writes the bundle to the **committed** path with
> `emptyOutDir: false`, and `scripts/build_page.py:61` **reads that committed file**
> (`_replace_block(html, BUNDLE_MARK, BUNDLE.read_text() …)`; `BUNDLE` is declared at `:30`,
> `BUNDLE_MARK` at `:33`) `[lane, 2ac44d42]`. Both are true under (B) exactly as under (A) —
> staleness is a property of *committing a built artifact*, not of *which entry it builds*. (B)
> removes the **other** drift class (kit-implementation-vs-`ChartView`). **Two classes become one;
> neither becomes zero.** TOR-785's own *"Related"* line asserts otherwise and is FALSE;
> `/adjudicate` recorded that correction on TOR-785. **Phase 0 (T0.1–T0.4) is therefore REQUIRED
> UNDER THIS RULING and stays on the critical path. Do not defer it as "(B) fixes it".**

Nothing guards this today: `tests/test_page_kit.py::test_the_chart_bundle_is_committed_not_merely_built`
(`:242`) checks git *tracked-ness* only, and `test_page_css_is_not_stale` (`:271`) guards only the CSS
copy `[lane, 2ac44d42]`.

### 0.4 What the 18 DECISION slots need — a FIDELITY MEASUREMENT, not a build backlog

Population: the 18 non-retiring DECISION slots in the frozen index (6 products × `historical`,
`forecast`, `simulator`; LX retiring, SMP absent from the frozen record entirely — `_REAL_PRODUCTS`
has 7 products so the live count is 21, of which 18 are gradable). **107 figures** across their
`defaults` payloads. **All of §0.4 is `[relayed — 9cf4a350]`; none of it was re-derived at
`2ac44d42`.**

**(a) Compiled through `chart_compiler.compile_figure`** — the population an *emitter* would face:

```
line 24 · bar 16 · combo 8 · area 4 · scatter 3 · heatmap 2      = 57 compile
50 refuse (CHART_AXIS_IMPLICIT_DATE_FORMAT 28 · GROUPNORM 5 · AXIS_LINKED 4 ·
           ANNOTATIONS_NOT_CARRIABLE 3 · Y2_ZEROLINE 3 · …)
```

6 of 7 kinds are used; only `pie` is not. (Informational under (B): a hand-authored page traverses no
compiler, so these refusals are neither this ticket's problem nor its licence.)

**(b) Raw Plotly features** — the population a *hand-author* faces, which is the ruled lane. No
compiler in the path, so all 107 count.

⚠️ **READ THIS TABLE AS A FIDELITY MEASUREMENT, NOT A BUILD LIST — the ruling's correction C2.**
Under (B) the renderer arrives whole; what these rows now say is *how many figures will exercise each
capability when the pages are re-authored*, i.e. where to point T3.1's per-figure fidelity check.
**`per-series stroke width — 67 figures / 13 slots` must NOT be read as 67 figures (B) fixes.**

| capability | figures (of 107) | DECISION slots (of 18) | kit today | closed by (B)? |
| - | -: | -: | - | - |
| axis title | 105 | 13 | ✗ | ✅ `ChartView.tsx:333,411,445,466,477,485` |
| per-series stroke width | 67 | 13 | ✗ | ⚠️ **PARTLY** — two-level only (`:647`) |
| reference lines / bands | 41 | 11 | ✗ | ✅ `ReferenceArea :495` · `RcReferenceLine :507` · `ReferenceDot :529` |
| dashed line (`nature`) | 23 | 11 | ✓ `natureDash` | ✅ (already) |
| annotations | 13 | 8 | ✗ | ⚠️ **PARTLY** — `x`/`y`/`text`/`emphasis` only; six fields REFUSE (`reference_placement.ts:355+`) |
| per-point colour | 13 | 5 | ✗ | ⚠️ **PARTLY** — `bar` and `point` marks only (`:574`) |
| markers-only scatter | 12 | 6 | ✗ | ✅ `Scatter :631` |
| combo (mixed trace types) | 11 | 7 | ✗ | ✅ `ComposedChart` |
| value labels / text | 10 | 6 | ✗ | ✅ `LabelList :546` |
| second (or third) y axis | 9 | 7 | ✗ | ⚠️ **PARTLY** — second only (`yAxisId="y2" :480`); **no third axis exists** |
| error bars | 9 | 2 | ✗ | ✅ `ErrorBar :564` |
| stacked bars | 8 | 6 | ✓ `stacked` (bool) | ✅ (already) |
| heatmap | 2 | 2 | ✗ | ⚠️ **PARTLY** — cells draw (`:680-743`); **`colorbar` / `colorbar_title` are never read** |
| subplot grid | 1 | 1 | ✗ | ❌ **NOT CLOSED BY EITHER OPTION** |

Every `closed by (B)?` cell was read from the artifact at `2ac44d42` `[lane]` — bare `:N` coordinates are `ChartView.tsx`; the annotations row cites `reference_placement.ts`, and the heatmap row cites an ABSENCE (`colorbar` has **0** mentions anywhere in the renderer), which is why it carries no coordinate.

🔑 **THE ARITHMETIC, because the predecessor's "12 of 14 gaps at once" was WRONG.** The table has 14
rows, of which **12 are gaps** (`dashed line` and `stacked bars` are already ✓). **(B) closes 11 of
those 12**; `subplot grid` is closed by neither. **Three residuals sit INSIDE otherwise-closed rows
and each is absent from the CONTRACT, not from a renderer** `[lane, 2ac44d42, read from
`frontend/src/charts/spec.ts`]`:

1. **Arbitrary per-series stroke width.** `ChartSeries` has **15 fields and none is a stroke width**
   — the only `width` token in `spec.ts` is inside a comment at `:54`. `ChartView.tsx:647` gives a
   **two-level** width derived from `emphasis` (`s.emphasis === 'primary' ? 2.4 : 1.8`); the kit
   hard-codes `strokeWidth={2}` (`entry.tsx:116`). **The operational case behind TOR-745 defect 6 —
   *"thick line = per-vintage median"* — IS closed by (B)** through `emphasis: 'primary'`, which is
   exactly how that lane's own workaround worked. **3+ distinct widths in one figure is not.**
2. **A third y axis.** `ChartSeries.axis` is `'y' | 'y2'` only; `ChartSpec` carries `y` and `y2` and
   nothing else. The row above reads *"second (or third)"*; only the second half is closed.
3. **Per-point colour on `line` and `area` marks.** `ChartView.tsx:574`, verbatim: *"Only `bar` and
   `point` read these — the contract admits `Point.emphasis` for no other mark."* Whether the 13
   figures in that row are bar/point or line/area is **UNMEASURED**; T3.1 must settle it per figure.

🔴 **A SECOND, DIFFERENT CLASS: SIX CONTRACT FIELDS THE RENDERER NEVER READS.** The three above are
absent from the contract. These are **present in the contract and dropped by `ChartView`** — a
renderer gap, not a contract gap, and the two must not be conflated. Measured at `2ac44d42` by
sweeping every field declared in `frontend/src/charts/spec.ts` (comments stripped) against every
mention in `ChartView.tsx` + `reference_placement.ts` + `tooltip.tsx`, with a discriminating control
(`markers` 8 mentions, `emphasis` 14, `value_labels` 3) `[lane, 2ac44d42]`:

| field | declared | mentioned by any renderer file |
| - | - | -: |
| `HeatmapSpec.colorbar` | `spec.ts:189` | **0** |
| `HeatmapSpec.colorbar_title` | `spec.ts:190` | **0** |
| `ReferenceLine.label_position` | `spec.ts` | **0** |
| `ReferenceBand.label_position` | `spec.ts` | **0** |
| `ChartSeries.fill_to` | `spec.ts` | **0** |
| `ChartSpec.point_fields` | `spec.ts` | **0** |

**This is not hypothetical.** `frontend/src/charts/__fixtures__/combo-dual-axis.chart.json:21`
declares `"label_position": "top-start"` on a reference line, and
`api/services/{lr,tbr}/historical_analysis.py` both request a heatmap colorbar with a unit title
(`ROAS`, `cash ROAS (×)`) — so two DECISION heatmaps lose their scale legend and its units
permanently on re-author, while a mark-count check still passes.

⚠️ **The sweep is a NAME-MENTION heuristic and can only over-report.** Each of the six was then
confirmed individually (0 mentions in all three reader files); none is destructured or
dynamically accessed. **What the sweep cannot say is whether a dropped field is reader-VISIBLE** —
`fill_to` may be implicit in recharts' stacking, `point_fields` may be inert where no tooltip
references an extra. **T3.1 measures that per field; this plan does not assert it.**

🔴 **ANNOTATIONS ARE PARTIAL FOR A THIRD REASON — a REFUSAL, not a silent drop.**
`frontend/src/charts/reference_placement.ts` (`unhonouredAnnotationFields`, ~`:355`) classifies
`dx`, `dy`, `anchor`, `y_ref`, `boxed` and `arrow` as unhonoured, and `annotationProblem` **refuses**
a non-default value — `ChartView` returns `ChartError` rather than a chart. `CLAUDE.md` records this
as TOR-416's deliberate ruling: *"a half-honoured field is worse than an inert one."* So an authored
annotation reproducing a Plotly callout with an offset or a plate **fails loudly**, and only the
`x`/`y`/`text`/`emphasis` subset draws. **Lifting that refusal is TOR-416's, not this ticket's** —
`CLAUDE.md` records neutralising the projector-side sibling as freeing **zero** slots.

None of the three contract-level residuals is this ticket's work. Each is an additive contract change
(`contracts/torque_contracts/chart.py` + `scripts/gen_manifest_schema.py` + the **hand-mirror** in
`frontend/src/charts/spec.ts` + `ChartView`), of the shape TOR-201 (`markers`), TOR-254
(`Point.emphasis`) and TOR-534 (`ticks`) took. **This cuts FOR (B):** under (A) the kit's private type
could grow a `width` field unilaterally and the divergence widens; under (B) the gap closes once, in
the contract, for builder-served DSL charts and authored pages together.

⚠️ **This is a BLOCKING inventory** (`CLAUDE.md` TOR-716). It says which figures a missing capability
blocks; it cannot say how many become drawable if you add one, because a figure can need several.
Yield is T3.1's measurement, by rendering.

### 0.5 The relayed gap list, verified against the artifact

Verified first-party against `git show origin/develop:authored_pages/lr_historical/body.html`
(29,529 bytes, 15 sections) — the source bytes the published artifact was built from
`[relayed — 9cf4a350]`:

| relayed claim | reproduces? |
| - | - |
| no combined bar+line, no second axis → one figure drawn as two | ✅ *"The builder draws this as one figure with a right-hand axis."* |
| no reference lines — dotted 1.0× absent | ✅ *"…not drawable here."* |
| no scatter — `M0 dependence` renders zero charts | ✅ *"Not drawable in this kit"* block present |
| no per-series stroke width | ✅ (also `charts.js` `isHeavy` works around it via `LRMETA.emphasised`) |
| no colour-by-data-attribute | ✅ |
| layout shapes drawn as flat benchmark series | ✅ |
| **(not relayed) no axis title** | ✅ *"the kit renders no axis title"* — the **highest-incidence** gap of all |
| **(not relayed) no heatmap** | ✅ *"The builder draws this as a heatmap … the kit cannot do."* |

**Nothing relayed failed to reproduce.** Two gaps were missing from the relayed list, one of which
outranks everything on it.

### 0.6 Nothing pins the two together — with controls

```
frontend tests importing pagekit/entry     0    (git grep, rc=1)
frontend tests importing charts/ChartView  7    ← control: the grep works, the asymmetry is real
tests/test_page_kit.py                    37 tests, all lint / CSS-drift / vendoring
.github/** referencing build:page-kit      0    ← control: `npm` matches 6× in ci.yml
```

The first three rows are `[relayed — 9cf4a350]`; the CI row is `[lane, 2ac44d42]`, re-derived, and
`[ruling]` reproduced it independently.

### 0.7 Option (B) sized and lint-cleared — measured twice, by two seats

| | raw | gzip | vs the kit rebuilt at HEAD |
| - | -: | -: | - |
| kit rebuilt at HEAD | 586,046 | 169,640 | — |
| **`ChartView` bundled** | **659,510** | **187,471** | **+73,464 (+12.5%) · +17,831 (+10.5%)** |

`[ruling]` — built with a wrapper the adjudicator wrote (`createRoot` + `ChartView`, exporting `chart`
and `format`), through the same `external: []` / IIFE / `minify` shape; build time 161 ms. The
predecessor lane, with a *different* wrapper, measured `+73,563 / +17,962` `[relayed — 9cf4a350]` —
within ~100 bytes raw. **Independently reproduced.**

**Lint — the predecessor's "largest unknown about (B)" — is CLOSED, with both directions of control**
`[ruling]`, by loading `scripts/lint_page.py`'s own `NETWORK_CALL` and `NAV_SINK` regexes:

```
kit rebuilt   NETWORK_CALL=0   NAV_SINK=0
ChartView     NETWORK_CALL=0   NAV_SINK=0
controls:  fetch('https://x') -> NETWORK_CALL True    (must fire)
           location.href='x'  -> NAV_SINK     True    (must fire)
           var a = 1          -> NETWORK_CALL False   (must not fire)
```

Two committed tests already hold whatever ships to that bar —
`tests/test_page_kit.py::test_the_pinned_chart_bundle_passes_its_own_lint` (`:169`) and
`::test_the_pinned_bundle_contains_no_navigation_sink` (`:348`) `[lane, 2ac44d42]` — so swapping the
bundle re-runs the gate automatically.

**Cost model.** The bundle is inlined verbatim into every page (`build_page.py:61`), so (B) costs
~74 kB raw / ~18 kB over the wire **per published immutable artifact** — 18–21 pages ≈ 1.4 MB across
the estate. There is **no size cap anywhere in the publish path** (`git grep` across
`api/services/publishing.py`, `api/routers/artifacts.py`, `scripts/build_page.py`,
`scripts/lint_page.py` → rc=1, positive control `def ` = 3 in `build_page.py`) `[ruling]`.

**`ChartView`'s import closure is why the delta is +74 kB and not megabytes** `[lane, 2ac44d42]`:
`react`, `recharts`, and five siblings under `charts/` — `format`, `spec`, `reference_placement`,
`tooltip`, `theme`. **No API client, no router, no app context, no plotly.** TOR-734's round-2
finding *"the shared renderer cannot currently produce a self-contained chart bundle"* is
**WITHDRAWN** `[ruling §2③]`.

### 0.8 🔴 The degenerate render — explained, and the real-browser requirement it produces

The predecessor lane rendered the built IIFE bundles under jsdom and got: kit `lineChart` → 1
`.recharts-surface`, 2 `.recharts-line`; option-B `ChartView` (spec compiled from the frozen
`LR/historical` payload, 44 series) → axis title *"Month (cohort age)"*, 44 legend items, 2
`.recharts-reference-line`, **and 0 `.recharts-line`** `[relayed — 9cf4a350]`.

**That asymmetry is the repo's own documented jsdom sizing case and is NOT evidence against (B)**
`[lane, 2ac44d42]`. `ChartView.tsx:770`, verbatim: *"Explicit size. Tests must pass one:
**ResponsiveContainer measures 0 in jsdom**."* The lane's harness passed no `width`/`height`; the
repo's own working harness does (`ChartView.test.tsx:140`, `render(<ChartView spec={spec} {...SIZE} />)`).
`ChartView.tsx:803-805` records the same failure in a **browser**: *"with only a `minHeight` it
measured 0px wide and every chart rendered an empty SVG: present in the DOM, invisible on the page,
and **completely silent**."*

**The lesson that survives:** a golden or a probe generated under a mis-stubbed jsdom pins a
degenerate DOM that both sides agree on — two sides moving together. That is why T2.B4 proves
non-degeneracy in a **real browser** before anything is recorded, and why a zero-mark render is RED.

⚠️ **Where I part company with the ruling's correction C3 — a narrowing, not a disagreement.** C3's
operational instruction (*verify in a real browser; a zero-mark render is RED*) is right and is
adopted verbatim as T2.B4. Its stated *mechanism* — that the container class `tp-chart` is undefined,
so (B)'s container may have no width — is **not (B)-specific and is measurably not the live risk**:

* `tp-chart` really is undefined. At `2ac44d42` it occurs **1×** in
  `.claude/skills/torque-page-kit/assets/template.html`, **11×** in
  `authored_pages/lr_historical/body.html`, **1×** in `scripts/lint_page.py`, and **0×** in both
  tracked CSS files (`assets/torque-page.css`, `frontend/src/theme.css`) and in
  `scripts/gen_page_kit_css.py`. Control: `tp-` occurs 21× in the generated kit CSS, so the
  instrument discriminates. `[lane, 2ac44d42]` — TOR-751 §3.2 reproduces exactly.
* **But the kit's own mount already uses the identical sizing shape.** `entry.tsx:101` mounts
  `<ResponsiveContainer width="100%" height={height}>` straight onto the target element — the same
  `width="100%"` as `ChartView`'s no-`width` production branch (`ChartView.tsx:814-815`), which
  additionally wraps it in a `<div style={{width:'100%', height: h}}>` whose height is a definite
  pixel value. `[lane, 2ac44d42]`
* **And the published artifact demonstrably renders.** TOR-785 read **4,684 plotted values across 14
  charts and 70 y-axis tick labels out of a real browser's DOM** on that same page. `[TOR-785]`

So the container width today comes from the target element's ordinary block layout, not from
`tp-chart`, and (B) does not newly endanger it. **The requirement stands regardless** — it is cheap,
it is the only instrument that can distinguish "rendered" from "present but zero-width", and TOR-751
T2 should still define or delete `tp-chart`. **What must NOT be carried forward is the inference that
(B) introduces a container-width risk the kit does not already have.**

---

## 1 · Task list

Checkboxes are the Builder's. `[V]` marks a Verifier gate. Phase 0 and Phase 2 are independent of
each other and can fan out.

### Phase 0 — bundle currency (REQUIRED UNDER THIS RULING — see §0.3; do first)

- [ ] **T0.1 · Rebuild and commit the chart bundle.** `npm --prefix frontend run build:page-kit`
      (`frontend/package.json:14`), commit the resulting bytes. Expect 584,770 → 586,046.
      ⚠️ **Escalate BEFORE this lands.** Rebuilding changes what the next publish renders and makes
      the before-state harder to reconstruct. The blast radius is measured (§0.3) and small, but
      **whether `loora/historical` v1 is superseded is a decision record and Shahar's** (TOR-785).
      T0.1 does not supersede anything; it only stops the bleeding forward.
- [ ] **T0.2 · Drift guard for the JS bundle** — the sibling of `test_page_css_is_not_stale`
      (`tests/test_page_kit.py:271`). Build to a temp dir, compare bytes to the committed artifact,
      and **state the remedy in the failure message** (`npm run build:page-kit`).
      ⚠️ **Sound only if the build is byte-reproducible from a clean `npm ci`. MEASURE THAT FIRST.**
      🔴 **If it is not, T0.3 is NOT the fallback.** T0.3 exercises `TorqueCharts.format` and nothing
      else, while the bundle's entry closure is `ChartView` + `format` + `spec` +
      `reference_placement` + `tooltip` + `theme` (`ChartView.tsx:12-49`) `[lane, 2ac44d42]` — so a
      guard keyed on T0.3 reports GREEN while `theme.ts` moves, or while an axis-title change never
      reaches the committed bytes. That is a guard answering a different question from the one it is
      named for. The two admissible fallbacks are: **(a)** make the build reproducible (pin the
      minifier's inputs, strip any embedded path/timestamp) and keep the byte comparison; or **(b)**
      commit a **source-closure digest** beside the bundle — sha256 over the entry's transitive
      import closure plus `package-lock.json` — and assert the recorded digest equals the recomputed
      one. (b) needs no build determinism and covers the whole closure, which is the property (a)
      and T0.3 respectively have and lack. **Whichever is taken, say which and why.**
      **Do not ship a flaky byte guard**; a guard that fires on correct work is one somebody deletes.
      **And do not let T0.3 stand in for currency** — it is an independent behaviour check, kept for
      its own sake.
- [ ] **T0.3 · Bundle-vs-golden format-parity test.** Load the committed bundle under jsdom, run
      `TorqueCharts.format` over every row of `frontend/src/charts/__fixtures__/format.fixture.json`,
      assert **0** disagreements. Independent of build reproducibility.
      🔴 **T0.2 AND T0.3 LIVE IN THE FRONTEND VITEST SUITE, NOT `tests/test_page_kit.py`.** Both need
      node: T0.2 shells to `vite`, T0.3 needs jsdom. `.github/workflows/ci.yml` runs `test-backend`
      as `uv sync --frozen` + `uv run python -m pytest` with **no** `setup-node` and **no** `npm ci`;
      those appear only in `test-frontend`, under `working-directory: frontend`, and the two jobs do
      not share `node_modules` `[lane, 2ac44d42]`. Every page-kit test in `tests/test_page_kit.py`
      today is node-free (the CSS check runs `gen_page_kit_css.py`, which is Python). Putting these
      two there makes `test-backend` fail on a missing binary before either guard is evaluated.
      *Must-fire:* the pre-T0.1 bundle → **59** failures. *Must-not-fire:* the rebuilt bundle → **0**.
      Both numbers are already measured twice (§0.3).
- [ ] **T0.4 · Wire `build:page-kit` into `.github/workflows/ci.yml`'s `test-frontend`,** OR wire T0.2
      into it — **one of the two, and say which**, per the ticket's acceptance clause 5. Measured
      today: 0 references under `.github/`, control `npm` = 6 in `ci.yml`. Job ids stay
      `<verb>-<component>-<env>` (`tests/structure/test_dev_env_cicd.py`).
- [ ] `[V]` **Verifier gate 0.** T0.3 RED on the old bundle, GREEN on the new. `test-frontend` green.
      **Report whether the build is byte-reproducible and which shape T0.2 took.**

### Phase 1 — record the decision

- [ ] **T1.1 · Write `docs/decisions/page_kit_renderer.md`.** Records: the ruling and its date; that
      (A) and the parity golden are **deleted, not deferred**, with the two-sides-move-together
      reason; both independently-measured bundle deltas (§0.7); the lint result with its controls;
      and the three contract-level residuals of §0.4(b) so a future reader does not re-file them as
      renderer gaps. **This is a decision record, not a design doc — it must not re-argue the fork.**

### Phase 2 — bundle `ChartView`, delete the kit's renderer

- [ ] **T2.B0 · DECIDE Q4 before writing C3.** Does the kit keep `lineChart` / `barChart` /
      `areaChart` as thin adapters, or are they removed? **This is OPEN and must be decided, not
      defaulted** — it constrains the entry point's shape. Measured inputs: each published artifact
      carries its **own** inlined bundle (`build_page.py:61`), so **no already-published page is
      affected either way**; the kit exports exactly four symbols today — `lineChart`
      (`entry.tsx:97`), `barChart` (`:124`), `areaChart` (`:148`), `format` (`:177`); the affected
      parties are a future page authored against the old API and
      `authored_pages/lr_historical/charts.js`, which TOR-745 hands back for re-authoring regardless.
      **Escalate to `/adjudicate`; do not pick one and proceed.**
- [ ] **T2.B1 · New entry `frontend/src/pagekit/chartview-entry.tsx`** exposing `chart(target, spec)`
      over a **DSL `ChartSpec`**, plus `format`. Mount with `createRoot`, keeping `entry.tsx`'s loud
      failure on an unmatched target (`entry.tsx:61-69`) — *"a silent no-op here produces a page that
      looks finished with a blank space where the chart should be."* Adapters per T2.B0.
- [ ] **T2.B2 · Delete `entry.tsx`'s own recharts trees.** *Acceptance:* `from 'recharts'` returns
      **0** in `frontend/src/pagekit/**`. *Control:* the same grep against `ChartView.tsx` returns
      its 21 symbols, so the instrument discriminates.
      🔴 **The parity golden is DELETED and must not be built** — under one renderer its two sides
      are the same code.
- [ ] **T2.B2b · Update the kit's PUBLIC GUIDANCE to whatever T2.B0 decided.**
      `.claude/skills/torque-page-kit/SKILL.md:69` documents
      `TorqueCharts.lineChart|barChart|areaChart(selector, spec)` with a **wide-form** example at
      `:73`, and `.claude/skills/torque-page-kit/assets/template.html:124` carries a commented
      `TorqueCharts.lineChart(...)` example in the same wide-form shape `[lane, 2ac44d42]`. Neither
      mentions a DSL `ChartSpec`. **Both outcomes of T2.B0 need this task and neither is harmless
      without it:** if the adapters are removed, an author following the skill calls an undefined
      function and gets a blank page; if they are kept, an author never learns the API that carries
      combo, scatter, pie, heatmap, reference lines and axis titles — i.e. the whole point of (B).
      ⚠️ **Nothing reports this today.** `tests/test_page_kit.py::test_the_shipped_template_lints_clean`
      (`:44`) lints the template's bytes; a commented example naming a function that no longer exists
      passes lint. Replace both examples with a valid long-form `ChartSpec`.
- [ ] **T2.B3 · Re-point `frontend/vite.pagekit.config.ts:23` (`lib.entry`).** Leave
      `publicDir: false`, `external: []`, `emptyOutDir: false` and `minify` alone — the comments at
      `:5-19` record why each is load-bearing. Re-run the lint on the **real** entry's output and
      confirm 0 rules fire (measured clean on the adjudicator's wrapper, §0.7; re-measure on this
      one). Rebuild and commit the bundle; T0.2/T0.3 must stay green over the new bytes.
- [ ] 🔴 **T2.B4 · FIRST END-TO-END RENDER, IN A REAL BROWSER.** Build a page with
      `scripts/build_page.py` carrying **one figure of every DSL kind** — line, bar, area, combo,
      scatter, pie, heatmap — **plus an error-bar case**, open it with
      `agent-browser --session tor750-render` (never `close --all`), and **read the DOM**.
      🔴 **USE THE REPOSITORY'S OWN MARK SELECTORS, NOT THE WRAPPER CLASSES**
      (`ChartView.test.tsx:119-133` `MUST_DRAW`, read out of a committed snapshot):
      `.recharts-line-curve` · `path.recharts-rectangle` · `.recharts-area-area` ·
      `.recharts-symbols` + `.recharts-errorBar` · `.recharts-pie-sector` ·
      `.recharts-scatter-symbol`. **All > 0.**
      ⚠️ **`.recharts-line` and `.recharts-area` are WRAPPERS and must not be used.** That file's own
      docstring (`:113-117`) records why: *"A count of the wrapper is satisfied by a bar chart with no
      bars, which is how the first cut of TOR-642 reported 'element counts unchanged' while 15 paths
      were missing."* An earlier draft of this task used the wrapper classes — the exact defect the
      repo had already measured and written down.
      Also assert `document.hidden === false`, **0** `stroke-dasharray="0px …"`, **0** `clipPath`
      with `width="0"`.
      **A ZERO-MARK RENDER IS RED, NEVER A BASELINE.** *Must-fire control:* mount into a zero-width
      container → RED. ⚠️ **A screenshot does not satisfy this** — it can record frame 0 while
      looking settled (`CLAUDE.md` TOR-642), and under a starved rAF clock a settle delay yields
      *stability*, which reads as proof it is not an animation.
- [ ] 🔴 **T2.B5 · Animation flags reached the BUNDLE — A SEPARATE LANE FROM T2.B4, NOT ITS DOM.**
      `ChartView` carries 8 `isAnimationActive={false}` occurrences against `entry.tsx`'s 0, so the
      flags come free in the source — **but free in the source is not present in the bundle**, and
      that is the claim being checked.
      ⚠️ **THE PROBES CANNOT FIRE ON T2.B4's DOM AND AN EARLIER DRAFT PUT THEM THERE.** The 4
      `ZERO_STATE_PROBES` (`ChartView.test.tsx:98-103`) detect a render stuck at **frame 0**. T2.B4
      deliberately requires `document.hidden === false`, i.e. a serviced rAF clock, under which the
      animation **completes** and the settled DOM is identical whether or not the flag is set — so
      the must-fire control would come back GREEN and be read as the flag being present.
      **Run this lane the way `ChartView.test.tsx` does: mount the SHIPPED BUNDLE under vitest/jsdom
      and read `container.innerHTML` synchronously, before any rAF is pumped.** Cover **every**
      `isAnimationActive` call site — the 4 cartesian marks **and** `ErrorBar`, `Pie` and the heatmap
      `Scatter`, which a line/bar/area page never reaches.
      *Must-fire, per call site:* remove that one flag → that probe RED. *Must-not-fire:* a
      legitimate unitless DSL dash (`"6 4"`) → GREEN.
      ⚠️ The `stroke-dasharray` probe has a **measured** false negative on the comma spelling
      (`"0px, 0px"`, TOR-644) — **inherit the known gap, do not silently widen it.**
- [ ] `[V]` **Verifier gate 2.** The mutation table in §2, run and recorded, **M9 first**.

### Phase 3 — fidelity, then hand back

- [ ] **T3.1 · Fidelity measurement, in §0.4(b) incidence order.** Render each figure through the
      new bundle in a real browser and record what the reader sees against the builder's Plotly
      original.
      🔴 **DECLARE THE POPULATION BEFORE MEASURING, AND DO NOT CLAIM YIELD FROM A SAMPLE.**
      A representative figure per capability cannot settle a row that MIXES supported and
      unsupported forms — the per-point-colour row is exactly that (`ChartView.tsx:574`: *"Only
      `bar` and `point` read these"*), so a bar representative passes while every `line` incidence in
      the same row is silently dropped. Either **(a)** render every incidence the row names and
      report a real yield, or **(b)** declare the sample explicitly, report it AS a sample, and say
      which incidences were not measured. **Do not do (b) while writing the word "yield"**
      (`CLAUDE.md` TOR-716 — an inventory says what a cause BLOCKS and cannot say what it FREES).
      **Settle, per figure, all three classes §0.4(b) names:** the three contract-level residuals
      (arbitrary stroke width, third y axis, per-point colour on `line`/`area`); the **six**
      declared-but-never-read fields; and the **annotation refusal**. **File each as its own ticket
      rather than fixing it here** — the contract ones are additive contract changes, the six are
      renderer gaps, and the annotation refusal is TOR-416's ruling. Three different owners.
- [ ] **T3.2 · Hand back to TOR-745's lane to re-author `LR/historical`. NOT THIS TICKET** —
      TOR-745's comment rules *"fix the kit, then rebuild"*, and the prose rule is TOR-782's.
- [ ] `[V]` **Verifier gate 3.** T3.1's measurement recorded, with its population declared per
      §T3.1(a)/(b); every residual filed to its owning ticket.

> 🔴 **THIS TICKET HAS NO LIVE-PAGE GATE, AND THAT IS A CORRECTION, NOT AN OMISSION.** An earlier
> draft ended with *"the page renders on `app.dev.torque-capital.com` with a previously-absent figure
> present"*. **That is unsatisfiable by TOR-750 and would have been discovered only at the gate.**
> `scripts/build_page.py:61` inlines the bundle into each artifact **at build time**, and every
> published artifact therefore carries its **own** frozen copy — the same fact §0.7 uses to price (B)
> and §3/Q4 uses to say no published page is affected either way. So **deploying this source change
> cannot alter any page that already exists.** A previously-absent figure can only appear once
> TOR-745's lane re-authors the page and a **new version is published** — which this plan's own
> spec excludes (*What we are NOT building*, item 11) and which T3.2 hands away.
> **The live check belongs to the re-author/publish ticket, after a new artifact exists.**
> **T2.B4 is this ticket's end-to-end acceptance**: a real browser, a real container width, the
> repository's own mark selectors, and a zero-mark render RED. It is the strongest evidence
> obtainable without publishing, and it is obtainable without publishing.
> ⚠️ **Do not "rescue" the gate by publishing a page from this ticket.** Publishing is a decision
> record, the artifact is immutable, and the authored-page lane is TOR-745's.

---

## 2 · The two-direction control (Verifier gate 2 in full)

A guard never seen failing has not been shown to be one.

| # | mutation | expected | why it is not vacuous |
| - | - | - | - |
| **M9** | stub the render harness so it produces an empty wrapper | **RED** (T2.B4) | 🔴 **the control on the control.** §0.8 observed, turned into a check: without it every other row measures agreement between two empty DOMs. **RUN THIS FIRST.** |
| M4 | remove one `isAnimationActive={false}` from `ChartView` | **RED** (T2.B5) | the TOR-642 class; proves the flag reached the *bundle*, not just the source |
| M6 | **restore the pre-T0.1 committed bundle bytes** (`3350a022…`) | **RED** (T0.3) | reproduces the live defect at §0.3. **Belongs to TOR-785 and is required either way** — the ruling's C1. ⚠️ **An earlier draft mutated `charts/format.ts` instead, and that control CANNOT FIRE**: T0.3 loads the *committed bundle*, so editing a source file leaves its subject byte-identical and the probe reports GREEN. Mutate the artifact the check actually reads. |
| M10 | re-point `vite.pagekit.config.ts:23` back at `entry.tsx`, **rebuild, and read the BUILT BUNDLE** | **RED** | ⚠️ **the check must be a property of the BUILT BUNDLE or of `lib.entry`, never T2.B2's grep.** T2.B2 asserts `from 'recharts'` = 0 under `frontend/src/pagekit/**`; with `entry.tsx` already emptied, re-pointing the config changes nothing that grep can see, so the control reports GREEN. **So T2.B2 needs a second half:** assert `lib.entry` resolves to `chartview-entry.tsx` **and** that the built bundle carries a `ChartView`-only marker. Two checks, because either alone is satisfied by a wrong build. |
| M11 | touch `charts/theme.ts` without rebuilding | **RED** (T0.2, or T0.3 if T0.2 keys on behaviour) | the staleness class itself, from the palette side |
| M12 | mount T2.B4's page into a zero-width container | **RED** (T2.B4) | 🔴 the C3 requirement made falsifiable: a chart present-but-invisible must not read as a pass |
| M13 | reformat `chartview-entry.tsx` (whitespace only) | **GREEN** | **must-not-fire**: no behaviour change |
| M14 | a legitimate unitless DSL dash (`"6 4"`) on a series | **GREEN** | **must-not-fire**: the animation probe must not fire on a real dash pattern |

**DELETED with the parity golden (recorded so their absence is not read as an oversight):** M1
(kit series colour), M2 (`type="monotone"` → `"linear"`), M3 (drop `tickFormatter`), M5 (delete a
fixture from the corpus glob), M7 (edit a `zIndex-layer` class number). Each policed a kit-vs-`ChartView`
comparison that no longer exists. M8 (reformat `entry.tsx`) is superseded by M13.

**Report every GREEN that was expected RED, and every RED that was expected GREEN, rather than
re-rolling it.** A green control is a finding.
🔴 **BEFORE reading any row's verdict, confirm the mutation REACHED the subject the check reads.**
Two rows of an earlier draft of this very table did not (M6 mutated a source file against a check
that loads a committed artifact; M10 mutated a config against a grep over source). Both would have
reported GREEN and been read as the guard holding. **The question is never "did I edit something",
it is "did the thing this check opens change".** And **verify each mutation MOVED the population**
before reading its result — a mutation that preserves a file's byte SIZE and lands within the same
second as the last compile can leave stale `.pyc` bytecode running (`CLAUDE.md`, *Verifying a guard by
BREAKING it*); the JS side has the equivalent hazard in vite's cache, so
`rm -rf frontend/node_modules/.vite` between arms.

---

## 3 · Open questions — for `/adjudicate` and for Shahar, NOT answered here

**Q1 · The renderer fork — RULED (B), 2026-08-24. Closed. Do not re-open.**

**Q4 · Does the kit keep `lineChart` / `barChart` / `areaChart` under (B)? — OPEN.**
Blocks T2.B1's shape, so it is T2.B0. Measured input: no already-published page is affected either
way (each carries its own inlined bundle). **Decide it; do not default it** `[ruling §5]`.

**Q2 · TOR-785 — is `loora/historical` v1 superseded?** The blast radius is **measured** (§0.3): 7
hover-only wrong numbers on one series, on an artifact whose pointer is `serve_mode='legacy'` and
which is therefore not served. **Superseding an immutable published version is a decision record and
Shahar's.** This ruling changes nothing about it, and T0.1 does not perform it.

**Q3 · Sequencing the re-authoring of `LR/historical`** against TOR-782's prose rule and Q2. Above
this ticket.

**Q5 · Scope — 18 slots or 21?** The frozen index carries 6 gradable products (18 DECISION slots);
`_REAL_PRODUCTS` carries 7 — SMP's 3 DECISION slots are live and absent from the frozen record
entirely, so they can be migrated and cannot be graded. TOR-734 records this as Shahar's.

**All of TOR-751's Q1–Q7, in particular Q3 — the fidelity bar.** Shahar's verdict was *"it does not
reproduce the original"* against *"would an IC read this instead of the original."* **(B) makes that
bar reachable; it does not declare it met**, and nothing measured anywhere says a rebuilt page passes
it `[ruling §5]`. T3.1 produces the evidence; it does not set the bar.

---

## 4 · Method

Every `file:line`, count and sha labelled `[lane, 2ac44d42]` was re-derived first-party at
`origin/develop = 2ac44d42a180ba2fcf68313d9a78eb31ba300b32` on 2026-08-24 by `git show <ref>:<path>`
— never `ls`, never the working tree, which sits 10 commits behind. Set operations were computed by
parsing the artifact, never transcribed. Figures labelled `[ruling]` or `[TOR-785]` were measured by
another seat and are cited as such; figures labelled `[relayed — 9cf4a350]` were **not** re-derived
here and carry that label wherever they appear.

Two independent measurements of (B)'s size, taken by two seats with two different wrappers, agree to
within ~100 bytes raw. The lint result carries both directions of control in the same run as its
finding. The `tp-chart` sweep carries a discriminating positive control (`tp-` = 21 in the generated
CSS).

Three claims in the case *for* (B) were checked and came back **narrowed rather than confirmed**, and
each is recorded where it is load-bearing rather than in a footnote: the staleness class survives (B)
(§0.3); *"12 of 14 gaps"* is **11 of 12**, with three contract-level residuals (§0.4(b)); and the
container-width mechanism behind the real-browser requirement is **not (B)-specific** (§0.8) — the
requirement is adopted anyway, because it is cheap and it is the only instrument that separates
*rendered* from *present but zero-width*.

---

## 5 · Independent review — the Codex round and its adjudication

**Artifact:**
`/Users/shaharshavit/Projects/torque/.codex-review/20260824-120753-tor750-plan-b-r1.md`
(`gpt-5.6-sol`, effort `high`, mode `plan`, label `tor750-plan-b-r1`, session `tor750-plan-b`).

**Confirmed BY CONTENT, not by `ls`** — `.codex-review/` in this checkout is shared: measured
immediately before this round, **946 files (293 of them `.md`)**, and **0** naming TOR-750, which is
the gate the plan previously failed. (Both denominators are stated because two seats quoted different
numbers for the same directory; neither is wrong and neither is the other.)

* `…-r1.provenance` records `prompt_sha256=9974fd29c46eb1f22ebc486670128e3029de1042c260847295688024d0077b99`,
  which is the sha256 of the prompt this lane wrote, and
  `prompt_origin=…/scratchpad/tor750-plan-b-r1-prompt.md`, which is where it wrote it.
* The `.md` (14,363 B) is a distinct artifact from the copied `.prompt.md` (9,163 B) — the shape that
  defeats a substring glob.
* `scripts/verify_artifact.sh` → **UNCHANGED**, rc 0.
* The findings cite real `file:line` into this repository and the scan notes name the files read
  (`ChartView`, its tests and fixtures, the kit entry/config/template/SKILL, `build_page.py`, the
  package scripts, CI, the chart contracts, the reference-placement guards, and both DECISION heatmap
  builders) — **not** an apology for being unable to read the repo. It independently re-derived this
  plan's own 10-commit no-touch claim.

**Verdict returned: `not sound`, 10 findings.** Every one was adjudicated against the source and
**all 10 were CONFIRMED**; each is fixed above. Two were fixed **wider than filed** — the reviewer
named 2 unread contract fields where the sweep finds **6**, and named 1 mutation-reachability defect
per row where the same class also governs how every future row is read.

| # | finding | verdict | settled by |
| - | - | - | - |
| 1 | the live gate cannot be satisfied by this ticket | **Confirmed** | `build_page.py:61` inlines at build time, so no deploy alters an existing artifact; spec item 11 excludes publishing; T3.2 hands the re-author away → gate removed, T2.B4 is the acceptance |
| 2 | format parity cannot substitute for bundle currency | **Confirmed** | T0.3 reads `format` only; the entry closure is 6 modules (`ChartView.tsx:12-49`) → two admissible fallbacks named, T0.3 barred as one |
| 3 | annotations marked closed; six fields REFUSE | **Confirmed** | `reference_placement.ts` `unhonouredAnnotationFields`; `CLAUDE.md` TOR-416 → row is now ⚠️ PARTLY |
| 4 | heatmap marked closed; `colorbar` never read | **Confirmed, and WIDER** | `spec.ts:189-190` declare it, `ChartView.tsx` mentions it **0** times; the sweep finds **6** such fields, not 2 → new §0.4(b) subsection |
| 5 | the kit's public guidance is never updated | **Confirmed** | `SKILL.md:69`, `template.html:124` teach the wide-form API; the lint passes a commented dead call → new task T2.B2b |
| 6 | wrapper selectors, and 3 unexercised animation sites | **Confirmed** | `ChartView.test.tsx:119-133` uses `.recharts-line-curve`/`.recharts-area-area`, and `:113-117` records why the wrapper count is the measured false pass → selectors fixed, all kinds covered, **animation split into its own synchronous-read lane** |
| 7 | M6 and M10 cannot reach their checks | **Confirmed, and WIDER** | M6 edited a source file against a check that loads the committed bundle; M10 edited a config against a grep over source → both re-pointed, plus a standing rule to confirm every mutation reached its subject |
| 8 | C1/C2 need node; `test-backend` has none | **Confirmed** | `ci.yml` — `setup-node`/`npm ci` appear only in `test-frontend`; the existing page-kit tests are node-free → moved, recorded as Invariant 13 |
| 9 | a representative cannot establish population yield | **Confirmed** | the per-point-colour row mixes supported and unsupported marks (`ChartView.tsx:574`) → declare the population or declare the sample, never both |
| 10 | `T4.1` does not exist; spec C6 names the wrong task | **Confirmed** | three `T4.1` references and two spec references, all stale from the phase renumbering → fixed |

**Nothing was refuted.** That is itself worth stating rather than treating as a clean bill: a round
returning ten confirmed findings on a document its author had just re-verified is evidence about the
document, not about the reviewer's generosity. **Three of the ten (1, 6, 7) were checks that would
have reported GREEN** — the reassuring direction, and the one a second reading is for.

**Self-caught while applying the fixes, outside the round:** the INVARIANTS preamble said *"three of
the predecessor's ten lose their subject"* while striking exactly one. Corrected in the spec.

**Not reviewed by this round:** the ruling itself (settled, and stated as such in the prompt), and
anything the reviewer could not execute — no build, no `npm`, no pytest, no browser. Every claim it
makes about runtime behaviour is inference from reading, and the three findings that turn on runtime
(2, 6, 8) were each re-derived here from the artifact before being accepted.
