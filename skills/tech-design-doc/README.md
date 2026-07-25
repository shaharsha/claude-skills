# tech-design-doc

Author **technical design review documents** — RFCs, design docs, ADRs, technical specs, architecture proposals, partner-mode TDRs — sized correctly for the audience and the decision being made.

Part of [shaharsha/claude-skills](../..). MIT.

---

## Why this exists

The only thing a design doc optimizes for is decision quality: *can a reasonable reviewer make the right call from this doc in one meeting?*

Most "bad" design docs aren't bad at writing — they're bad at **triage**. A 20-page proposal for an ADR-shaped decision wastes everyone's time; a 2-page summary for a system-spanning rewrite gets rejected for thinness. Get the format right and 70% of the work is done. So this skill triages first (mini-ADR / standard-RFC / heavyweight / partner-mode), scaffolds from a research-grounded template, enforces the load-bearing sections, and audits against documented anti-patterns before anyone reads it.

## Install

**Claude Code**

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install engineering-decisions@shaharsha-skills
```

**Any other harness**

```bash
git clone https://github.com/shaharsha/claude-skills.git
ln -s "$PWD/claude-skills/skills/tech-design-doc" ~/.claude/skills/tech-design-doc
```

Then just ask for a design doc / RFC / ADR.

## Triage — done every time, before writing

```
Q1. Recording a decision already made, OR seeking buy-in?
    └─ recording → ADR (~1 page)

Q2. Buy-in: how many stakeholders?
    ├─ 1-3 your team           → standard RFC (4-6 pages, 60-min review)
    ├─ 4-10 cross-team         → standard RFC + formal approvers list
    └─ org-spanning / infra    → heavyweight (10-20 pages, KEP + PRR)

Q3. Audience is an external partner (different company)?
    └─ yes → partner-mode (adds glossary, ownership table, "proposing" tone)

Default if unsure: standard RFC. Need evidence to grow or shrink.
```

| Template | Pages | Meeting | When |
|---|---|---|---|
| `mini-adr.md.tmpl` | 1-2 | 30 min or async | Decision already made — recording it. Nygard format. |
| `standard-rfc.md.tmpl` | 4-6 | 60 min | Buy-in for a non-trivial design, one team. Rust-RFC skeleton. |
| `heavyweight-doc.md.tmpl` | 10-20 | multi-week | Org-spanning, infra-sensitive. KEP + Production Readiness Review. |
| `partner-doc.md.tmpl` | flexible | varies | External dev partner. Standard + glossary + ownership table. |

## Usage (the scripts run standalone — no agent required)

```bash
# Scaffold a new doc → ./drafts/design-<slug>-v1.md
scripts/new-doc.sh --template standard-rfc --slug my-decision \
    --title "Migrate the chat store"

# Audit a draft against the house rules (non-zero exit on errors)
scripts/audit-doc.py drafts/design-my-decision-v1.md

# After Accepted: append a row to DECISIONS.md
scripts/append-decision-log.py drafts/design-my-decision-v1.md
```

## What's in the box

```
.
├── SKILL.md                      # entry point: triage → workflow → house rules
├── README.md                     # this file
├── reference/
│   ├── triage.md                 # ADR vs RFC vs heavyweight vs partner-mode
│   ├── canonical-outline.md      # every section across all templates
│   ├── alternatives-considered.md
│   ├── non-goals.md              # quantification rules
│   ├── cross-cutting-checklist.md
│   ├── diagrams.md               # C4 + mermaid recipes
│   ├── partner-mode.md           # external dev partner specifics
│   ├── meeting-protocol.md       # pre-read, 2-round-trip, decision log
│   ├── anti-patterns.md          # 9 killers from the literature
│   └── examples/
│       ├── mini-adr-example.md
│       └── standard-rfc-example.md
├── templates/
│   ├── mini-adr.md.tmpl          # Nygard format, 1-2 pages
│   ├── standard-rfc.md.tmpl      # Rust-RFC skeleton, 4-6 pages
│   ├── heavyweight-doc.md.tmpl   # KEP + PRR, 10-20 pages
│   └── partner-doc.md.tmpl       # standard + glossary + decision-ownership
└── scripts/
    ├── new-doc.sh                # scaffold from template with frontmatter
    ├── audit-doc.py              # static checks against house rules
    └── append-decision-log.py    # append accepted-doc row to DECISIONS.md
