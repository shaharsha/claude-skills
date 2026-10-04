# episode.json reference

One file holds the whole project. `engine/config.py` loads it, fills in defaults, and validates it before any rendering or paid call; every problem is listed in one error. Relative paths resolve against the folder that holds `episode.json`, and `~` is expanded. `templates/episode.example.json` is a complete small episode.

## Top level

| Key | Type | Default | Meaning |
|---|---|---|---|
| `version` | int | 1 | schema version |
| `title` | string | - | for your own reference |
| `output` | string | `"episode"` | builds `build/<output>.mp4` and `build/<output>_whatsapp.mp4` |
| `video` | object | see below | frame rate and sizes |
| `text` | object | `{"language": "en"}` | on-screen text language and direction |
| `paths` | object | see below | where each asset kind lives |
| `fonts` | object | - | font key to `.ttf` path; styles name the keys |
| `timing` | object | see below | pads and gaps |
| `characters` | object | - | the cast, keyed by a short id |
| `speakers` | object | - | extra speakers that are not characters (a crowd, a shadow) |
| `voice` | object | see below | TTS settings for the whole cast |
| `pronounce` | list | `[]` | `[from, to]` pairs applied in order to TTS input only |
| `lines` | list | required | every spoken line |
| `groups` | object | `{}` | crowd lines: line id to the character ids who shout it |
| `prompts` | object | defaults | overrides of any generation template (below) |
| `panel_size` | string | `"1152x2048"` | panel image size |
| `panels` | object | `{}` | panel id to its characters and scene |
| `animate` | object | `{}` | image-to-video jobs |
| `music`, `sfx` | object | `{}` | cue or effect name to `{prompt, seconds}` |
| `music_cues` | list | `[]` | `[cue, from shot, to shot (inclusive), volume, offset into the cue]` |
| `styles` | object | `{}` | overlay styles, by key |
| `subtitle` | object | see below | the speaker-subtitle look |
| `collage` | object | - | the group shot (`img: "collage"`) |
| `tablet` | object | see below | the device frame for `img: "tablet:..."` |
| `lipsync` | object | `{}` | which shots, which lines to skip, face points |
| `shots` | list | required | the edit, in order |

`video`: `{"fps": 24, "size": [1080, 1920], "src_size": [1152, 2048], "clip_size": [720, 1280]}`. `src_size` is the working canvas the camera moves over; `clip_size` is the image-to-video model's output size.

`text`: `{"language": "he", "direction": null}`. `direction` null means derived: `he`, `ar`, `fa`, `ur` are right-to-left, anything else left-to-right.

`paths` defaults: `characters` = `characters/final`, `cards` = `characters`, `faces` = `faces`, `panels_final` = `panels/final`, `panels_draft` = `panels/draft`, `lines_raw` = `audio/lines_raw`, `lines` = `audio/lines`, `music` = `audio/music`, `sfx` = `audio/sfx`, `clips` = `video/omni`, `lipsync` = `video/lipsync`, `build` = `build`. `episode.py PROJECT lines` writes the generated takes to `lines_raw` and the processed ones (tempo, trim, level) to `lines`, which the edit reads; the two must differ.

`timing`: `{"pad_scale": 1.0, "gap": 0.12, "silent_scale": 1.0, "default_pre": 0.35, "default_post": 0.5, "sub_tail": 0.12}`. `pad_scale` multiplies every shot's `pre` and `post`; `silent_scale` multiplies the length of shots without lines; `sub_tail` keeps a subtitle up that long after its line ends.

`voice`: `{"model": "eleven_v4", "stability": 0.5, "similarity": null, "language_code": null, "tempo": 1.0, "level_target": -18}`. `similarity` (0-1) is sent only when set; raise it for cloned voices that drift from the original. `tempo` is applied to every line with `atempo` (pitch kept).

## characters

