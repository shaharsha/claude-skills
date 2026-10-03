"""Load and validate an episode.json; resolve every path against the project folder."""
import json, os, re

DEFAULT_VIDEO = {"fps": 24, "size": [1080, 1920], "src_size": [1152, 2048], "clip_size": [720, 1280]}
DEFAULT_TIMING = {"pad_scale": 1.0, "gap": 0.12, "silent_scale": 1.0, "default_pre": 0.35, "default_post": 0.5,
                  "sub_tail": 0.12}
DEFAULT_PATHS = {"characters": "characters/final", "cards": "characters", "faces": "faces",
                 "panels_final": "panels/final", "panels_draft": "panels/draft", "lines_raw": "audio/lines",
                 "lines": "audio/lines", "music": "audio/music", "sfx": "audio/sfx", "clips": "video/omni",
                 "lipsync": "video/lipsync", "build": "build"}
RTL_LANGS = {"he", "ar", "fa", "ur"}
NO_TEXT = ("NO TEXT: no writing of any kind in any language (Japanese and English included): no captions, labels, name tags, "
           "banners, speech bubbles, logos or watermark. A single person, seen once.")
# Every generation prompt is a template here; episode.json "prompts" overrides any key (keep the {placeholders}).
DEFAULT_PROMPTS = {
    "char_style": ("STYLE: anime cel art in a current TV look: bold clean outlines, flat shading with a single shadow tone, "
                   "saturated colors, grown-up proportions (no chibi, no idealizing). Likeness comes first."),
    "char_no_text": NO_TEXT,
    "char_face": ("GOAL: one specific real person, drawn from the chest up as a character in an animated story.\n{refs}\n"
                  "FACE: {likeness}. Keep their actual face shape, hairline, facial hair and weight; don't make them thinner, "
                  "prettier or younger.\n{style}\n{no_text}"),
    "char_face_refs_one": ("REFERENCES: the image is a close-up of the person's face. Draw that person as a character whom people "
                           "who know them would recognize at once."),
    "char_face_refs_many": ("REFERENCES: every image is a close-up of the same person's face. Draw that one person as a character "
                            "whom people who know them would recognize at once."),
    "char_face_text": "GOAL: a character in an animated story, drawn from the chest up.\nCHARACTER: {likeness}.\n{style}\n{no_text}",
    "char_card_keep": ("The face stays exactly as drawn in Image 1 (its shape, hairline, facial hair, eyes, nose, skin tone, line work "
                       "and colors)."),
    "char_card_keep_adjusted": ("Keep the person from Image 1 (hair, hairline, facial hair, eyes, nose, skin tone, line work and "
                                "colors), but {adjust}."),
    "char_card": ("Image 1 is this character's approved face. Draw the same character again, now as a waist-up figure. "
                  "BUILD: {body}. STANCE: {pose}. CLOTHES: {outfit}. BACKDROP COLOR: {bg}.\n"
                  "{keep} Only framing, pose, clothes and backdrop are new.\n"
                  "FRAMING: a waist-up view, the figure standing centered and facing the viewer, with some headroom.\n"
                  "BACKDROP: a single flat color edge to edge, with no gradient and no sky, room or scenery around the figure.\n{no_text}"),
    "char_final": ("Image 1 is the approved draft of this card. Redo it as the finished version: improve only the rendering "
                   "(crisper line work, cleaner shading, richer color). Everything else stays as it is: framing, face and "
                   "expression, hair, build, pose and hands, clothes, every prop and where it sits, and the flat {bg} backdrop. "
                   "Add nothing new: no extra objects, no writing, no watermark."),
    "panel_ref": "Image {i}: {name}'s character card (identity only).",
    "panel_bind": "{name} (the person from Image {i})",
    "panel_task": ("GOAL: a new illustration of these {n} named {noun}, each recognizable from their card (face, hair, build and "
                   "clothes), placed in the scene below. Leave the cards' flat backdrops, framing and poses behind. Only the props "
                   "the scene mentions."),
    "person_one": "person", "person_many": "people",
    "panel_style": ("STYLE: anime illustration in a current TV look: bold clean outlines, flat shading with a single shadow tone, "
                    "saturated colors, richly painted backgrounds, cinematic framing."),
    "panel_no_text_base": "no letters or numbers anywhere",
    "panel_no_text_except": " except {exception}",
    "panel_no_text": ("NO TEXT: {t}; no subtitles or captions in any language (English and Japanese included), no titles, speech "
                      "bubbles, logos or watermark. Each named person matches their card and appears once, and no one else is in "
                      "the frame unless the scene says so."),
    "panel_footer": "A vertical 9:16 frame. If the scene is inside, keep it inside.",
    "panel_final": ("Image 1 is the approved draft of this frame. Redo it as the finished version: improve only the rendering "
                    "(crisper line work, cleaner shading, deeper color, more detailed backgrounds). Everything else stays as it is: "
                    "camera angle and composition, every person with their face, expression, pose, hands and clothes, every "
                    "object and where it sits, the light and the palette. Add nothing new: no extra objects, no speech bubbles, "
                    "no watermark. "),
    "panel_final_keep": "Leave {exception} untouched and add no other text.",
    "panel_final_notext": "No writing anywhere.",
}


