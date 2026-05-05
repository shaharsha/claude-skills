#!/usr/bin/env python3
"""Internal: substitute {{VAR}} placeholders in a template.

Reads BS_SRC + BS_DEST + BS_* env vars. Called by new-brand-book.sh.
Not intended for direct invocation.
"""
from __future__ import annotations

import os
import sys


def env(key: str, default: str = "") -> str:
    return os.environ.get(f"BS_{key}", default)


def main() -> int:
    src = os.environ["BS_SRC"]
    dest = os.environ["BS_DEST"]

    with open(src, encoding="utf-8") as f:
        content = f.read()

    locale = env("LOCALE", "en")
    product = env("PRODUCT")
    signature_primitive = env("SIGNATURE_PRIMITIVE", "accent dot")

    # RTL-aware values depend on the locale
    is_rtl = any(part in ("he", "ar") for part in locale.split(","))

    if "he" in locale:
        script_support = "Hebrew and Latin"
    elif "ar" in locale:
        script_support = "Arabic and Latin"
    else:
        script_support = "Latin"

    if is_rtl:
        rtl_type_moves = (
            "- **Looser line-height** — heavier descenders need air:\n"
            "  ```css\n"
            f'  html[lang="{locale.split(",")[0]}"] body {{ line-height: 1.8; }}\n'
            "  ```\n"
            "- **No letter-spacing** — RTL scripts lose legibility when letter-spaced.\n"
            "- **Numbers stay LTR** inside RTL prose. Wrap in `<bdi>` where misparse risk exists.\n"
            "- **Prefer words over icons** in RTL UI. Users decode clear labels faster.\n"
            "- **No italics** — Hebrew/Arabic have no italic tradition."
        )
        rtl_voice_notes = (
            "- Second-person direct (`את`/`أنت`). Formal third-person reads cold.\n"
            "- Numerals always as digits: `3 דקות` / `3 دقائق`. Not spelled out.\n"
            "- Avoid loan words from English where a native word exists."
        )
    else:
        rtl_type_moves = "N/A (LTR only)"
        rtl_voice_notes = "N/A (LTR only)"

    # Mark glyph — first letter of product, lowercase
    mark_glyph = product.lower()[:1] if product else "a"

    replacements: dict[str, str] = {
        "{{PRODUCT}}":             product,
        "{{PRODUCT_LOWER}}":       env("PRODUCT_LOWER"),
        "{{POSITIONING}}":         env("POSITIONING"),
        "{{PALETTE_BG}}":          env("PALETTE_BG"),
        "{{PALETTE_FG}}":          env("PALETTE_FG"),
        "{{PALETTE_ACCENT}}":      env("PALETTE_ACCENT"),
        "{{PALETTE_BG_50}}":       env("PALETTE_BG_50"),
        "{{PALETTE_BG_200}}":      env("PALETTE_BG_200"),
        "{{PALETTE_BG_300}}":      env("PALETTE_BG_300"),
        "{{PALETTE_BG_500}}":      env("PALETTE_BG_500"),
        "{{PALETTE_FG_300}}":      env("PALETTE_FG_300"),
        "{{PALETTE_FG_500}}":      env("PALETTE_FG_500"),
        "{{PALETTE_FG_700}}":      env("PALETTE_FG_700"),
        "{{SEMANTIC_SUCCESS}}":    env("SEMANTIC_SUCCESS"),
        "{{SEMANTIC_WARNING}}":    env("SEMANTIC_WARNING"),
        "{{SEMANTIC_DANGER}}":     env("SEMANTIC_DANGER"),
        "{{SEMANTIC_INFO}}":       env("SEMANTIC_INFO"),
        "{{SIGNATURE_PRIMITIVE}}": signature_primitive,
        "{{SIGNATURE_PRIMITIVE_CLASS}}": env("SIGNATURE_PRIMITIVE_CLASS"),
        "{{PRIMARY_FONT}}":        env("PRIMARY_FONT"),
        "{{PRIMARY_FONT_URL}}":    env("PRIMARY_FONT_URL"),
        "{{LOCALE}}":              locale.split(",")[0],
        "{{YEAR}}":                env("YEAR"),
        "{{DATE}}":                env("DATE"),
        "{{MONTH_YEAR}}":          env("MONTH_YEAR"),
        "{{SCRIPT_SUPPORT}}":      script_support,
        "{{RTL_TYPE_MOVES}}":      rtl_type_moves,
        "{{RTL_VOICE_NOTES}}":     rtl_voice_notes,
        "{{MARK_GLYPH}}":          mark_glyph,

        # Micro-copy defaults
        "{{CTA_OPENING}}":         "Give me one",
        "{{CTA_EXAMPLES}}":        '"Send", "Start", "Show me how"',

        # Signature primitive oneliners
        "{{SIGNATURE_PRIMITIVE_ONELINER}}": (
            f"The visual brand does one thing: it carries a single "
            f"{signature_primitive} across every surface."
        ),
        "{{SIGNATURE_PRIMITIVE_MEANING}}":  (
            f"the brand is here"
        ),

        # Mark section seed (author-editable)
        "{{MARK_ONE_LINER}}":   "One character as the product's face.",
        "{{MARK_DESCRIPTION}}": "{{TODO: describe the mark in one sentence}}",
        "{{N_READINGS}}":       "three",
        "{{MARK_READING_1_TITLE}}": "{{TODO: first reading}}",
        "{{MARK_READING_1_DESC}}":  "{{TODO}}",
        "{{MARK_READING_2_TITLE}}": "{{TODO: second reading}}",
        "{{MARK_READING_2_DESC}}":  "{{TODO}}",
        "{{MARK_READING_3_TITLE}}": "{{TODO: third reading}}",
        "{{MARK_READING_3_DESC}}":  "{{TODO}}",
        "{{CONSTRUCTION_NOTE_1}}":  "{{TODO: stroke weight, asymmetry, etc.}}",
        "{{CONSTRUCTION_NOTE_2}}":  "{{TODO}}",
        "{{CONSTRUCTION_NOTE_3}}":  "{{TODO}}",

        # Primitive use-sites (seed values — author replaces)
        "{{PRIMITIVE_IN_MARK}}":    "Static in favicons; pulses once on landing hero first paint.",
        "{{PRIMITIVE_IN_LOADING}}": "Replaces spinners on agent-action buttons.",
        "{{PRIMITIVE_IN_NAV}}":     "Sits next to the active nav label.",
        "{{PRIMITIVE_IN_BULLETS}}": "Editorial <ul> bullets become 4px accent dots.",
        "{{PRIMITIVE_IN_FOCUS}}":   "Focus ring collapses to an 8px dot on round elements.",
        "{{PRIMITIVE_IN_CTA}}":     "The period after a standalone CTA verb.",
        "{{PRIMITIVE_IN_STATUS}}":  "6px dot in the nav signals online state.",
        "{{PRIMITIVE_IN_UNSAVED}}": "Accent dot next to the doc title.",
        "{{NEVER_APPEARS_1}}":      "Destructive actions (those use danger colour).",
        "{{NEVER_APPEARS_2}}":      "Decoration (only semantic use).",
        "{{NEVER_APPEARS_3}}":      "Multiple per screen-fold, except as semantic repetition.",

        # Signature moves and principles — author fills in from interview
        "{{SIGNATURE_MOVE_1}}":   "{{TODO: signature move #1 from interview}}",
        "{{SIGNATURE_MOVE_2}}":   "{{TODO: signature move #2}}",
        "{{SIGNATURE_MOVE_3}}":   "{{TODO: signature move #3}}",
        "{{SIGNATURE_MOVE_4}}":   "{{TODO: signature move #4}}",
        "{{SIGNATURE_MOVE_5}}":   "{{TODO: signature move #5}}",
        "{{BROKEN_BEST_PRACTICE}}": "{{TODO: the rule this brand deliberately breaks — paste from interview section 6}}",
        "{{PRINCIPLE_1}}":        "{{TODO: falsifiable principle from interview section 3}}",
        "{{PRINCIPLE_2}}":        "{{TODO: falsifiable principle #2}}",
        "{{PRINCIPLE_3}}":        "{{TODO: falsifiable principle #3}}",

        # Essence
        "{{WHAT_WE_ARE}}":     "{{TODO: one paragraph on what the product is}}",
        "{{WHAT_WE_ARE_NOT}}": "{{TODO: one paragraph on what the product is NOT}}",
        "{{TONE_ONELINER}}":   "Warm but direct. Present tense. Concrete outcomes > capabilities.",

        # Colour, typography, surfaces — author fills
        "{{COLOUR_STORY}}": (
            "{{TODO: where the palette comes from. An inspiration, a place, "
            "a photograph. The colour story is what keeps the palette from "
            "feeling arbitrary.}}"
        ),
        "{{TYPEFACE_RATIONALE}}": (
            "{{TODO: why this typeface for this brand. Script support? "
            "Editorial voice? Machine/brand fit?}}"
        ),
        "{{SURFACES_INTRO}}": (
            "{{TODO: describe the material system — typically one default "
            "material for content and one floating material for chrome.}}"
        ),
        "{{DEFAULT_MATERIAL_DESCRIPTION}}": (
            "{{TODO: the default material for content. Flat surfaces with "
            "hairlines and a subtle grain overlay (\"Paper\") is a strong "
            "starting point.}}"
        ),
        "{{FLOATING_MATERIAL_DESCRIPTION}}": (
            "{{TODO: the floating material for nav, modals, tooltips. "
            "Consider Apple Liquid Glass tuned for the palette.}}"
        ),
        "{{HERO_BG_DESCRIPTION}}": (
            "{{TODO: the landing hero background. Exactly one treatment — "
            "never repeated on interior pages.}}"
        ),

        # Imagery
        "{{PHOTOGRAPHY_RULES}}":  "{{TODO: natural vs studio, subject focus, cultural context. Never AI humans in production.}}",
        "{{ILLUSTRATION_RULES}}": "{{TODO: style (flat? geometric? two-colour?), when to use, subject matter rules}}",

        # Voice
        "{{VOICE_SAMPLE}}": "{{TODO: paste the 150-word voice sample from signature-interview.md here, verbatim}}",
        "{{VOICE_RULE_1}}": "{{TODO: voice rule #1 (e.g. first-person direct, present tense, never hype)}}",
        "{{VOICE_RULE_2}}": "{{TODO}}",
        "{{VOICE_RULE_3}}": "{{TODO}}",

        # Accessibility
        "{{CONTRAST_MATRIX}}": "{{TODO: paste the output of scripts/audit-contrast.py here}}",

        # Reference set
        "{{REFERENCE_BRANDS}}":      "{{TODO: 5–8 brands you admire, each with a one-line reason}}",
        "{{ANTI_REFERENCE_BRANDS}}": "{{TODO: 3–5 brands this must never look like}}",

        # Anti-patterns
        "{{ANTI_PATTERNS}}": "{{TODO: list specific don't-do-this items}}",
        "{{REAL_DONT_1}}":   "{{TODO: real don't from a past mistake (from interview section 4)}}",
        "{{REAL_DONT_2}}":   "{{TODO: real don't #2}}",
        "{{REAL_DONT_3}}":   "{{TODO: real don't #3}}",

        # Migration
        "{{MIGRATION_STEP_1}}": "❌ Tokens — migrate old palette to new.",
        "{{MIGRATION_STEP_2}}": "❌ Favicon + derived sizes — regenerate via brand-assets skill.",
        "{{MIGRATION_STEP_3}}": "❌ Hero — replace with on-brand treatment.",
        "{{MIGRATION_STEP_4}}": "❌ Copy sweep — align with §13 voice rules.",

        # Components
        "{{COMPONENT_DETAILS}}": (
            "{{TODO: for each component — Inputs, Cards, Badges, Nav, Alerts, "
            "Dialogs, Menus, Prose — document the four states: default, "
            "loading, empty, error.}}"
        ),
    }

    for key, value in replacements.items():
        content = content.replace(key, value)

    with open(dest, "w", encoding="utf-8") as f:
        f.write(content)

    return 0


if __name__ == "__main__":
    sys.exit(main())
