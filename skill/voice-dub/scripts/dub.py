"""Dub a video from its subtitles in a cloned voice: each cue is spoken from its start time.

    ~/.voice-dub/venv/bin/python dub.py --srt talk.srt --video talk.mp4 --out talk_dubbed.mp4 --only 1-4
    ~/.voice-dub/venv/bin/python dub.py --srt talk.srt --out talk_voice.wav           # voice track only

Writes the dubbed MP4 (video stream copied, the original audio replaced) or the voice track, and
<out stem>_dub/report.json with each cue's speech length against its slot. A cue whose speech runs into the
next cue is printed as OVERRUN.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import voice as vd


@dataclass(frozen=True)
class Cue:
    index: int
    start: float
    end: float
    text: str


def seconds(stamp: str) -> float:
    h, m, rest = stamp.replace(".", ",").split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")[:3]) / 1000


def read_srt(path: Path) -> list[Cue]:
    body = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    cues = []
    for block in re.split(r"\n[ \t]*\n", body.strip()):
        m = re.match(r"\s*(\d+)\s*\n(\S+)\s+-->\s+(\S+)[^\n]*(?:\n(.*))?\Z", block, re.S)
        if not m:
            continue
        text = re.sub(r"<[^>]+>|\{\\[^}]*\}", "", html.unescape(m.group(4) or ""))   # <i>, {\an8}, &amp;
        text = " ".join(text.split("\n")).strip()
        if text:
            cues.append(Cue(int(m.group(1)), seconds(m.group(2)), seconds(m.group(3)), text))
    return cues


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--srt", type=Path, required=True)
    ap.add_argument("--video", type=Path, help="video to put the voice on; without it only the voice track is written")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--voice", default="me")
    ap.add_argument("--lang", choices=["auto", *vd.LANGS], default="auto")
    ap.add_argument("--lexicon", type=Path, help='JSON {"written": "spoken"} pronunciations')
    ap.add_argument("--only", help="cue range for a trial, e.g. 1-4")
    ap.add_argument("--fresh", action="store_true", help="render again instead of using cached takes")
    args = ap.parse_args()

    cues = read_srt(args.srt)
    if not cues:
        sys.exit(f"no cues found in {args.srt}")
    following = {c.index: (cues[k + 1].start if k + 1 < len(cues) else c.end + 2.0) for k, c in enumerate(cues)}
    if args.only:
        try:
            lo, _, hi = args.only.partition("-")
            lo, hi = int(lo), int(hi or lo)
        except ValueError:
            sys.exit(f"--only takes a cue number or range, like 3 or 1-4 (got {args.only!r})")
        cues = [c for c in cues if lo <= c.index <= hi]
        if not cues:
            sys.exit(f"no cues numbered {args.only} in {args.srt}")
    work = args.out.with_name(args.out.stem + "_dub")
    work.mkdir(parents=True, exist_ok=True)
    lexicon = vd.load_lexicon(args.lexicon)
    speaker = vd.Speaker(args.voice)

    clips, report = [], []
    for cue in cues:
        lang = args.lang if args.lang != "auto" else vd.detect_lang(cue.text)
        clip = speaker.read(cue.text, lang, lexicon, fresh=args.fresh)
        length = len(clip) / vd.RATE
        slot = following[cue.index] - cue.start
        over = round(max(0.0, length - slot), 2)
        clips.append((cue.start, clip))
        report.append(dict(cue=cue.index, start=cue.start, speech_s=round(length, 2), slot_s=round(slot, 2),
                           overrun_s=over, spoken=vd.speakable(cue.text, lang, lexicon)))
        print(f"{cue.index:3d} {length:5.1f}s / slot {slot:5.1f}s {'OVERRUN' if over else ''}", flush=True)
    (work / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    offset = cues[0].start if args.only and not args.video else 0.0
    total = max(int((start - offset) * vd.RATE) + len(clip) for start, clip in clips) + vd.RATE // 2
    track = np.zeros(total, np.float32)
    for start, clip in clips:
        at = int((start - offset) * vd.RATE)
        track[at: at + len(clip)] += clip
    peak = float(np.max(np.abs(track)))
    if peak > 1.0:                                  # overlapping (overrun) cues: scale down instead of clipping
        track /= peak

    if args.video:
        voice_wav = work / "voice.wav"
        vd.write(voice_wav, track)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(args.video), "-i", str(voice_wav),
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                        "-af", "apad", "-shortest", str(args.out)], check=True)
    else:
        vd.write(args.out, track)
    overruns = [r["cue"] for r in report if r["overrun_s"] > 0]
    print(f"done: {args.out}; overrun cues: {overruns or 'none'}")


if __name__ == "__main__":
    main()
