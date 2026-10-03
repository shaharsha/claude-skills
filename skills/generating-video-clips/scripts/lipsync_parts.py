#!/usr/bin/env python3
"""Cut a dialogue shot into one-speaker parts for lip-sync, and join the synced parts back frame-exactly.

  python3 lipsync_parts.py normalize src.mp4 shot.mp4 --frames 132 [--off 1.5] [--speed 1.22] [--fps 24] [--size 720x1280]
  python3 lipsync_parts.py split shot.json parts/ [--synced synced/]
      -> parts/<id>_<k>.mp4 + .wav, parts/<id>_plan.json, parts/<id>_lipsync_jobs.json
  python3 lipsync_parts.py join parts/<id>_plan.json synced/ final/<id>.mp4 [--strict]

normalize makes exactly --frames frames: start at --off seconds, slow by --speed, resample to --fps, scale to
cover --size and center-crop (a 16:9 clip into a 9:16 size is cropped, never squashed), and hold the last frame
if the clip runs out.
shot.json: {"id": "S05", "video": "shot.mp4", "fps": 24, "frames": 132, "size": "720x1280",
            "lines": [{"id": "05-1", "audio": "lines/05-1.mp3", "start": 0.72, "end": 2.31, "speaker": "maya"},
                      {"id": "05-2", "audio": "lines/05-2.mp3", "start": 2.43, "end": 4.10, "speaker": "ido", "skip": true}]}
start/end are seconds from the shot start, where the edit places each line (paths relative to shot.json).
A part runs from the middle of the gap before its line to the middle of the gap after it, or to the next
line's start when lines overlap, so every frame belongs to exactly one speaker. Mark skip for a speaker seen
from behind, off screen, or a crowd shout: those parts keep their original frames.
split also writes <id>_lipsync_jobs.json for lipsync_fal.py --jobs: one entry per NON-skip part, with absolute
paths, out = <synced>/<id>_<k>.mp4 (the name join looks for) and face = null. Set each face to "x,y@<mid>"
(mid is in the entry) or leave null to let the model guess when only one face is visible.
join takes <synced>/<id>_<k>.mp4 when it exists, forces every part to its exact frame count (holding its last
frame however short the model's output is), warns for every non-skip part with no synced file (--strict
makes that an error), concatenates, and checks the total frame count.
"""
import argparse, json, os, subprocess, sys


def ff(*a):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *a], check=True)


def cuts(lines, frames, fps):
    """[(line, f0, f1)] covering frames 0..frames exactly, one part per line, in time order."""
    ls = sorted(lines, key=lambda l: l["start"])
    edges = [0]
    for a, b in zip(ls, ls[1:]):
        c = (a["end"] + b["start"]) / 2 if b["start"] >= a["end"] else b["start"]
        edges.append(round(c * fps))
    edges.append(frames)
    return [(l, edges[i], edges[i + 1]) for i, l in enumerate(ls)]


def normalize(src, out, frames, off=0.0, speed=1.0, fps=24, size="720x1280"):
    w, h = size.split("x")
    ff("-ss", f"{off:.3f}", "-i", src, "-vf",
       f"setpts=PTS*{speed},fps={fps},scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h},"
       "tpad=stop_mode=clone:stop=-1",
       "-frames:v", str(frames), "-an", "-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p", out)