```

## House rules (enforced by audit)

1. BLUF every doc — first paragraph names the decision being requested.
2. Quantify every adjective in goals.
3. Always ≥3 alternatives, scored on consistent axes.
4. Non-goals are load-bearing.
5. No happy-path-only diagrams.
6. Cross-cutting checklist runs every time.
7. Status header is mandatory.
8. Be opinionated.
9. Length matches scope (2-page → 30-min, 6-page → 60-min, >6 → split).
10. End with Next Steps, not approval.

See [SKILL.md](SKILL.md) for full guidance and [reference/anti-patterns.md](reference/anti-patterns.md) for what these rules prevent — 9 documented killers with rewrite examples.

## Gotchas

- **Alternatives are the highest-leverage section, and the most commonly faked.** Three alternatives scored on *consistent axes* — status quo + incremental + proposal at minimum. A straw-man alternative is worse than none: reviewers notice, and it costs you the room.
- **Non-goals prevent ~80% of scope-creep arguments.** They're not filler; they're the cheapest section in the doc.
- **Happy-path-only diagrams hide the actual risk.** Show retries, timeouts, and failure paths, or the review discusses the wrong thing.
- **The cross-cutting checklist runs every time** — security, privacy, observability, rollout, scalability, dependencies, failure modes, on-call. Silent omission is forbidden; "N/A, because…" is fine.
- **Past ~6 pages, comment volume goes nonlinear.** If a doc outgrows its meeting slot, split it or escalate the format — don't just make the meeting longer.
- **End with Next Steps, not approval.** Phases, owners, dates, metrics. Approval is the start of the work, not the end of it.

## When NOT to use it

- **PRD / product plan** — vision-first, customer-first. Different shape.
- **Brainstorm or sketch** — too early; free-form notes, escalate when you're ready for buy-in.
- **A single-line decision** — write a commit message; don't ADR-ify trivia.
- **Post-mortem / incident review** — separate format (timeline → root cause → corrective actions).

## Related skills

- [gdoc-sync](../gdoc-sync) — push the finished doc to a live Google Doc for stakeholder comments (step 11 of the workflow).
- [codex-review](../codex-review) — get an independent read on the plan before implementing it.
- [presentation-generator](../presentation-generator) — derive an exec-summary deck from the doc's Summary + Goals + Alternatives.

## Research foundation

The skill encodes findings from:
- [Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/) (industrialempathy.com)
- [The Pragmatic Engineer — RFC & Design Doc Examples](https://newsletter.pragmaticengineer.com/p/software-engineering-rfc-and-design)
- [designdocs.dev](https://www.designdocs.dev/) (curated library, 1000+ examples)
- [Rust RFC 2394 (async/await)](https://rust-lang.github.io/rfcs/2394-async_await.html)
- [React RFC 0068 (Hooks)](https://github.com/reactjs/rfcs/blob/main/text/0068-react-hooks.md)
- [Kubernetes KEP template](https://github.com/kubernetes/enhancements/blob/master/keps/NNNN-kep-template/README.md)
- [Ohio State — Technical Design Review Writing Guide](https://ohiostate.pressbooks.pub/feptechcomm/back-matter/appendix-a-technical-design-review-writing-guide/)
- Bhatti's "How Not to Write a Design Document" + Slatton's "Writing a good design document"
- Microsoft Engineering Playbook (async design reviews, decision logs)
- Nowland's "6-page and 2-page" empirical sizing
- Joel Parker Henderson's ADR collection (Nygard / MADR / Tyree-Akerman variants)

## License

MIT — see [LICENSE](../../LICENSE).
