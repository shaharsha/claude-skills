#!/usr/bin/env python3
"""Run every phase of an animated episode from one episode.json.

  python3 episode.py PROJECT check                         config + assets + keys + sibling skills
  python3 episode.py PROJECT chars face [keys]             anime faces from face crops (2 drafts each)   [paid]
  python3 episode.py PROJECT chars card key=face.png[:n]   costume card from the chosen face             [paid]
  python3 episode.py PROJECT chars final keys              promote approved cards (Sunburst max)         [paid]
  python3 episode.py PROJECT panels draft [ids] [--flare|--hq]   panel drafts                            [paid]
  python3 episode.py PROJECT panels final ids              promote approved panels                       [paid]
  python3 episode.py PROJECT lines [ids]                   dialogue (+ crowd mix, tempo, trim, level)    [paid]
  python3 episode.py PROJECT sound [names]                 music cues and SFX                            [paid]
  python3 episode.py PROJECT animate [shots] [--takes N]   clips from final panels                       [paid]
  python3 episode.py PROJECT animate pick SHOT K           install take K as the shot's clip
  python3 episode.py PROJECT lipsync plan|prep|run|join [shots]   (run is paid)
  python3 episode.py PROJECT build [--only S05,S06] [--force] [--nomusic] [--no-lipsync] [--out DIR] [--workers 6]
  python3 episode.py PROJECT sheet [shots]                 review frames of rendered segments
  python3 episode.py PROJECT deliver                       chat-app friendly encode of the build
  python3 episode.py PROJECT prompts                       every generation request as JSON (no API calls)
  python3 episode.py DIR demo                              write a synthetic demo project (no API calls)
"""
import argparse, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import audio, config, generate, lipsync, render, timeline  # noqa: E402
import textlayers as TL  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

KEYS = ["OPENAI_IMAGE_API_KEY", "ELEVENLABS_API_KEY", "GEMINI_API_KEY", "FAL_KEY"]
SIBLINGS = [("image-generation", "openai-image.sh"), ("elevenlabs-tts", "generate_tts.py"),
            ("elevenlabs-tts", "generate_music_and_sfx.py"), ("generating-video-clips", "omni_generate.py"),
            ("generating-video-clips", "lipsync_fal.py"), ("generating-video-clips", "lipsync_parts.py")]