def split(shot, parts_dir, root=".", synced_dir=None):
    os.makedirs(parts_dir, exist_ok=True)
    synced_dir = os.path.abspath(synced_dir or os.path.join(os.path.dirname(os.path.abspath(parts_dir)), "synced"))
    fps, sid = shot.get("fps", 24), shot["id"]
    video = os.path.join(root, shot["video"])
    plan = {"id": sid, "fps": fps, "size": shot.get("size", "720x1280"), "parts": []}
    for k, (l, f0, f1) in enumerate(cuts(shot["lines"], shot["frames"], fps)):
        if l["start"] * fps >= shot["frames"]:
            print(f"WARNING: line {l['id']} starts at {l['start']:.2f}s, after the shot ends "
                  f"({shot['frames'] / fps:.2f}s): its part is silent", file=sys.stderr)
        if f1 - f0 < 12:
            print(f"WARNING: {sid}_{k} ({l.get('speaker')}) is only {f1 - f0} frames: lines that start together can't be "
                  f"split one speaker per part; mark one of them \"skip\"", file=sys.stderr)
        v = os.path.join(parts_dir, f"{sid}_{k}.mp4")
        a = os.path.join(parts_dir, f"{sid}_{k}.wav")
        ff("-i", video, "-vf", f"trim=start_frame={f0}:end_frame={f1},setpts=PTS-STARTPTS", "-an",
           "-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p", v)
        ms = max(0, int((l["start"] - f0 / fps) * 1000))
        ff("-i", os.path.join(root, l["audio"]), "-af", f"adelay={ms}|{ms},apad", "-t", f"{(f1 - f0) / fps:.4f}",
           "-ar", "44100", a)
        plan["parts"].append({"k": k, "line": l["id"], "speaker": l.get("speaker"), "f0": f0, "f1": f1,
                              "mid": (f1 - f0) // 2, "skip": bool(l.get("skip")), "video": v, "audio": a})
    path = os.path.join(parts_dir, f"{sid}_plan.json")
    with open(path, "w") as fh:
        json.dump(plan, fh, indent=1)
    jobs = [{"video": os.path.abspath(p["video"]), "audio": os.path.abspath(p["audio"]),
             "out": os.path.join(synced_dir, f"{sid}_{p['k']}.mp4"), "face": None, "mid": p["mid"], "speaker": p["speaker"]}
            for p in plan["parts"] if not p["skip"]]
    with open(os.path.join(parts_dir, f"{sid}_lipsync_jobs.json"), "w") as fh:
        json.dump(jobs, fh, indent=1)
    return path


def nframes(path):
    return int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                               "stream=nb_read_frames", "-of", "csv=p=0", path], capture_output=True, text=True).stdout or 0)


def join(plan_path, synced_dir, out, strict=False):
    plan = json.load(open(plan_path))
    fps, sid = plan["fps"], plan["id"]
    w, h = plan["size"].split("x")
    d = os.path.dirname(os.path.abspath(plan_path))
    lst = os.path.join(d, f"{sid}_join.txt")
    with open(lst, "w") as fh:
        for p in sorted(plan["parts"], key=lambda p: p["k"]):
            synced = os.path.join(synced_dir, f"{sid}_{p['k']}.mp4")
            if not p["skip"] and not os.path.exists(synced):
                msg = f"{sid}_{p['k']} ({p.get('speaker')}): no {synced}, the part stays unsynced"
                if strict:
                    raise RuntimeError(msg)
                print("WARNING:", msg, file=sys.stderr)
            src = synced if (os.path.exists(synced) and not p["skip"]) else p["video"]
            fixed = os.path.join(d, f"{sid}_{p['k']}_fixed.mp4")
            ff("-i", src, "-vf", f"fps={fps},scale={w}:{h},tpad=stop_mode=clone:stop=-1",
               "-frames:v", str(p["f1"] - p["f0"]), "-an", "-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p", fixed)
            fh.write(f"file '{fixed}'\n")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    tmp = out + ".part.mp4"
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c:v", "libx264", "-crf", "15", "-pix_fmt", "yuv420p", "-r", str(fps), tmp)
    want = sum(p["f1"] - p["f0"] for p in plan["parts"])
    got = nframes(tmp)
    if got != want:
        os.remove(tmp)
        raise RuntimeError(f"{sid}: joined {got} frames, the plan needs {want}")
    os.replace(tmp, out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("normalize"); n.add_argument("src"); n.add_argument("out")
    n.add_argument("--frames", type=int, required=True); n.add_argument("--off", type=float, default=0.0)
    n.add_argument("--speed", type=float, default=1.0); n.add_argument("--fps", type=int, default=24)
    n.add_argument("--size", default="720x1280")
    s = sub.add_parser("split"); s.add_argument("shot_json"); s.add_argument("parts_dir"); s.add_argument("--synced")
    j = sub.add_parser("join"); j.add_argument("plan"); j.add_argument("synced_dir"); j.add_argument("out")
    j.add_argument("--strict", action="store_true", help="fail instead of warning when a non-skip part has no synced file")
    a = ap.parse_args()
    if a.cmd == "normalize":
        normalize(a.src, a.out, a.frames, a.off, a.speed, a.fps, a.size)
    elif a.cmd == "split":
        shot = json.load(open(a.shot_json, encoding="utf-8"))
        print(split(shot, a.parts_dir, os.path.dirname(os.path.abspath(a.shot_json)), a.synced))
    else:
        join(a.plan, a.synced_dir, a.out, a.strict)
        print(a.out)


if __name__ == "__main__":
    main()
