import os, subprocess
import pytest
import audio, timeline

DUR = {"01-1": 1.0, "02-1": 1.5, "02-2": 1.2, "02-3": 0.8}


def sine(path, sec, f=300):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"sine=frequency={f}:duration={sec}", path], check=True)


def with_audio(ep):
    for lid, d in DUR.items():
        sine(ep.line_audio(lid), d)
    return timeline.build_timeline(ep)


def test_graph_shape(tiny):
    shots, total = timeline.build_timeline(tiny, DUR)
    inputs, fc, warnings = audio.audio_graph(tiny, shots, total, length_of=lambda p: 30.0)
    assert inputs.count("-i") == 5 and not warnings
    assert "amix=inputs=4:normalize=0,acompressor=threshold=0.06" in fc
    assert "anullsrc=r=48000:cl=stereo[sfx]" in fc and "sidechaincompress" in fc
    assert fc.endswith(f"loudnorm=I=-15:TP=-1.5:LRA=11,aresample=48000,asetpts=N/SR/TB,apad=whole_dur={total:.6f}[out]")
    assert "[dlgk0]apad[dlgk]" in fc and not fc.startswith(";")


def test_short_music_cue_warns(tiny):
    shots, total = timeline.build_timeline(tiny, DUR)
    _, _, warnings = audio.audio_graph(tiny, shots, total, length_of=lambda p: 2.0)
    assert len(warnings) == 1 and "music cue theme has 2.0s but S01-S02 needs" in warnings[0]


def test_filter_script_args(monkeypatch):
    monkeypatch.setattr(audio, "_major", 9)
    assert audio.filter_script_args("f.txt") == ["-/filter_complex", "f.txt"]
    monkeypatch.setattr(audio, "_major", 6)
    assert audio.filter_script_args("f.txt") == ["-filter_complex_script", "f.txt"]


def test_graph_without_sfx_or_music_runs(tiny, tmp_path):
    shots, total = with_audio(tiny)
    wav = audio.mix(tiny, shots, total, str(tmp_path), nomusic=True)
    assert abs(timeline.adur(wav) - total) < 0.002


def test_mix_is_padded_to_total(tiny, tmp_path, capsys):
    shots, total = with_audio(tiny)
    sine(tiny.path("music", "theme.mp3"), 3.0, 200)          # shorter than S01-S02
    sine(tiny.path("sfx", "ding.mp3"), 0.3, 900)
    shots[1]["sfx"] = [["ding", "S02-2", 0.5]]
    wav = audio.mix(tiny, shots, total, str(tmp_path))
    assert abs(timeline.adur(wav) - total) < 0.002            # the silent last shot is still there
    assert "music cue theme" in capsys.readouterr().out
    assert open(tmp_path / "audio_filter.txt").read().count("[out]") == 1


def test_mux_check_and_deliver(tmp_path):
    v, a, out = str(tmp_path / "v.mp4"), str(tmp_path / "a.wav"), str(tmp_path / "o.mp4")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=108x192:rate=24",
                    "-frames:v", "48", "-pix_fmt", "yuv420p", v], check=True)
    sine(a, 2.0)
    audio.mux(v, a, out)
    vd, ad = audio.check_durations(out, 2.0, 24)
    assert abs(vd - 2.0) < 0.05 and abs(ad - 2.0) < 0.06
    short = str(tmp_path / "short.wav"); sine(short, 1.0)
    audio.mux(v, short, str(tmp_path / "bad.mp4"))
    with pytest.raises(RuntimeError):
        audio.check_durations(str(tmp_path / "bad.mp4"), 2.0, 24)
    audio.deliver(out, str(tmp_path / "wa.mp4"))
    assert set(audio.stream_durations(str(tmp_path / "wa.mp4"))) == {"video", "audio"}


def test_music_keeps_playing_after_the_last_line(tmp_path):
    # the last shot is silent (no lines) but its music cue runs to the end: ducking must not cut the music off
    import config, json
    from conftest import tiny_cfg
    cfg = tiny_cfg()
    cfg["music_cues"] = [["theme", "S01", "S03", 0.5, 0]]
    (tmp_path / "episode.json").write_text(json.dumps(cfg, ensure_ascii=False))
    ep = config.load(str(tmp_path))
    shots, total = with_audio(ep)
    sine(ep.path("music", "theme.mp3"), total + 3, 200)
    wav = audio.mix(ep, shots, total, str(tmp_path / "b"))
    last = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{total - 1.2:.2f}", "-t", "0.8", "-i", wav,
                           "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    mean = float(last.split("mean_volume:")[1].split("dB")[0])
    assert mean > -40, mean                    # music audible in the last second, after every line has ended