def check(ep):
    TL.require_raqm()
    blockers, notes = [], []
    for k in ep.data.get("fonts", {}):
        if not os.path.exists(ep.font(k)):
            blockers.append(f"font '{k}' missing: {ep.font(k)}")
    for lid in ep.lines:
        if not os.path.exists(ep.line_audio(lid)):
            blockers.append(f"line audio missing: {ep.line_audio(lid)} (episode.py lines)")
    for s in ep.shots:
        img = s["img"]
        need = []
        if img.startswith("card:"):
            need = [ep.path("characters", img[5:] + ".png")]
        elif img.startswith("tablet:"):
            need = [ep.panel(p) for p in img.split(":")[1:]]
        elif img == "collage":
            need = [ep.path("characters", f"{k}.png") for r in ep.data["collage"]["rows"] for k in r["keys"]]
        elif img != "black":
            need = [ep.panel(img)]
        blockers += [f"{s['id']}: image missing {p}" for p in need if not os.path.exists(p)]
        clip = ep.path("clips", f"{s.get('clip', s['id'])}.mp4")
        if img not in ("black", "collage") and not img.startswith("card:") and not os.path.exists(clip):
            notes.append(f"{s['id']}: no clip, the still panel is used")
        for name, *_ in s.get("sfx", []):
            if not os.path.exists(ep.path("sfx", f"{name}.mp3")):
                blockers.append(f"{s['id']}: sfx missing {name}.mp3 (episode.py sound)")
    for cue in ep.data.get("music_cues", []):
        if not os.path.exists(ep.path("music", f"{cue[0]}.mp3")):
            blockers.append(f"music cue missing: {cue[0]}.mp3 (episode.py sound)")
    used = {ov.get("style") for s in ep.shots for ov in s.get("overlays", [])}
    S = ep.data.get("subtitle", {})
    need = {S.get("font", "bold"): "subtitles", S.get("name_font", "hblack"): "subtitle names"} if ep.lines else {}
    for name in used:
        st = ep.styles.get(name, {})
        kind = st.get("kind", "text")
        if kind == "text":
            need.setdefault(st.get("font", ""), f"style {name}")
        elif kind == "band":
            need.setdefault(st.get("name_font", "black"), f"style {name}"); need.setdefault(st.get("stat_font", "bold"), f"style {name}")
        elif kind == "stack":
            for it in st.get("items", []):
                need.setdefault(it.get("font", ""), f"style {name}")
        elif kind == "poll":
            need.setdefault(st.get("title_font", "hblack"), f"style {name}"); need.setdefault(st.get("option_font", "bold"), f"style {name}")
    for key, user in need.items():
        if key and not os.path.exists(ep.font(key)):
            blockers.append(f"font '{key}' (used by {user}) is not in fonts, or its file is missing")
    for skill, script in SIBLINGS:
        if not os.path.exists(os.path.join(generate.SKILLS, skill, "scripts", script)):
            blockers.append(f"sibling skill file missing: {skill}/scripts/{script}")
    for s in ep.shots:  # overlay text wider than the frame is clipped at both edges
        for ov in s.get("overlays", []):
            st = ep.styles.get(ov.get("style"), {})
            kind = st.get("kind", "text")
            if kind not in ("text", "stack") or not os.path.exists(ep.font(st.get("font", "bold") if kind == "text" else "bold")):
                continue
            try:
                if kind == "text":
                    widths = [TL.render_style(ep, st, ov.get("text"), ov.get("color"))[0].width]
                else:
                    widths = [TL.text_layer([t], TL.font(ep.font(it["font"]), it["size"]), stroke=it.get("stroke", 0),
                                            pad=it.get("pad", 0)).width for it, t in zip(st["items"], ov.get("text") or [])]
            except Exception as e:
                notes.append(f"{s['id']}: overlay '{ov.get('style')}' could not be measured ({e})")
                continue
            if max(widths) > ep.W:
                notes.append(f"{s['id']}: overlay '{ov.get('style')}' is {max(widths)} px, wider than the frame ({ep.W} px): "
                             "lower its size or add 'wrap'")
    print("keys:", ", ".join(f"{k} {'set' if os.environ.get(k) else 'not set'}" for k in KEYS))
    print("ffmpeg filter scripts:", " ".join(audio.filter_script_args("<file>")))
    for n in notes:
        print(("  WARNING: " if "wider than the frame" in n else "  note: ") + n)
    for b in blockers:
        print("  BLOCKER:", b)
    print(f"{len(blockers)} blocker(s) for build")
    return 1 if blockers else 0


def build(ep, a):
    out_dir = os.path.join(ep.root, a.out) if a.out else ep.path("build")
    os.makedirs(out_dir, exist_ok=True)
    shots, total = timeline.build_timeline(ep)
    timeline.write_timeline(shots, os.path.join(out_dir, "timeline.json"))
    print(f"{len(shots)} shots, total {total:.1f}s ({int(total // 60)}:{total % 60:04.1f})")
    only = set(a.only.split(",")) if a.only else None
    render.render_all(ep, shots, out_dir, only, a.force, not a.no_lipsync, a.workers)
    if only:
        return 0
    video = render.concat(shots, out_dir)
    wav = audio.mix(ep, shots, total, out_dir, a.nomusic)
    final = os.path.join(out_dir, f"{ep.output}{'_nomusic' if a.nomusic else ''}.mp4")
    audio.mux(video, wav, final)
    v, au = audio.check_durations(final, total, ep.fps)
    print(f"wrote {final}  video {v:.2f}s  audio {au:.2f}s")
    return 0


