"""Shared helpers for the elevenlabs-tts scripts: the API key, clip paths, clip lengths.

Stdlib only. Imported by the scripts that sit beside it.
"""
import json, os, re, subprocess, sys

KEY_FILE = os.path.expanduser("~/.config/elevenlabs/api_key")
TAG = re.compile(r"\[[^\[\]\n]*\]")
# mp3_44100_128 is constant-bitrate: 128 kbit/s = 16,000 bytes per second of audio.
MP3_128_BYTES_PER_SECOND = 16_000


def api_key():
    """ELEVENLABS_API_KEY from the environment, else the first line of ~/.config/elevenlabs/api_key.

    Never prints the key. Exits with a message naming both places when neither has it.
    """
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key and os.path.exists(KEY_FILE):
        key = open(KEY_FILE).readline().strip()
    if not key:
        sys.exit(f"no ElevenLabs key: set ELEVENLABS_API_KEY, or put the key alone in {KEY_FILE} "
                 "(chmod 600). Never paste the key into a command or its output.")
    return key


def spoken_chars(text):
    """Characters that are actually spoken: the script with its audio tags removed."""
    return len(re.sub(r"\s+", " ", TAG.sub(" ", text)).strip())


def clip_path(audio_dir, key, prefix=None):
    """Where generate_tts.py wrote clip `key`.

    An explicit prefix wins. Otherwise the manifest's record for that clip (it stores
    the file name), and only then the historical default `slide`. This keeps a
    generate run with --prefix and a later check or align run without it in step.
    """
    if prefix is None:
        manifest = os.path.join(audio_dir, "_manifest.json")
        if os.path.exists(manifest):
            entry = json.load(open(manifest)).get(key) or {}
            if entry.get("file"):
                return os.path.join(audio_dir, entry["file"])
        prefix = "slide"
    return os.path.join(audio_dir, f"{prefix}{key}.mp3")


def duration(path, timeout=60):
    """Length in seconds via ffprobe (stdin closed so it can never wait on a terminal)."""
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True,
                         stdin=subprocess.DEVNULL, timeout=timeout, check=True).stdout
    return float(out.strip())


def mmss(seconds):
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}:{s:02d}"
