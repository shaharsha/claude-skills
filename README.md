# claude-skills

Agent skills by [@shaharsha](https://github.com/shaharsha) - 26 production-grade [Agent Skills](https://platform.claude.com/docs/en/agents-and-tools/agent-skills) that work in Claude Code, claude.ai, Codex, Cursor, and any other harness that reads the SKILL.md format.

MIT licensed. Built day-to-day; battle-tested in real projects.

---

## Install

### Claude Code (recommended)

```bash
/plugin marketplace add shaharsha/claude-skills
/plugin install shaharsha-skills@shaharsha-skills
```

This installs all 26 skills as one plugin. Or pick a subset:

```bash
/plugin install documents-and-decks@shaharsha-skills    # gdoc-sync + gslides-sync + gsheets + presentation-generator + elevenlabs-tts + elevenlabs-stt + narrating-pptx + deck-to-video + self-presenting-decks + writing-plainly
/plugin install brand-and-visuals@shaharsha-skills      # brand-system + brand-assets + image-generation + excalidraw-diagrams
/plugin install engineering-decisions@shaharsha-skills  # tech-design-doc + pair-intelligence
/plugin install building-agents@shaharsha-skills        # prompt-engineer + writing-project-instructions + reviving-sessions
/plugin install utilities@shaharsha-skills              # namecheap-domains + office-render + viewing-videos + proton-pass + tavily-extract
/plugin install video-production@shaharsha-skills       # generating-video-clips + producing-animated-episodes
```

Or install one skill by its name:

```bash
/plugin install pair-intelligence@shaharsha-skills
```

<details>
<summary>The install line for each of the 26 skills</summary>

```bash
/plugin install gdoc-sync@shaharsha-skills
/plugin install gslides-sync@shaharsha-skills
/plugin install gsheets@shaharsha-skills
/plugin install presentation-generator@shaharsha-skills
/plugin install elevenlabs-tts@shaharsha-skills
/plugin install elevenlabs-stt@shaharsha-skills
/plugin install narrating-pptx@shaharsha-skills
/plugin install deck-to-video@shaharsha-skills
/plugin install self-presenting-decks@shaharsha-skills
/plugin install writing-plainly@shaharsha-skills
/plugin install brand-system@shaharsha-skills
/plugin install brand-assets@shaharsha-skills
/plugin install image-generation@shaharsha-skills
/plugin install prompt-engineer@shaharsha-skills
/plugin install writing-project-instructions@shaharsha-skills
/plugin install tech-design-doc@shaharsha-skills
/plugin install namecheap-domains@shaharsha-skills
/plugin install office-render@shaharsha-skills
/plugin install viewing-videos@shaharsha-skills
/plugin install proton-pass@shaharsha-skills
/plugin install excalidraw-diagrams@shaharsha-skills
/plugin install tavily-extract@shaharsha-skills
/plugin install pair-intelligence@shaharsha-skills
/plugin install reviving-sessions@shaharsha-skills
/plugin install generating-video-clips@shaharsha-skills
/plugin install producing-animated-episodes@shaharsha-skills
```

</details>

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
| [gdoc-sync](skills/gdoc-sync) | Push a local `.md` to an existing Google Doc, fixing what Google's converter breaks (`#anchor` links, cross-doc refs, 1500pt images, missing RTL), re-applying the styling each push resets, and refusing to overwrite edits made in the Doc since the last sync. |
| [gslides-sync](skills/gslides-sync) | The same shape for `.pptx` → an existing Google Slides: native `pageObjectId` links, scaled images, RTL per text shape, warnings for what the import drops, and the command that restores narration videos a push deleted. |
| [gsheets](skills/gsheets) | Sheets API v4 CLI: read as records, find rows, compare-and-set writes for shared Sheets, one-call table layout, validation, inspect and export, plus a raw `batchUpdate` with A1 ranges. Runs on a bare `python3`. |
| [presentation-generator](skills/presentation-generator) | 16:9 PDF + PPTX decks where every slide is a custom AI-rendered image. Style locks globally; composition varies per slide. |
| [elevenlabs-tts](skills/elevenlabs-tts) | Speech with ElevenLabs Eleven v4 in any language — short spoken briefings ("explain this to me as an MP3"), v4 audio-tag direction, consistent 429-safe batches, a speech-to-text check that no tag was read aloud, and forced-alignment timings for subtitles. |
| [elevenlabs-stt](skills/elevenlabs-stt) | Transcripts and subtitles with ElevenLabs Scribe v3 in any language: meetings, talks and YouTube links into timestamped, speaker-labelled `transcript.md` and clean SRT, keyterms and a clean mode that keep English terms in Latin script inside Hebrew speech, and live transcription over the Scribe v3 Live WebSocket. |
| [narrating-pptx](skills/narrating-pptx) | Per-slide ElevenLabs narration embedded in a pptx, with autoplay authored by real PowerPoint — the one method that doesn't corrupt the file — or added to a Google Slides deck as autoplaying Drive videos. |
| [deck-to-video](skills/deck-to-video) | Slides + narration → a self-playing mp4 with a progress bar, countdown, and slide counter, baked with PIL because ffmpeg's animated `drawbox` silently renders full. |
| [self-presenting-decks](skills/self-presenting-decks) | The orchestration map over the whole chain, plus the update matrix for what to rebuild when something changes. |
| [writing-plainly](skills/writing-plainly) | Messages, emails, updates, PR descriptions and tickets that people read to the end and that don't read as AI: one recipe, a shape per genre, Slack and email specifics, Hebrew rules, and a checker for the mechanical tells. |

### Brand & visuals

| Skill | What it does |
|---|---|
| [brand-system](skills/brand-system) | A production-grade brand book: 20-section `BRAND.md`, printable PDF sibling, and matched `tokens.css` (Tailwind v4) + `tokens.json` (W3C DTCG). WCAG 2.2 AA audited at authoring time. |
| [brand-assets](skills/brand-assets) | The mechanical-pixel sibling: vectorize, finalize-svg, rasterize, icon-pack, colour-audit. Bash + Python stdlib. |
| [image-generation](skills/image-generation) | Logos, icons, mockups, and product shots via OpenAI GPT Image 2.5 (Sunburst for finals, Flare for drafts) or Gemini Nano Banana — each prompted in its provider's native grammar, with native transparent PNGs. |
| [excalidraw-diagrams](skills/excalidraw-diagrams) | Architecture and flow diagrams on an Excalidraw+ canvas with real tech icons, plus the MCP quirks that silently break a diagram. |

### Engineering decisions

| Skill | What it does |
|---|---|
| [tech-design-doc](skills/tech-design-doc) | RFCs, ADRs, KEPs, and partner-mode TDRs, triaged to the right format first and audited against documented anti-patterns. |
| [pair-intelligence](skills/pair-intelligence) | Consult a second model (Codex or Gemini) to review, advise, brainstorm, research or browse, then judge every claim against the source. Replaces codex-review. |

### Building agents

| Skill | What it does |
|---|---|
| [prompt-engineer](skills/prompt-engineer) | Prompt and context engineering for the Claude / GPT / Gemini / Kimi / Grok APIs — system prompts, tool descriptions, provider differences, agent harness patterns (approvals, modes, async work, compaction), judge-prompt design. |
| [writing-project-instructions](skills/writing-project-instructions) | Author or audit a `CLAUDE.md` / `AGENTS.md`, with the falsifiability test and the loading semantics people usually get wrong. |
| [reviving-sessions](skills/reviving-sessions) | Bring back sessions the Claude desktop app cannot see — adopt CLI and headless sessions into it, fix renames, recover stranded transcripts, and read what an ended session said. |

### Utilities

| Skill | What it does |
|---|---|
| [namecheap-domains](skills/namecheap-domains) | Domain availability via Namecheap's API — one domain, batches of 50, or TLD sweeps, with premium and EAP fees surfaced. |
| [office-render](skills/office-render) | Render `.docx` / `.pptx` / `.xlsx` to PDF and page images using the real Office apps on macOS — pixel-faithful, unlike LibreOffice. |
| [viewing-videos](skills/viewing-videos) | How an agent sees a video: the fewest ffmpeg frames that answer the question, triaged on a contact sheet. |
| [proton-pass](skills/proton-pass) | Credentials and secrets from the CLI via Proton Pass, with never-print-secrets guardrails. |
| [tavily-extract](skills/tavily-extract) | Fetch the JS-rendered SPAs and 403-blocked hosts a normal fetcher can't, and flag soft 404s. |

### Video production

| Skill | What it does |
|---|---|
| [generating-video-clips](skills/generating-video-clips) | Still to short clip with Gemini Omni, takes reviewed on frame sheets, and mouths lip-synced to your own dialogue with Sync 3 on fal, one speaker per part, frame-exact. |
| [producing-animated-episodes](skills/producing-animated-episodes) | A voiced, subtitled, animated, lip-synced vertical episode from photos and a script: one episode.json, one engine, human gates at every paid step, timing driven by the real dialogue. |

## How they compose

A few of these are designed to work together:

- `presentation-generator` calls `image-generation` for every slide.
- `presentation-generator` consumes `brand-system`'s `BRAND.md` for palette / typography / motif lock when present in the directory.
- `brand-system` (the document) and `brand-assets` (the pixels) are siblings - run both for a complete brand rollout.
- `gdoc-sync`, `gslides-sync`, and `gsheets` share Google service-account setup; one SA works for all three APIs.
- `tech-design-doc` calls `gdoc-sync` at the end of the workflow to push the finished TDR to a live Google Doc for stakeholder comments.
- `elevenlabs-stt` is the speech-to-text side of `elevenlabs-tts` (whose tag-leak check transcribes with Scribe v3); `deck-to-video` burns its SRT into a video.
- `narrating-pptx` narrates decks produced by `presentation-generator` (or any pptx), generates its audio with `elevenlabs-tts`, and uses `office-render` for the real-PowerPoint validation step.
- `deck-to-video` reuses the per-slide mp3s (and `elevenlabs-tts`' forced alignment for subtitles) and `office-render`'s real-PowerPoint PDF — the pptx and the video sound and look identical.
- `self-presenting-decks` is the map over the whole chain: pptx authoring → `office-render` → `narrating-pptx` (+ `elevenlabs-tts`) → `deck-to-video`.
- `generating-video-clips` animates `image-generation`'s panels and lip-syncs them to `elevenlabs-tts` dialogue.
- `producing-animated-episodes` drives `image-generation` (cards, panels), `elevenlabs-tts` (voices, music, SFX) and `generating-video-clips` (clips, lip-sync) from one config.

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