def sheet(ep, ids):
    shots, _ = timeline.build_timeline(ep)
    seg = ep.path("build", "seg")
    rows = [s for s in shots if (not ids or s["id"] in ids) and os.path.exists(os.path.join(seg, f"{s['id']}.mp4"))]
    out_dir = ep.path("build", "review")
    os.makedirs(out_dir, exist_ok=True)
    W, H = 216, 384
    for n in range(0, len(rows), 6):
        im = Image.new("RGB", (3 * (W + 6) + 120, len(rows[n:n + 6]) * (H + 6)), "white")
        d = ImageDraw.Draw(im)
        for r, s in enumerate(rows[n:n + 6]):
            d.text((6, r * (H + 6) + 8), f"{s['id']}\n{s['start']:.1f}s\n+{s['dur']:.1f}s", fill="black")
            for c, frac in enumerate((.15, .5, .85)):
                png = os.path.join(out_dir, "_f.png")
                subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{s['dur'] * frac:.3f}", "-i",
                                os.path.join(seg, f"{s['id']}.mp4"), "-frames:v", "1", "-vf", f"scale={W}:{H}", png], check=True)
                im.paste(Image.open(png).convert("RGB"), (120 + c * (W + 6), r * (H + 6)))
        out = os.path.join(out_dir, f"shots_{n // 6}.jpg")
        im.save(out, quality=88)
        print("  ", out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project"); ap.add_argument("command"); ap.add_argument("rest", nargs="*")
    ap.add_argument("--only"); ap.add_argument("--force", action="store_true"); ap.add_argument("--nomusic", action="store_true")
    ap.add_argument("--no-lipsync", action="store_true"); ap.add_argument("--out"); ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--flare", action="store_true"); ap.add_argument("--hq", action="store_true")
    ap.add_argument("--takes", type=int, default=1)
    a = ap.parse_args(argv)
    if a.command == "demo":
        root = __import__("demo").write_demo(a.project)
        print(f"demo project: {root}\nnext: python3 {__file__} {root} check && python3 {__file__} {root} build")
        return 0
    try:
        ep = config.load(a.project)
    except config.ConfigError as e:
        print(e)
        return 1
    TL.configure(ep)
    cmd, rest = a.command, a.rest
    if cmd == "check":
        return check(ep)
    if cmd == "build":
        return build(ep, a)
    if cmd == "sheet":
        return sheet(ep, set(rest)) or 0
    if cmd == "prompts":
        print(json.dumps(generate.prompts_dump(ep), ensure_ascii=False, indent=1))
        return 0
    if cmd == "deliver":
        src = ep.path("build", f"{ep.output}.mp4")
        out = ep.path("build", f"{ep.output}_whatsapp.mp4")
        audio.deliver(src, out)
        d = audio.stream_durations(out)
        print(f"wrote {out}  {os.path.getsize(out) / 1e6:.1f} MB  video {d.get('video', 0):.2f}s audio {d.get('audio', 0):.2f}s")
        return 0
    if cmd == "chars":
        sub, keys = rest[0], rest[1:]
        if sub == "face":
            arglists = [generate.char_face_args(ep, k) for k in (keys or ep.characters)]
        elif sub == "card":
            arglists = []
            for kv in keys:
                key, face = kv.split("=", 1)
                face, _, n = face.partition(":")
                arglists.append(generate.char_card_args(ep, key, face, n or 1))
        elif sub == "final" and keys:
            arglists = [generate.char_final_args(ep, k) for k in keys]
        else:
            ap.error("chars face [keys] | chars card key=face.png[:n] ... | chars final keys")
        generate.run_images(ep, arglists)
        return 0
    if cmd == "panels":
        sub, ids = rest[0], rest[1:]
        P = ep.data.get("panels", {})
        if sub == "draft":
            def hq(pid):
                if a.hq or a.flare:
                    return a.hq
                v = P[pid].get("hq")
                return v if v is not None else len(P[pid].get("chars", [])) >= 2
            generate.run_images(ep, [generate.panel_draft_args(ep, p, hq(p)) for p in (ids or P)])
        elif sub == "final" and ids:
            generate.run_images(ep, [generate.panel_final_args(ep, p) for p in ids])
        else:
            ap.error("panels draft [ids] [--flare|--hq] | panels final ids")
        return 0
    if cmd == "lines":
        generate.run_lines(ep, set(rest) or None)
        return 0
    if cmd == "sound":
        generate.run_sound(ep, set(rest) or None)
        return 0
    if cmd == "animate":
        if rest[:1] == ["pick"]:
            generate.pick_take(ep, rest[1], int(rest[2]))
        else:
            generate.run_animate(ep, set(rest) or None, a.takes)
        return 0
    if cmd == "lipsync":
        sub, only = rest[0], set(rest[1:]) or None
        shots, _ = timeline.build_timeline(ep)
        if sub == "plan":
            for p in lipsync.plan_parts(ep, shots):
                if not only or p["shot"] in only:
                    print(f"  {p['shot']}|{p['k']}  {p['line']:8} {p['who']:10} frames {p['f0']}-{p['f1']} mid {p['mid']}"
                          f"{'  SKIP' if p['skip'] else ''}")
        elif sub == "prep":
            lipsync.prep(ep, shots, only)
        elif sub == "run":
            lipsync.run(ep, shots, only, a.workers)
        elif sub == "join":
            lipsync.join_all(ep, shots, only)
        else:
            ap.error("lipsync plan|prep|run|join [shots]")
        return 0
    ap.error(f"unknown command {cmd}")


if __name__ == "__main__":
    sys.exit(main())
