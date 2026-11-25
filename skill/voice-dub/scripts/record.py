"""Record or import the reference clip a cloned voice is built from. Needs only python3 and ffmpeg.

    python3 record.py --lang zh                      # show a sentence, count down, record it from the built-in mic
    python3 record.py --lang en --text "What I will read."
    python3 record.py --lang zh --import memo.m4a --text "录音里一字不差的原话。"
    python3 record.py --check                        # list saved voices and check each clip
    python3 record.py --mics                         # list microphones

Saves <VOICE_DUB_HOME>/voices/<voice>/<lang>.wav (24 kHz mono, silence trimmed) and <lang>.txt (the transcript).
VOICE_DUB_HOME defaults to ~/.voice-dub; the voice name defaults to "me".
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HOME = Path(os.environ.get("VOICE_DUB_HOME", "~/.voice-dub")).expanduser()
RATE = 24000
SENTENCES = {
    "zh": "今天天气不错，我打算先把手头的事情做完，再出门走走。路上要是碰到朋友，就一起坐下来喝杯咖啡，聊聊最近过得怎么样。",
    "en": "Today I want to finish the work on my desk first, and then go out for a walk. "
          "If I run into a friend on the way, we will sit down for a coffee and catch up.",
}
PREFER = re.compile(r"MacBook|Built-in|内建|麦克风|Microphone|Mikrofon", re.I)
AVOID = re.compile(r"iPhone|Teams|Zoom|BlackHole|Loopback|Virtual|Aggregate|Soundflower|Webex", re.I)


def mics() -> list[tuple[int, str]]:
    """Audio input devices as ffmpeg's avfoundation numbers them (the numbers can change between runs)."""
    out = subprocess.run(["ffmpeg", "-hide_banner", "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                         capture_output=True, text=True).stderr
    audio = out.split("audio devices:", 1)[1] if "audio devices:" in out else ""
    return [(int(i), name.strip()) for i, name in re.findall(r"\]\s*\[(\d+)\]\s*(.+)", audio)]


def pick_mic(devices: list[tuple[int, str]], wanted: str | None) -> tuple[int, str]:
    if wanted is not None:
        for i, name in devices:
            if wanted == str(i) or wanted.lower() in name.lower():
                return i, name
        sys.exit(f"No microphone matches {wanted!r}. Found: {devices}")
    if not devices:
        sys.exit("No microphone found. Allow your terminal app to use the microphone "
                 "(System Settings → Privacy & Security → Microphone).")
    good = [d for d in devices if PREFER.search(d[1]) and not AVOID.search(d[1])]
    return (good or [d for d in devices if not AVOID.search(d[1])] or devices)[0]


def clean(src: Path, dst: Path) -> None:
    """24 kHz mono, leading and trailing silence cut, 0.2 s kept at each end."""
    cut = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.2"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-ac", "1", "-ar", str(RATE),
                    "-af", f"{cut},areverse,{cut},areverse", str(dst)], check=True)


def stats(path: Path) -> dict[str, float]:
    out = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    level = {k: float(v) for k, v in re.findall(r"(max_volume|mean_volume): (-?[\d.]+) dB", out)}
    length = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                            capture_output=True, text=True, check=True).stdout
    return {"seconds": float(length), "peak_db": level.get("max_volume", -99.0), "mean_db": level.get("mean_volume", -99.0)}


def problems(s: dict[str, float]) -> list[str]:
    found = []
    if s["peak_db"] < -40:
        found.append("almost silent: wrong microphone, or the terminal has no microphone permission")
    elif s["peak_db"] < -25:
        found.append("quiet: move closer to the microphone")
    if s["peak_db"] > -0.3:
        found.append("clipped: move back a little or speak softer")
    if s["seconds"] < 5:
        found.append("short: 6 to 15 seconds of speech works best")
    if s["seconds"] > 25:
        found.append("long: 6 to 15 seconds of speech works best; trim it")
    return found


