Review the change described below for defects. This is a pre-merge review of the
author's own repository, requested by the author.

<scope>
Branch `me/smp-decision-pages`, worktree
`/Users/shaharshavit/Projects/torque/.claude/worktrees/smp-decision`.

Get the diff with:  git diff origin/develop...HEAD

Develop merges are in that range and their content is NOT under review. THE CHANGE
UNDER REVIEW IS EVERYTHING ELSE IN THAT DIFF — this round is scoped to the WHOLE
change, not to a commit list, deliberately (see "what the earlier rounds missed").

Two authored DECISION pages for a real client, plus the as-of mechanism they
depend on:

    authored_pages/smp_forecast/**     the whole directory, README.md INCLUDED
    authored_pages/smp_simulator/**    the whole directory, README.md INCLUDED
    authored_pages/_recipe/as_of.py    the mechanism
    authored_pages/_recipe/build_lib.sh
    scripts/build_page.py
    api/services/pages.py              the marker constant
    api/services/smp/forecast.py
    api/services/smp/loan_simulator.py
    api/services/tbr/historical_analysis.py
    scripts/measure/tor1297_sweep.py
    tests/test_as_of_projection_marker.py
    frontend/src/pagekit/authored_recompute_echo.test.ts
    tests/structure/test_no_undeclared_enumerated_markup_sink.py
    tests/test_page_kit_chrome_parity.py
</scope>

<what-the-earlier-rounds-claimed-to-cover>
🔴 READ THIS FIRST. Three earlier Codex rounds ran on this branch. An adjudicator
measured that ALL THREE prompts scoped themselves to a commit list that OMITTED
`3be0d813` — the commit that adds the ENTIRE `authored_pages/smp_forecast/`
directory (a 1,228-line generated `body.html`, `charts.js`, `recipe.py`,
`parity_spec.py`, a 183-line README) and the six `(TOR-1005)` prose edits under
`api/services/smp/**`. Two-direction controls confirmed the gap: `3be0d813`
scores 0 hits across all three prompts where a sibling commit scores 1/1/1, and
`smp_forecast` / `TOR-1005` / `body.html` score 0 in the round OUTPUTS where
`as_of` scores 4/4/2.

So: the as-of MACHINERY was reviewed thoroughly, three times. THE PAGES
THEMSELVES HAVE NEVER BEEN ADVERSARIALLY READ BY ANYTHING THAT DID NOT WRITE
THEM. The earlier rounds' findings — which were good — are therefore NOT
evidence about the pages, and reproducing them is not useful here.

Already found and fixed by those rounds; do not re-report unless the fix is
wrong:
  · the renderer door checked the LONGEST marked trace while the resolver
    checked every one (fixed by listing all of them; the compression is gone,
    not patched)
  · `projected_traces` carries a diagnostic `label` that enters no predicate
  · `build_page.py` derives `projected` from the recorded VERDICT, not the
    sentence text
  · the sweep tool's dead-probe guards (all-zero and all-error runs)

Also known, filed, and explicitly OUT OF SCOPE: TOR-1309 — the per-trace bound
catches a mis-MARKED trace but cannot catch an UNSEEN one (an unmarked actual
whose `x` is epoch-ms contributes no period and the page can collapse to
`all-projection`). It is filed; do not re-file it. `as_of.py::_is_projection`
carries a pointer at it.
</what-the-earlier-rounds-claimed-to-cover>

<where-to-look-hardest>
Because the pages are the unreviewed half, weight the read that way.

1. `authored_pages/smp_simulator/charts.js` — hand-authored, ~690 lines. It sets
   each control's domain and value onto markup `scripts/gen_page_body.py`
   emitted; it repaints KPIs, four figures, two tables, eight text bodies and an
   editable grid on `torque:computed`; and it carries `mdRenderHTML`, a JS
   transcription of `authored_pages/_recipe/md.py`. Specific questions:
     · does `rowsFromFigure` reproduce `pivot.py`'s `_key` and spine EXACTLY,
       including when a trace is absent at the first x value?
     · `k(rows, i)` addresses a series by POSITION in `Object.keys(rows[0])`.
       Is that safe on every input either caller can produce?
     · the repaint writes `innerHTML` for the two tables and the eight bodies.
       Can any payload string reach the DOM as markup?
     · the boot loop sets `min`/`max`/`step` BEFORE `value`. Is that true on
       every branch, including the grid and the select?
     · are there surfaces the builder moves that this handler does NOT repaint,
       leaving the previous scenario on screen beside recomputed figures?

2. `authored_pages/smp_forecast/**` — the same directory, never read. Its README
   makes claims about the page (counts, gate results, the as-of sentence, a
   live-browser check). Do those claims match the tracked files beside them?

3. Both READMEs' difference lists. Each is supposed to name EVERY reader-visible
   difference from the builder-served page. Is anything the code does absent
   from its list — especially anything that would read as an IMPROVEMENT rather
   than a loss? The project rule is that faithfulness beats improvement and an
   undeclared improvement is a defect.

4. `frontend/src/pagekit/authored_recompute_echo.test.ts` — the new whole-grammar
   markdown arm and the new `SMPSIM` fixture. Is the fixture a real
   reconstruction of the page's behaviour, or does it only exercise paths that
   happen to pass? Is `divergentAtDefaults` correct against the SPA's own `fmt`?

5. `authored_pages/_recipe/as_of.py` — only the parts the earlier rounds did not
   settle. In particular whether the census's `marks` record and the two doors
   (resolver and renderer) can still disagree on any input.
</where-to-look-hardest>

Report each finding with: severity, the file and line, the input that reaches it,
and what a reader of the published page would see. Say explicitly when a
suspicion is unmeasured rather than stating it as a defect.

<round-5-note>
THIS IS ROUND 5, ON THE HEAD THAT CONTAINS ROUND 4'S FIXES. Round 4 ran on
`50ae7868` and found five defects in the two page directories; every one is
either fixed or explicitly refuted in this head. A round's verdict describes the
bytes it read, and those are not these bytes -- which is why this round exists
rather than the earlier sidecar being reused.

What round 4 found and what was done, so you audit the FIXES rather than
rediscover the defects:

  1 (high) SMP/forecast `mk()` dropped `fill_to`, so six `tonexty` bands filled
    to zero. FIXED: `fill_to` is forwarded and declared `'previous'` on exactly
    the six series `compile_figure` names. Audit: are those the right six? Does
    any OTHER field that allowlist drops matter the same way?
  2 (high) SMP/simulator omitted the committed-facility and break-even
    reference lines. FIXED: carried from the payload via a new `recipe.carry`
    `refs` alias and a `refsOf` mapper, at boot and on recompute. Audit: can
    `refsOf` mis-read any shape this builder emits? Is the shape-to-annotation
    pairing right? Does the new `CARRIED` entry weaken any parity half?
  3 (medium) a partial or empty recompute left the previous scenario on screen.
    FIXED: fails closed behind a `SCENARIO_KEEP` allowlist plus a symmetric
    restore. Audit: is anything scenario-dependent left OUT of the hide set or
    wrongly IN the keep set? Can the restore half strand a box hidden, or
    un-hide something that should stay hidden?
  4 (medium) internal repository paths in reader prose. REFUTED as an authored
    defect: the strings are the BUILDER's own, so reproducing them is faithful.
    Audit that refutation.
  5 (low) the recompute fixture named an impossible select value. FIXED to the
    descriptor's own option set.

Concentrate on the FIXES and on what they newly touch: `recipe.carry`,
`parity_spec.CARRIED`, `refsOf` / `refsFor` / `refsFromFigure`, the empty-state
branch and its restore, the `echo` text-node write, and both READMEs' accounts
of all of it.
</round-5-note>

<round-6-note>
THIS IS ROUND 6, ON THE HEAD THAT CONTAINS ROUND 5'S TWO FIXES, plus a develop
merge whose content is NOT under review.

Round 5 (on `d9645863`) returned "sound with reservations" with one medium and
one low, both now fixed:

  1 (medium) the empty-response guard keyed on `sim-mechanics` alone, so a
    PARTIAL response read as complete and the restore half unhid every scenario
    box — leaving omitted groups showing the previous scenario. FIXED:
    visibility is reconciled PER COMPONENT against the response's own node set
    (`el.hidden = !nodeById(payload, id)`), with `SCENARIO_KEEP` still governing
    what is exempt. Audit: can that predicate hide something that must stay, or
    keep something stale? Is the group-container case right?
  2 (low) SMP/forecast's README named a stale build base and byte count. FIXED
    by re-reading both from the artifact. Audit the new values against
    `build_base.txt` and `build/out.html`.

Concentrate on those two fixes and anything they touch. Everything else in the
diff has had an adversarial read on an earlier head; say so rather than
re-reporting it, unless a fix since then broke it.
</round-6-note>
