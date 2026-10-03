"""Shot timeline driven by the real line durations: every start and length is a whole number of frames."""
import json, re, subprocess


def adur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    if not out:
        raise FileNotFoundError(f"no duration for {path} (missing or unreadable)")
    return float(out)


def resolve_time(ref, placed):
    """A number, or 'S<line>[+-x]' (that line's start) / 'E<line>[+-x]' (its end), relative to the shot start."""
    if ref is None or isinstance(ref, (int, float)):
        return ref
    m = re.match(r"([SE])(\w+-\w+)([+-][\d.]+)?$", ref)
    if not m:
        raise ValueError(f"bad time reference {ref!r}")
    kind, lid, off = m.group(1), m.group(2), float(m.group(3) or 0)
    st, en = placed[lid]
    return (st if kind == "S" else en) + off


def build_timeline(ep, durations=None):
    """(shots, total). durations: {line id: seconds} instead of ffprobe (tests)."""
    T, fps = ep.timing, ep.fps
    t_frames, shots = 0, []
    for s in ep.shots:
        cur, placed, prev_end = s.get("pre", T["default_pre"]) * T["pad_scale"], {}, None
        for spec in s.get("lines", []):
            lid, _, ov = spec.partition("@")
            d = durations[lid] if durations is not None else adur(ep.line_audio(lid))
            st = (prev_end + float(ov)) if (ov and prev_end is not None) else cur
            placed[lid] = (st, st + d)
            prev_end = st + d
            cur = prev_end + s.get("gap", T["gap"])
        if s.get("dur") is not None:
            dur = s["dur"] * T["silent_scale"]
        else:
            dur = max(prev_end + s.get("post", T["default_post"]) * T["pad_scale"], s.get("mindur", 0))
        nf = max(1, round(dur * fps))
        shots.append(dict(s, start=t_frames / fps, nframes=nf, dur=nf / fps, placed=placed))
        t_frames += nf
    return shots, t_frames / fps


def write_timeline(shots, path):
    json.dump([{k: v for k, v in s.items() if k in ("id", "start", "dur", "placed")} for s in shots],
              open(path, "w"), indent=1, ensure_ascii=False)