def report(wav: Path) -> bool:
    s = stats(wav)
    text = wav.with_suffix(".txt")
    words = text.read_text(encoding="utf-8").strip() if text.exists() else ""
    issues = problems(s) + ([] if words else ["no transcript next to it"])
    print(f"{wav}  {s['seconds']:.1f} s  peak {s['peak_db']:.1f} dB  mean {s['mean_db']:.1f} dB")
    print(f"  transcript: {words or '—'}")
    for issue in issues:
        print(f"  ! {issue}")
    return not issues


def countdown(n: int) -> None:
    for k in range(n, 0, -1):
        print(f"  {k}…", flush=True)
        time.sleep(1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--voice", default="me", help="voice name (folder under voices/)")
    ap.add_argument("--lang", choices=sorted(SENTENCES), help="language the reference is spoken in")
    ap.add_argument("--text", help="exact words that are (or will be) read; default: a sample sentence")
    ap.add_argument("--import", dest="source", type=Path, help="use an existing recording instead of the microphone")
    ap.add_argument("--seconds", type=int, default=14, help="recording length (silence is trimmed afterwards)")
    ap.add_argument("--countdown", type=int, default=3)
    ap.add_argument("--mic", help="microphone number or part of its name (see --mics)")
    ap.add_argument("--mics", action="store_true", help="list microphones and exit")
    ap.add_argument("--check", action="store_true", help="check the saved voices and exit")
    ap.add_argument("--print-text", action="store_true", help="print the sentence to read and exit")
    args = ap.parse_args()

    if args.mics:
        for i, name in mics():
            print(f"[{i}] {name}")
        return
    if args.check:
        clips = sorted((HOME / "voices").glob("*/*.wav"))
        if not clips:
            sys.exit(f"No voices yet in {HOME / 'voices'}. Record one: python3 record.py --lang zh")
        ok = [report(c) for c in clips]
        sys.exit(0 if all(ok) else 1)
    if not args.lang:
        ap.error("--lang is required (zh or en): the language you speak in the reference")
    if args.source and not args.text:
        ap.error("--import needs --text: the exact words spoken in that recording")

    text = (args.text or SENTENCES[args.lang]).strip()
    if args.print_text:
        print(text)
        return
    folder = HOME / "voices" / args.voice
    wav = folder / f"{args.lang}.wav"
    if args.source:
        if not args.source.exists():
            sys.exit(f"Not found: {args.source}")
        if args.source.resolve() == wav.resolve():
            sys.exit(f"{wav} is already the saved reference; to fix its transcript, edit {wav.with_suffix('.txt')}")
    folder.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "raw.wav"
        if args.source:
            raw = args.source
        else:
            if sys.platform != "darwin":
                sys.exit("Recording uses macOS's avfoundation; on other systems record elsewhere and use --import.")
            index, name = pick_mic(mics(), args.mic)
            print(f"Microphone: [{index}] {name}")
            print("Read this aloud once, at your normal pace, then stay quiet until recording stops:\n")
            print(f"    {text}\n")
            if sys.stdin.isatty():
                input("Press Enter when you are ready… ")
            countdown(args.countdown)
            print(f"  ● recording {args.seconds} s — read now, then stay quiet", flush=True)
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "avfoundation", "-i", f":{index}",
                            "-t", str(args.seconds), "-ac", "1", "-ar", str(RATE), str(raw)], check=True)
            print("  ■ done\n")
        clean(raw, wav)
    if not wav.exists() or wav.stat().st_size < 1000:
        wav.unlink(missing_ok=True)
        sys.exit("The recording is silent after trimming. Check the microphone (--mics) and its permission.")
    wav.with_suffix(".txt").write_text(text + "\n", encoding="utf-8")

    if report(wav):
        print(f"\nSaved. Listen to it: afplay {wav}")
        print("If you changed any words while reading, fix the transcript so it matches exactly:")
        print(f"  {wav.with_suffix('.txt')}")
    else:
        print("\nSaved, but re-record it (or --import a better take) before relying on it.")
        sys.exit(1)


if __name__ == "__main__":
    main()
