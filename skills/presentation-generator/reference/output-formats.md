# Output formats — PDF and PPTX dimensions, gotchas, when to choose what

The skill emits **both** PDF and PPTX by default. The user can pass `--format pdf` or `--format pptx` to constrain.

## Dimensions

Both formats target **standard 16:9 widescreen** at 13.333" × 7.5" (PowerPoint's modern default). This is the same aspect as 1920×1080, 2560×1440, and 3840×2160 — all of which are valid output sizes for the slide PNGs.

Slide PNGs are generated at **2560×1440** by default — clean 16:9, both edges multiples of 16 (a hard requirement for gpt-image-2; `1920×1080` is invalid because 1080 is not a multiple of 16).

## PDF output

Built by `render-pdf.sh`. The script:

1. Reads the deck plan to know slide order.
2. Builds a self-contained HTML file with one `<section>` per slide, each a full-bleed `<img>` filling a 13.333"×7.5" page.
3. Calls Chrome headless via `--print-to-pdf` to render the HTML to PDF.

The CSS uses `@page { size: 13.333in 7.5in; margin: 0; }` so each slide PDF page is exactly 16:9 with zero margins. Images are set to `object-fit: cover` over a `width: 100%; height: 100%` frame, so even if a slide PNG is slightly off-aspect (rare, but happens when gpt-image-2 occasionally returns 2544×1440 instead of 2560×1440), the PDF page stays clean.

**Gotchas**:
- Chrome must be installed. macOS path: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`. The script searches several known locations.
- Chrome's `--virtual-time-budget=10000` waits up to 10s for the page to settle. If a deck has many large PNGs and the disk is slow, bump this.
- The PDF is **not selectable text** — every slide is an image. If the user needs text-searchable slides, they should use the official `anthropics/skills` `pptx` skill instead.

## PPTX output

Built by `build-pptx.py` using `python-pptx`:

1. Creates a new Presentation.
2. Sets `slide_width = Inches(13.333)`, `slide_height = Inches(7.5)`.
3. For each slide in the plan: adds a blank slide layout, strips the default placeholder shapes (title and content boxes that come for free), drops the slide PNG as a full-bleed picture at (0, 0) sized to (13.333", 7.5"), and attaches the slide's `speaker_notes` to the slide's notes.

**Gotchas**:
- `python-pptx` is required. Install with `pip install python-pptx`. The skill's SKILL.md surfaces this as a dependency.
- Some PPTX viewers (older Keynote versions, LibreOffice) auto-fit slide pictures to the slide's "content area" rather than respecting the (0,0)-to-fullsize geometry. The script forces explicit `Inches(0)` left/top and `Inches(13.333)` width to avoid this.
- The default theme's blank layout is usually slide_layouts[6]. The script tries [6] first, falls back to [5]. If the user has a custom template, they can post-process.
- Speaker notes appear in the "Notes" pane of PowerPoint/Keynote. They're plain text — formatting is not preserved.

## When the user picks PDF, PPTX, or both

Default: **both**. Reasoning:
- PDF is the universal viewing format. Slack, email, web — everyone can open it.
- PPTX is editable. The user can rearrange slides, replace one image with a regenerated version, or drop the deck into someone else's PowerPoint template.
- Both run sequentially after Phase 5 (cheap relative to image generation — under 5 seconds each).

If the user explicitly requests one:
- **PDF only** → for sharing / portfolio / final deliverable. Preserves visual fidelity exactly.
- **PPTX only** → for editing / handing off / branded template integration.

## Aspect-ratio safety areas

Some venues display 16:9 with letterboxing (4:3 projector with a 16:9 deck), some crop (older 16:10 displays show ~4% less of the height). For mission-critical decks projected at unknown venues:

- **Title overlay text** should sit within the inner 90% of the canvas — i.e., at least 5% margin from each edge.
- **Important diagram elements** (boxes that must remain visible) should also stay within the inner 90%.
- **Decorative motifs** can extend to the edges — losing a corner of the dotted background pattern is cosmetic.

When writing `image_prompt` for slides with critical text, mention the safe area: "Title overlay positioned with at least 8% margin from all four edges."

## Picking a different output size

If the user wants 4K slide images (e.g., for a giant projector or print), set `--size 3840x2160` on `generate-deck.py`. Cost roughly 2.4× per slide vs the default 2560×1440. PPTX still uses 13.333"×7.5" inches; PDF page size unchanged. Only the embedded image resolution changes.

For 1080p (smaller files, faster generation), use `--size 1280x720`. Halves the cost. Quality is still strong for screen-only viewing; not for print.

## Bonus output: HTML deck

If the user wants a web-viewable version (e.g., to embed in a doc or share as a single-file webpage), pass `--keep-html` to `render-pdf.sh`. The intermediate HTML is preserved alongside the PDF. It uses `file://` references to the slide PNGs, so to make it portable copy the HTML and the slides directory together.

## Bonus output: individual slide images

The `slides/` directory always contains the standalone PNGs after Phase 4. The user can use these directly — for social media excerpts, doc embeds, or hand-arranged layouts. They are the source of truth; PDF and PPTX are just packaging.
