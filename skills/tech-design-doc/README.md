# claude-skill-tech-design-doc

A Claude Code skill for authoring **technical design review documents** — RFCs, design docs, ADRs, technical specs, architecture proposals — sized correctly for the audience and the decision being made.

This is a [Claude Code skill](https://docs.anthropic.com/claude-code). It lives at `~/.claude/skills/tech-design-doc` (typically as a symlink to this repo).

## Why this skill exists

Most "bad" design docs aren't bad at writing — they're bad at triage. A 20-page proposal for a one-line ADR-shaped decision wastes everyone's time; a 2-page summary for a system-spanning rewrite gets rejected for thinness. This skill triages format first (mini-ADR / standard-RFC / heavyweight / partner-mode), scaffolds from a research-grounded template, enforces the load-bearing sections, and audits against best-practice anti-patterns before sync.

## Install (symlink into Claude Code skills dir)

```bash
git clone https://github.com/<you>/claude-skill-tech-design-doc.git ~/Projects/claude-skill-tech-design-doc
ln -s ~/Projects/claude-skill-tech-design-doc ~/.claude/skills/tech-design-doc
```

After install, the skill is available to Claude Code. Invoke by asking for a design doc / RFC / ADR.

## Usage (manual scripts, no Claude required)

```bash
# Scaffold a new doc
~/.claude/skills/tech-design-doc/scripts/new-doc.sh \
    --template standard-rfc \
    --slug my-decision \
    --title "Migrate the chat store"

# Audit a draft
~/.claude/skills/tech-design-doc/scripts/audit-doc.py drafts/design-my-decision-v1.md

# After Accepted: append to project decision log
~/.claude/skills/tech-design-doc/scripts/append-decision-log.py drafts/design-my-decision-v1.md
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

See `SKILL.md` for full guidance and `reference/anti-patterns.md` for what these rules prevent.

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

MIT. Use freely; PRs welcome.
