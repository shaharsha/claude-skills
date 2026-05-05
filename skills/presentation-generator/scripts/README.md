# `presentation-generator/scripts/` — script reference

All scripts are invoked from the deck's working directory (where `deck-plan.json` lives). They write to that directory's `slides/` and `output/` subdirectories.

## Pipeline at a glance

```
1. lock-style.py     → ./refs/style-ref-{1,2}.png
                       (Claude reads, picks one, writes path into deck-plan.json's style_ref)

2. generate-deck.py  → ./slides/slide-NN-<slug>.png  (parallel, concurrency=4)

3. qa-slides.py      → mechanical QA report
                       (Claude does visual QA by reading PNGs)

4. render-pdf.sh     → ./output/<deck-slug>-v1.pdf
   build-pptx.py     → ./output/<deck-slug>-v1.pptx
```

---

## `lock-style.py`

Generate 1-2 style reference frames from the deck plan's `style_brief` alone. No slide content yet — pure aesthetic anchors.

```bash
~/.claude/skills/presentation-generator/scripts/lock-style.py \
  --plan deck-plan.json \
  --output-dir ./refs/ \
  [--n 2] [--size 2560x1440] [--quality high]
```

Reads `deck-plan.json`'s `title`, `aesthetic`, `palette`, `motif`, and `style_brief`. Sends a synthesized style-anchor prompt to `openai-image.sh` `--n` times in parallel. Each ref is saved as `refs/style-ref-N.png`. Stdout: paths of successful refs.

After running, **read each PNG with the Read tool** and pick the strongest. Set `deck-plan.json`'s `style_ref` to its path.

---

## `generate-deck.py`

The core orchestrator. Reads the deck plan, fans out one image-generation call per slide, runs them through a thread pool with `max_workers=4`.

```bash
~/.claude/skills/presentation-generator/scripts/generate-deck.py \
  --plan deck-plan.json \
  --output-dir ./slides/ \
  [--concurrency 4] [--size 2560x1440] [--quality high] [--dry-run] [--only 03,07]
```

Behavior:
- For each slide: builds an `openai-image.sh` (or `gemini-image.sh` if `model: gemini`) command. Appends `style_brief` to the per-slide `image_prompt`. Adds `--ref <style_ref>` if set in the plan.
- Runs up to `--concurrency` jobs in parallel via `concurrent.futures.ThreadPoolExecutor`.
- Per-slide failures don't kill siblings. Failures are logged at the end with the underlying error.
- Stdout: paths of successful slides (one per line, sorted by slide id).
- Exit 0 if all slides succeeded, 1 if any failed, 2 if invocation was malformed.

Useful flags:
- `--dry-run` — print the planned schedule and shell commands without executing. Free, fast, lets you eyeball the prompts before spending tokens.
- `--only 03,07` — regenerate just the listed slide IDs. Use when QA flags specific slides.

---

## `qa-slides.py`

Mechanical sanity checks across all generated slides.

```bash
~/.claude/skills/presentation-generator/scripts/qa-slides.py \
  --plan deck-plan.json \
  --slides-dir ./slides/ \
  [--json]
```

Per-slide checks: file exists, dimensions in the right ballpark for 16:9 (within 2% tolerance), file size > 50KB, mean luminance is not pure-black or pure-white, std-dev > 5 (a flat-color slide is almost always a generation failure).

Output: human-readable report or JSON (`--json`). Exit 0 if all clean, 1 if any flagged.

This is *mechanical* QA — visual QA still requires Claude reading each PNG with the Read tool.

---

## `render-pdf.sh`

Assemble the slide PNGs into a 16:9 PDF via Chrome headless.

```bash
~/.claude/skills/presentation-generator/scripts/render-pdf.sh \
  --plan deck-plan.json \
  --slides-dir ./slides/ \
  --output ./output/<deck-slug>.pdf \
  [--keep-html]
```

Builds an intermediate HTML with one `<section>` per slide (full-bleed `<img>` in a 13.333"×7.5" frame), then runs Chrome `--headless=new --print-to-pdf`. The `--keep-html` flag preserves the intermediate HTML alongside the PDF.

Searches for Chrome in standard macOS / Linux locations. Errors out if it can't find one.

---

## `build-pptx.py`

Assemble the slide PNGs into a PPTX deck via `python-pptx`.

```bash
~/.claude/skills/presentation-generator/scripts/build-pptx.py \
  --plan deck-plan.json \
  --slides-dir ./slides/ \
  --output ./output/<deck-slug>.pptx \
  [--no-notes]
```

Each slide gets a blank layout (placeholders stripped), a full-bleed picture, and the slide's `speaker_notes` attached unless `--no-notes`. Slide dimensions are 13.333" × 7.5" (modern PowerPoint widescreen).

---

## End-to-end one-liner

For a deck plan that already has `style_ref` set:

```bash
S=~/.claude/skills/presentation-generator/scripts && \
  $S/generate-deck.py --plan deck-plan.json --output-dir ./slides/ && \
  $S/qa-slides.py --plan deck-plan.json --slides-dir ./slides/ && \
  $S/render-pdf.sh --plan deck-plan.json --slides-dir ./slides/ --output ./output/deck-v1.pdf && \
  $S/build-pptx.py --plan deck-plan.json --slides-dir ./slides/ --output ./output/deck-v1.pptx
```

In normal use the parent SKILL.md walks Claude through the phases interactively — this one-liner is for power users who already have a finalized plan.

---

## Environment

Both `generate-deck.py` and `lock-style.py` rely on `openai-image.sh`, which requires:

```bash
export OPENAI_IMAGE_API_KEY='sk-proj-...'
```

Get the key from `~/.claude/projects/-Users-shaharshavit/memory/api-keys.md` → "OpenAI (image generation)".

For slides with `model: gemini`:

```bash
export GEMINI_IMAGE_API_KEY='AQ.Ab8RN...'
```
