"""Dialogue + SFX + music mix (music ducked under dialogue, dialogue compressed, loudness-normalized, padded to the
exact video length), the final mux, a duration check, and the share-friendly delivery encode."""
import os, re, subprocess
from timeline import adur, resolve_time

FFMPEG = "ffmpeg"
DIALOG_COMP = "acompressor=threshold=0.06:ratio=3.5:attack=5:release=150:makeup=2.2"  # lifts words a take let sag
DUCK = "sidechaincompress=threshold=0.02:ratio=6:attack=15:release=350"
# loudnorm shifts timestamps by ~70 ms, so an output -t would trim real audio off the end: renumber, then pad to the
# exact timeline length, so the mix is never shorter than the video
MASTER = "alimiter=limit=0.95,loudnorm=I=-15:TP=-1.5:LRA=11,aresample=48000,asetpts=N/SR/TB,apad=whole_dur={total:.6f}"
SILENT = "anullsrc=r=48000:cl=stereo"
_major = None


def _ffmpeg_major():
    global _major
    if _major is None:
        out = subprocess.run([FFMPEG, "-version"], capture_output=True, text=True).stdout
        m = re.search(r"version n?(\d+)\.", out)
        _major = int(m.group(1)) if m else 99
    return _major


def filter_script_args(path):
    """ffmpeg 7+ reads any option's value from a file with '-/'; 9 removed -filter_complex_script."""
    _ffmpeg_major()
    return ["-/filter_complex", path] if _major >= 7 else ["-filter_complex_script", path]


def audio_graph(ep, shots, total, nomusic=False, length_of=adur):
    starts = {s["id"]: s["start"] for s in shots}
    ends = {s["id"]: s["start"] + s["dur"] for s in shots}
    inputs, chains, dl, sx, mu, warnings = [], [], [], [], [], []

    def add(path, delay, vol, extra=""):
        inputs.extend(["-i", path])
        i = len(inputs) // 2 - 1
        ms = int(delay * 1000)
        chains.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo{extra},volume={vol},adelay={ms}|{ms}[a{i}]")
        return f"[a{i}]"

    for s in shots:
        for lid, (st, en) in s["placed"].items():
            dl.append(add(ep.line_audio(lid), s["start"] + st, 1.0))
        for name, t0, vol in s.get("sfx", []):
            sx.append(add(ep.path("sfx", f"{name}.mp3"), s["start"] + resolve_time(t0, s["placed"]), vol))
    for cue, a, b, vol, off in ([] if nomusic else ep.data.get("music_cues", [])):
        st, d = starts[a], ends[b] - starts[a]
        path = ep.path("music", f"{cue}.mp3")
        have = length_of(path) - off
        if have < d + .3:
            warnings.append(f"music cue {cue} has {have:.1f}s but {a}-{b} needs {d:.1f}s: it will stop early")
        mu.append(add(path, st, vol, f",atrim=start={off}:duration={d + .4},asetpts=PTS-STARTPTS,"
                                     f"afade=t=in:d=0.25,afade=t=out:st={max(0, d - .7)}:d=0.9"))
    parts = list(chains)
    if dl:
        parts.append(f'{"".join(dl)}amix=inputs={len(dl)}:normalize=0,{DIALOG_COMP}[dlg]')
    else:
        parts.append(f"{SILENT}[dlg]")
    if mu:
        # the ducking key is padded: sidechaincompress stops when its key ends, which would cut the music after the last line
        parts.append("[dlg]asplit=2[dlg1][dlgk0];[dlgk0]apad[dlgk]")
    parts.append(f'{"".join(sx)}amix=inputs={len(sx)}:normalize=0[sfx]' if sx else f"{SILENT}[sfx]")
    if mu:
        parts.append(f'{"".join(mu)}amix=inputs={len(mu)}:normalize=0[mus]')
        parts.append(f"[mus][dlgk]{DUCK}[musd]")
        parts.append(f"[dlg1][sfx][musd]amix=inputs=3:normalize=0,{MASTER.format(total=total)}[out]")
    else:
        parts.append(f"[dlg][sfx]amix=inputs=2:normalize=0,{MASTER.format(total=total)}[out]")
    return inputs, ";".join(parts), warnings


def mix(ep, shots, total, build_dir, nomusic=False):
    os.makedirs(build_dir, exist_ok=True)
    inputs, fc, warnings = audio_graph(ep, shots, total, nomusic)
    for w in warnings:
        print("WARNING:", w)
    out, script = os.path.join(build_dir, "audio.wav"), os.path.join(build_dir, "audio_filter.txt")
    with open(script, "w") as fh:
        fh.write(fc)
    r = subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", *inputs, *filter_script_args(script),
                        "-map", "[out]", "-t", f"{total:.6f}", "-ar", "48000", out])
    if r.returncode:
        raise SystemExit("audio mix failed (see the ffmpeg error above; the graph is in audio_filter.txt)")
    return out


def mux(video, wav, out):
    tmp = out + ".part.mp4"
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", video, "-i", wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", tmp], check=True)
    os.replace(tmp, out)


def stream_durations(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return {kind: float(d) for kind, d in (l.split(",")[:2] for l in out.split()) if d not in ("N/A", "")}


def check_durations(path, total, fps):
    d = stream_durations(path)
    v, a = d.get("video", 0.0), d.get("audio", 0.0)
    tol = max(1.5 / fps, 0.05)
    if abs(v - total) > tol or abs(a - v) > tol:
        raise RuntimeError(f"{os.path.basename(path)}: video {v:.3f}s, audio {a:.3f}s, timeline {total:.3f}s")
    return v, a


def deliver(src, out):
    """H.264/AAC at a size chat apps accept without re-compressing it much (~75 MB for 3.5 min at 1080x1920)."""
    tmp = out + ".part.mp4"
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-c:v", "libx264", "-preset", "slow",
                    "-crf", "24", "-maxrate", "3.5M", "-bufsize", "7M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out)