```json
"maya": {"display": "מאיה", "background": "hot magenta #E0218A", "color": null, "voice": "<voice id>",
         "panel_name": "Maya", "refs": ["maya-1", "maya-2"], "likeness": "...", "body": "...", "pose": "...",
         "outfit": "...", "face_adjust": null}
```
- `display`: the name shown on subtitles and cards.
- `color`: the subtitle-pill color; when null, the first `#RRGGBB` in `background` is used.
- `panel_name`: the name used inside image prompts (Latin letters work best).
- `refs`: face-crop stems in `faces/`. Leave empty for a character described only by text.
- `likeness`, `body`, `pose`, `outfit`, `background`, `face_adjust`: the card prompt fields (see image-generation, characters from photos).

`speakers`: `{"ALL": {"display": "everyone", "color": "#FFFFFF"}}`. A line's `who` must be a character or a speaker.

## lines and groups

```json
{"id": "02-1", "who": "maya", "text": "[proud, energetic] Justice!", "trim": true, "level": true}
```
- `id` is `<scene>-<n>`. Time references use it (below).
- `text` keeps the audio tags. Subtitles show it with the tags stripped (a line that is only tags gets no subtitle).
- `trim: true` cuts the clip to its aligned words after generation; `level: true` levels it to `voice.level_target`. Use both for one-word lines.

`groups`: `{"19-7": ["maya", "ido", "noa"]}` makes line 19-7 a crowd: one take per listed voice, mixed 0-160 ms apart.

## panels and animate

```json
"panels": {"p01": {"chars": ["maya", "ido"], "scene": "SCENE: ...", "text_exception": null, "hq": null}}
```
`hq` null means automatic: 2 or more characters are drafted with Sunburst `high`, otherwise Flare. `text_exception` names the only text allowed in the panel, quoted, once.

```json
"animate": {"base": "<prefix for every clip prompt>", "shots": {"S01": {"panel": "p01", "motion": "[0-3s] ..."}}}
```

## shots

```json
{"id": "S02", "img": "p02", "lines": ["02-1", "02-2", "02-3@-0.4"], "pre": 0.3, "post": 0.5, "gap": 0.12,
 "mindur": 0, "dur": null, "cam": {"in": [1.1, 0.5, 0.45]}, "fx": [["flash", 0]], "sfx": [["whoosh", 0, 0.5]],
 "overlays": [{"style": "cap", "text": "An hour earlier.", "t0": 0, "t1": "E02-1"}],
 "who": {"02-3": "ALL"}, "nosub": false, "static": false,
 "clip": "S02", "clip_off": 0.0, "clip_speed": 1.0, "clip_cam": null}
```

| Key | Meaning |
|---|---|
| `img` | a panel id, `black`, `collage`, `card:<character>`, or `tablet:<screen panel>:<background panel>` |
| `lines` | spoken in order, each `gap` after the previous; `"id@-1.1"` starts 1.1 s before the previous line ends |
| `pre`, `post` | silence before the first line and after the last (scaled by `timing.pad_scale`) |
| `mindur` | the shot lasts at least this long (cards that must stay readable) |
| `dur` | a fixed length for a shot without lines |
| `cam` | camera keyframes `[[u, zoom, cx, cy], ...]` over the shot (`u` 0..1), or `{"in": [zoom, cx, cy]}` / `{"out": [zoom0, cx0, cy0]}` |
| `fx` | `["flash", t]`, `["shake", t0, t1, px]`, `["glow", t0, t1, "#hex", "top"/"bottom"]`, `["desat", t]`, `["speed", t, null, [cx, cy]]`, `["fadeout", seconds]` |
| `sfx` | `[name, t, volume]` |
| `overlays` | `{style, text, t0, t1, color}`; `t1` null means to the end of the shot |
| `who` | override a line's speaker in this shot |
| `nosub` | no subtitles in this shot |
| `static` | ignore any clip and use the still |
| `clip`, `clip_off`, `clip_speed`, `clip_cam` | which clip file, where it starts, how much it is slowed, and the camera over the clip |

