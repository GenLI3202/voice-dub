"""Read text aloud in a cloned voice.

    ~/.voice-dub/venv/bin/python say.py "Hello, this is my voice." --out hello.wav
    ~/.voice-dub/venv/bin/python say.py --file script.md --out narration.m4a

Paragraphs (blank-line separated) get a longer pause than sentences. Language is detected per paragraph
(any Chinese character → zh) unless --lang is given. The output format follows the extension.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np

import voice as vd


def plain(markdown: str) -> str:
    """Markdown → the words to say: no fences, headings marks, bullets, emphasis or link targets."""
    text = re.sub(r"```.*?```", "", markdown, flags=re.S)
    text = re.sub(r"^\s*(#+|[-*+]|\d+\.)\s+", "", text, flags=re.M)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"(\*\*|__|\*|`)(.+?)\1", r"\2", text)
    return text.strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", nargs="?", help="text to read (or use --file)")
    ap.add_argument("--file", type=Path, help="plain text or markdown file to read")
    ap.add_argument("--out", type=Path, required=True, help=".wav, .mp3 or .m4a")
    ap.add_argument("--voice", default="me")
    ap.add_argument("--lang", choices=["auto", *vd.LANGS], default="auto")
    ap.add_argument("--lexicon", type=Path, help='JSON {"written": "spoken"} pronunciations')
    ap.add_argument("--pause", type=float, default=0.7, help="seconds between paragraphs")
    ap.add_argument("--fresh", action="store_true", help="render again instead of using cached takes")
    args = ap.parse_args()

    if (args.text is None) == (args.file is None):
        ap.error("give either the text or --file")
    body = args.text if args.file is None else args.file.read_text(encoding="utf-8")
    paragraphs = [plain(p) for p in re.split(r"\n[ \t]*\n", body.replace("\r\n", "\n"))]
    paragraphs = [p for p in paragraphs if p]
    lexicon = vd.load_lexicon(args.lexicon)
    speaker = vd.Speaker(args.voice)

    out = []
    for k, para in enumerate(paragraphs, 1):
        lang = args.lang if args.lang != "auto" else vd.detect_lang(para)
        print(f"[{k}/{len(paragraphs)}] {lang} {para[:60]}{'…' if len(para) > 60 else ''}", flush=True)
        out += [speaker.read(" ".join(para.split("\n")) if lang == "en" else para.replace("\n", ""), lang,
                             lexicon, fresh=args.fresh), vd.silence(args.pause)]
    if not out:
        sys.exit("nothing to read")
    audio = np.concatenate(out[:-1])
    vd.write(args.out, audio)
    print(f"done: {args.out} ({len(audio) / vd.RATE:.1f} s)")


if __name__ == "__main__":
    main()