class ConfigError(ValueError):
    pass


def char_color(c):
    if c.get("color"):
        return c["color"]
    m = re.search(r"#[0-9A-Fa-f]{6}", c.get("background", ""))
    return m.group(0) if m else "#FFFFFF"


class Episode:
    def __init__(self, file):
        self.file = os.path.abspath(file)
        self.root = os.path.dirname(self.file)
        d = self.data = json.load(open(self.file, encoding="utf-8"))
        self.video = {**DEFAULT_VIDEO, **d.get("video", {})}
        self.timing = {**DEFAULT_TIMING, **d.get("timing", {})}
        self.paths = {**DEFAULT_PATHS, **d.get("paths", {})}
        self.prompts = {**DEFAULT_PROMPTS, **d.get("prompts", {})}
        self.fps = self.video["fps"]
        self.W, self.H = self.video["size"]
        self.SRC_W, self.SRC_H = self.video["src_size"]
        self.output = d.get("output", "episode")
        t = d.get("text", {})
        self.text_lang = t.get("language", "en")
        self.text_dir = t.get("direction") or ("rtl" if self.text_lang in RTL_LANGS else "ltr")
        self.characters = d.get("characters", {})
        self.speakers = {k: {"display": c.get("display", k), "color": char_color(c)} for k, c in self.characters.items()}
        self.speakers.update(d.get("speakers", {}))
        self.lines = {l["id"]: l for l in d.get("lines", [])}
        self.shots = d.get("shots", [])
        self.styles = d.get("styles", {})
        self.validate()

    def path(self, key, *parts):
        base = os.path.expanduser(self.paths[key])
        return os.path.join(self.root, base, *parts)

    def font(self, name):
        p = os.path.expanduser(self.data.get("fonts", {}).get(name, name))
        return p if os.path.isabs(p) else os.path.join(self.root, p)

    def line_audio(self, lid):
        return self.path("lines", f"{lid}.mp3")

    def panel(self, pid):
        f = self.path("panels_final", f"{pid}.png")
        return f if os.path.exists(f) else self.path("panels_draft", f"{pid}.png")

    def validate(self):
        errs, ids = [], [s.get("id") for s in self.shots]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            errs.append(f"duplicate shot ids: {dup}")
        for s in self.shots:
            sid = s.get("id", "?")
            if "img" not in s:
                errs.append(f"{sid}: missing img")
            if not s.get("lines") and s.get("dur") is None:
                errs.append(f"{sid}: needs lines or dur")
            lids = [x.partition("@")[0] for x in s.get("lines", [])]
            for lid in lids:
                if lid not in self.lines:
                    errs.append(f"{sid}: unknown line {lid}")
            for ov in s.get("overlays", []):
                if ov.get("style") not in self.styles:
                    errs.append(f"{sid}: unknown style {ov.get('style')!r}")
            who = {l: self.lines[l]["who"] for l in lids if l in self.lines}
            who.update(s.get("who", {}))
            for l, w in who.items():
                if w not in self.speakers:
                    errs.append(f"{sid}: line {l} speaker {w!r} is neither a character nor a speaker")
        for cue in self.data.get("music_cues", []):
            for sid in cue[1:3]:
                if sid not in ids:
                    errs.append(f"music cue {cue[0]}: unknown shot {sid}")
        if errs:
            raise ConfigError("episode.json has problems:\n  " + "\n  ".join(errs))


def load(path):
    f = os.path.join(path, "episode.json") if os.path.isdir(path) else path
    if not os.path.exists(f):
        raise ConfigError(f"no episode.json at {f}")
    return Episode(f)