**Time references** (`t0`, `t1`, fx and sfx times): seconds from the shot start, or `S<line>[+-x]` (that line's start) or `E<line>[+-x]` (its end), e.g. `"E15-1+0.4"`. The line must be one of this shot's lines; loading checks every reference.

When `video/omni/<clip>.mp4` exists the shot uses it, and when `video/lipsync/final/<shot>.mp4` exists and was made from the shot as it is now, that wins (it is already offset, slowed and frame-exact). After a change to the clip, `clip_off`, `clip_speed` or the shot's lines it is stale: the build uses the raw clip and says so until `lipsync prep` and `lipsync run` redo it. `build --no-lipsync` ignores the lip-synced versions.

## styles

| `kind` | Fields |
|---|---|
| `text` (default) | `font`, `size`, `fill` (`#RRGGBB` or `#RRGGBBAA`), `stroke`, `stroke_fill`, `spacing` (1.15), `pad` (30), `wrap` (px), `pill` (`#RRGGBBAA` background), `pill_pad` ([34, 18]), `radius` (26), `rotate` (degrees), placement by `center` ([fx, fy] of the frame), or `x` ("center" or px) plus `y_center` or `y_top`, and `anim` (`pop`, `fade`, `slide`, `write`, `none`) |
| `band` | a character card's name band: `name_font`, `name_size` (130), `stat_font`, `stat_size` (54), `stat_fill`, `y_top`, `anim` (`slide`). The overlay `text` is `[name, stat]` and `color` is the character's color |
| `stack` | lines of different fonts stacked: `canvas` [w, h], `pos` [x, y], `anim`, and `items` (`font`, `size`, `fill`, `stroke`, `stroke_fill`, `pad`, then `y` for the first and `gap` after the previous). The overlay `text` is one string per item |
| `poll` | a chat-app poll card: `title`, `subtitle`, `options` [[label, votes]], `total`, `fill_seconds` (3.2), `y_top` (140) |

`episode.py PROJECT check` warns when an overlay's text is wider than the frame.

Every font key a used style or the subtitles name must be in `fonts` (`check` blocks otherwise).

`subtitle`: `{"font": "bold", "size": 58, "wrap": 940, "stroke": 7, "pad": 6, "name_font": "hblack", "name_size": 38, "name_pad": [24, 8], "name_radius": 20, "bottom": 1560}`.

## collage, tablet, lipsync

`collage`: `{"rows": [{"keys": ["maya", "ido"], "h": 980, "y": 900, "dx": 0}], "mirror": [], "gradient_top": [255, 150, 70], "gradient_bottom": [185, 110, 180], "card_h": 1536, "scale_clamp": [0.75, 1.25], "margin": 20}`. Rows are drawn back to front. With OpenCV installed, each card is scaled so its face matches the row's median face size, and faces line up. List a character in `mirror` when a raised hand or prop would cover a neighbor.

`tablet`: `{"w": 980, "h": 1500, "blur": 28, "dim": 0.45, "dim_color": [10, 12, 20], "radius": 60, "inset": 28, "screen_radius": 40, "lift": 40}`.

`lipsync`: `{"shots": ["S05"], "skip": [["S05", "05-3"]], "faces": {"S05|0": [400, 520]}}`. Face points are pixels in the clip's own size, on the part's middle frame.

## prompts

Every generation prompt is a template in `engine/config.py` `DEFAULT_PROMPTS`; any key in `episode.json` `prompts` replaces it. Keep the placeholders:

| Key | Placeholders |
|---|---|
| `char_style`, `char_no_text`, `char_face_refs_one`, `char_face_refs_many`, `char_card_keep`, `person_one`, `person_many`, `panel_style`, `panel_no_text_base`, `panel_footer`, `panel_final`, `panel_final_notext` | none |
| `char_face` | `{refs}`, `{likeness}`, `{style}`, `{no_text}` |
| `char_face_text` | `{likeness}`, `{style}`, `{no_text}` |
| `char_card_keep_adjusted` | `{adjust}` |
| `char_card` | `{body}`, `{pose}`, `{outfit}`, `{bg}`, `{keep}`, `{no_text}` |
| `char_final` | `{bg}` |
| `panel_ref`, `panel_bind` | `{i}`, `{name}` |
| `panel_task` | `{n}`, `{noun}` |
| `panel_no_text_except`, `panel_final_keep` | `{exception}` |
| `panel_no_text` | `{t}` |

For a different look (3D cartoon, watercolor, photoreal), override `char_style` and `panel_style`, and the anime wording elsewhere if you like. `episode.py PROJECT prompts` prints every request the project would send, without calling anything.
