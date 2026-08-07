# claude-skills

Agent skills by [@shaharsha](https://github.com/shaharsha) - 20 production-grade [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills) that work in Claude Code, claude.ai, Codex, Cursor, and any other harness that reads the SKILL.md format.

MIT licensed. Built day-to-day; battle-tested in real projects.

---

## Install

### Claude Code (recommended)

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install shaharsha-skills@shaharsha-skills
```

This installs all 20 skills as one plugin. Or pick a subset:

```bash
/plugin install documents-and-decks@shaharsha-skills    # gdoc-sync + gslides-sync + gsheets + presentation-generator + narrating-pptx + deck-to-video + self-presenting-decks
/plugin install brand-and-visuals@shaharsha-skills      # brand-system + brand-assets + image-generation + excalidraw-diagrams
/plugin install engineering-decisions@shaharsha-skills  # tech-design-doc + codex-review
/plugin install building-agents@shaharsha-skills        # prompt-engineer + writing-project-instructions + working-with-other-sessions
/plugin install utilities@shaharsha-skills              # namecheap-domains + office-render + viewing-videos + proton-pass + tavily-extract
```

### Manual (any other harness)

```bash
git clone https://github.com/shaharsha/claude-skills.git ~/shaharsha-skills
ln -s ~/shaharsha-skills/skills/<skill-name> ~/.claude/skills/<skill-name>
# repeat per skill, or symlink the whole skills/ dir
```

For Codex, Cursor, Gemini CLI, OpenClaw, etc., follow the same shape - point your harness at `skills/<name>/SKILL.md`.

---

## Skills

Each links to its own README — what it does, why it exists, install, and the gotchas it encodes.

### Documents & decks

| Skill | What it does |
|---|---|
| [gdoc-sync](skills/gdoc-sync) | Push a local `.md` to an existing Google Doc, fixing the four things Google's converter breaks: `#anchor` links, cross-doc refs, 1500pt images, and missing RTL. |
| [gslides-sync](skills/gslides-sync) | The same shape for `.pptx` → an existing Google Slides: native `pageObjectId` links, scaled images, RTL per text shape. |
| [gsheets](skills/gsheets) | Full Sheets API v4 CLI — cells, tabs, freeze/resize/merge, header styling, filters, banding, conditional formatting, plus a raw `batchUpdate` escape hatch. |
| [presentation-generator](skills/presentation-generator) | 16:9 PDF + PPTX decks where every slide is a custom AI-rendered image. Style locks globally; composition varies per slide. |
| [narrating-pptx](skills/narrating-pptx) | Per-slide ElevenLabs narration embedded in a pptx, with autoplay authored by real PowerPoint — the one method that doesn't corrupt the file. |
| [deck-to-video](skills/deck-to-video) | Slides + narration → a self-playing mp4 with a progress bar, countdown, and slide counter, baked with PIL because ffmpeg's animated `drawbox` silently renders full. |
| [self-presenting-decks](skills/self-presenting-decks) | The orchestration map over the whole chain, plus the update matrix for what to rebuild when something changes. |

### Brand & visuals

| Skill | What it does |
|---|---|
| [brand-system](skills/brand-system) | A production-grade brand book: 20-section `BRAND.md`, printable PDF sibling, and matched `tokens.css` (Tailwind v4) + `tokens.json` (W3C DTCG). WCAG 2.2 AA audited at authoring time. |
| [brand-assets](skills/brand-assets) | The mechanical-pixel sibling: vectorize, finalize-svg, rasterize, icon-pack, colour-audit. Bash + Python stdlib. |
| [image-generation](skills/image-generation) | Logos, icons, mockups, and product shots via OpenAI gpt-image-2 or Gemini Nano Banana 2 / Pro — each prompted in its provider's native grammar. |
| [excalidraw-diagrams](skills/excalidraw-diagrams) | Architecture and flow diagrams on an Excalidraw+ canvas with real tech icons, plus the MCP quirks that silently break a diagram. |

### Engineering decisions

| Skill | What it does |
|---|---|
| [tech-design-doc](skills/tech-design-doc) | RFCs, ADRs, KEPs, and partner-mode TDRs, triaged to the right format first and audited against documented anti-patterns. |
| [codex-review](skills/codex-review) | An independent read-only second opinion on a plan or diff from OpenAI Codex — then adjudicate every finding against the source. |

### Building agents

| Skill | What it does |
|---|---|
| [prompt-engineer](skills/prompt-engineer) | Prompt and context engineering for the Claude / GPT / Gemini APIs — system prompts, tool descriptions, provider differences, judge-prompt design. |
| [writing-project-instructions](skills/writing-project-instructions) | Author or audit a `CLAUDE.md` / `AGENTS.md`, with the falsifiability test and the loading semantics people usually get wrong. |
| [working-with-other-sessions](skills/working-with-other-sessions) | Read what a parallel agent session actually said — list every session, print one as a conversation, search the prose of all of them. |

### Utilities

| Skill | What it does |
|---|---|
| [namecheap-domains](skills/namecheap-domains) | Domain availability via Namecheap's API — one domain, batches of 50, or TLD sweeps, with premium and EAP fees surfaced. |
| [office-render](skills/office-render) | Render `.docx` / `.pptx` / `.xlsx` to PDF and page images using the real Office apps on macOS — pixel-faithful, unlike LibreOffice. |
| [viewing-videos](skills/viewing-videos) | How an agent sees a video: the fewest ffmpeg frames that answer the question, triaged on a contact sheet. |
| [proton-pass](skills/proton-pass) | Credentials and secrets from the CLI via Proton Pass, with never-print-secrets guardrails. |
| [tavily-extract](skills/tavily-extract) | Fetch the JS-rendered SPAs and 403-blocked hosts a normal fetcher can't, and flag soft 404s. |

## How they compose

A few of these are designed to work together:

- `presentation-generator` calls `image-generation` for every slide.
- `presentation-generator` consumes `brand-system`'s `BRAND.md` for palette / typography / motif lock when present in the directory.
- `brand-system` (the document) and `brand-assets` (the pixels) are siblings - run both for a complete brand rollout.
- `gdoc-sync`, `gslides-sync`, and `gsheets` share Google service-account setup; one SA works for all three APIs.
- `tech-design-doc` calls `gdoc-sync` at the end of the workflow to push the finished TDR to a live Google Doc for stakeholder comments.
- `narrating-pptx` narrates decks produced by `presentation-generator` (or any pptx) and uses `office-render` for the real-PowerPoint validation step.
- `deck-to-video` reuses `narrating-pptx`'s per-slide mp3s and `office-render`'s real-PowerPoint PDF — the pptx and the video sound and look identical.
- `self-presenting-decks` is the map over the whole chain: pptx authoring → `office-render` → `narrating-pptx` → `deck-to-video`.

---

## Compatibility

These are standard [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills) (SKILL.md-format). They work in any harness that reads the format:

- **Claude Code** (CLI) - full plugin marketplace support; install via `/plugin install` as above.
- **claude.ai** - upload skills via Settings -> Capabilities -> Skills.
- **Codex CLI** - point Codex at the skill folder; it reads SKILL.md natively.
- **Cursor** - drop the skill into your `~/.cursor/skills/` (or wherever your Cursor config expects).
- **Gemini CLI** - point at the skill via `gemini extensions install`.
- **OpenClaw / other harnesses** - any tool that respects SKILL.md frontmatter works.

---

## License

MIT. See [LICENSE](LICENSE).
