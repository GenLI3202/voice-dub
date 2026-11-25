"""Shared parts of voice-dub: where voices live, text → speakable text, and a cached, checked renderer.

Run the scripts that import this with the voice-dub Python: <VOICE_DUB_HOME>/venv/bin/python (default ~/.voice-dub).
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HOME = Path(os.environ.get("VOICE_DUB_HOME", "~/.voice-dub")).expanduser()
MODEL = os.environ.get("VOICE_DUB_MODEL", "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit")
RATE = 24000
CJK = re.compile(r"[㐀-鿿]")
LANGS = ("zh", "en")


# ---------- voices ----------

def reference(voice: str, lang: str) -> tuple[Path, str]:
    """The reference clip and transcript for a voice; the same language is preferred, any other one is used if not."""
    folder = HOME / "voices" / voice
    order = [lang] + [other for other in LANGS if other != lang]
    for code in order:
        wav, txt = folder / f"{code}.wav", folder / f"{code}.txt"
        if wav.exists() and txt.exists():
            if code != lang:
                print(f"note: no {lang} reference for voice {voice!r}; using the {code} one "
                      f"(the timbre carries over, with a slight accent)", file=sys.stderr)
            return wav, txt.read_text(encoding="utf-8").strip()
    found = sorted(p.parent.name for p in (HOME / "voices").glob("*/*.wav"))
    hint = f" Saved voices: {', '.join(dict.fromkeys(found))}." if found else ""
    sys.exit(f"No reference for voice {voice!r} in {folder}.{hint} "
             f"Record one: python3 record.py --voice {voice} --lang {lang}")


def detect_lang(text: str) -> str:
    return "zh" if CJK.search(text) else "en"


# ---------- text ----------

GREEK_ZH = {"α": "阿尔法", "β": "贝塔", "γ": "伽马", "δ": "德尔塔", "Δ": "德尔塔", "ε": "艾普西龙", "θ": "西塔",
            "λ": "兰姆达", "μ": "缪", "π": "派", "ρ": "柔", "σ": "西格玛", "Σ": "西格玛", "τ": "套", "φ": "斐",
            "χ": "凯", "ω": "欧米伽", "Ω": "欧米伽", "ℓ": "艾欧"}
SIGNS_ZH = {"≥": "大于等于", "≤": "小于等于", "≠": "不等于", "≈": "约等于", "±": "正负", "×": "乘", "÷": "除以",
            "→": "到", "「": "", "」": "", "『": "", "』": ""}
SIGNS_EN = {"≥": " at least ", "≤": " at most ", "≠": " not equal to ", "≈": " about ", "±": " plus or minus ",
            "×": " times ", "÷": " divided by ", "→": " to ", "&": " and ", "%": " percent", "°C": " degrees Celsius",
            "°": " degrees"}


def load_lexicon(path: Path | None) -> dict[str, str]:
    """User pronunciations, {"written": "spoken"}, applied before every other rule (longest first)."""
    if not path:
        return {}
    table = json.loads(path.read_text(encoding="utf-8"))
    return dict(sorted(table.items(), key=lambda kv: -len(kv[0])))


def speakable(text: str, lang: str, lexicon: dict[str, str] | None = None) -> str:
    """What the model is asked to say. English spells out numbers and acronyms, or a Chinese reference
    makes them come out in Chinese; Chinese replaces symbols the model reads oddly."""
    for written, spoken in (lexicon or {}).items():
        text = text.replace(written, spoken)
    if lang == "zh":
        text = re.sub(r"(\d+(?:\.\d+)?)\s*%", r"百分之\1", text)
        text = re.sub(r"(?<=\d)\s*[~～]\s*(?=\d)", "到", text)              # 3~5 → 3到5
        for old, new in {**GREEK_ZH, **SIGNS_ZH}.items():
            text = text.replace(old, new)
        return re.sub(r"\s+", " ", text).strip()
    from num2words import num2words
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)                      # 6,700 → 6700
    for old, new in SIGNS_EN.items():
        text = text.replace(old, new)
    text = re.sub(r"\b([A-Z]{2,5})\b", lambda m: " ".join(m.group(1)), text)  # SOC → S O C
    text = re.sub(r"\b(\d+)\s*h\b", lambda m: f"{m.group(1)} {'hour' if m.group(1) == '1' else 'hours'}", text)
    text = re.sub(r"\b(\d+)(st|nd|rd|th)\b", lambda m: num2words(int(m.group(1)), to="ordinal"), text)
    text = re.sub(r"\d+\.\d+|\d+", lambda m: decimal_words(m.group()), text)
    return re.sub(r"\s+", " ", text).strip()


def decimal_words(number: str) -> str:
    """0.65 → zero point six five; digits after the point are read one by one, trailing zeros kept."""
    from num2words import num2words
    whole, _, frac = number.partition(".")
    said = num2words(int(whole))
    return said + (" point " + " ".join(num2words(int(d)) for d in frac) if frac else "")


def chunks(text: str, lang: str) -> list[str]:
    """Sentences, merged up to a comfortable length: the model drifts on very long inputs."""
    limit = 90 if lang == "zh" else 220
    parts = [p.strip() for p in re.split(r"(?<=[。！？!?；;])\s*|(?<=[.])\s+", text) if p.strip()]
    out: list[str] = []
    for part in parts:
        if out and len(out[-1]) + len(part) <= limit:
            out[-1] = f"{out[-1]}{'' if lang == 'zh' else ' '}{part}"
        else:
            out.append(part)
    return out


def expected_max(spoken: str, lang: str) -> float:
    """Longest believable clip, in seconds; a longer take has a made-up tail and is rendered again."""
    return 1.1 + (0.32 * len(spoken) if lang == "zh" else 0.085 * len(spoken))


# ---------- audio ----------

def decode(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(RATE),
                          "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()


def write(path: Path, x: np.ndarray) -> None:
    """Write mono float audio; the extension picks the format (.wav, .mp3, .m4a …)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    codec = {".mp3": ["-b:a", "160k"], ".m4a": ["-c:a", "aac", "-b:a", "160k"]}.get(path.suffix.lower(), [])
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(RATE), "-ac", "1", "-i", "-",
                    *codec, str(path)], input=x.astype(np.float32).tobytes(), check=True)


def trim(x: np.ndarray, rel: float = 0.006, lead: float = 0.04, tail: float = 0.16) -> np.ndarray:
    """Cut silence around a clip but keep the decay of the last syllable."""
    idx = np.flatnonzero(np.abs(x) > rel * (float(np.max(np.abs(x))) if len(x) else 1.0))
    if not len(idx):
        return x
    return x[max(0, idx[0] - int(lead * RATE)): idx[-1] + int(tail * RATE)]


def fade(x: np.ndarray, fin: float = 0.012, fout: float = 0.12) -> np.ndarray:
    """Raised-cosine fades, so no clip starts or ends on a click."""
    x = x.copy()
    a, b = min(len(x) // 4, int(fin * RATE)), min(len(x) // 3, int(fout * RATE))
    if a:
        x[:a] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, a))
    if b:
        x[len(x) - b:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, b))
    return x


def level(x: np.ndarray, rms: float = 0.1, peak: float = 0.89) -> np.ndarray:
    """Same loudness for every clip."""
    r = float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0
    x = x * (rms / (r or 1.0))
    m = float(np.max(np.abs(x))) if len(x) else 0.0
    return x * min(1.0, peak / (m or 1.0))


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * RATE), np.float32)


# ---------- rendering ----------

class Speaker:
    """One voice. Takes are cached by (model, reference, language, text), so a re-run renders only what changed."""

    def __init__(self, voice: str, cache: Path | None = None):
        self.voice = voice
        self.cache = cache or HOME / "cache" / voice
        self.cache.mkdir(parents=True, exist_ok=True)
        self._model = None
        self._refs: dict[str, tuple[Path, str]] = {}

    def _ref(self, lang: str) -> tuple[Path, str]:
        if lang not in self._refs:
            self._refs[lang] = reference(self.voice, lang)
        return self._refs[lang]

    def _load(self):
        if self._model is None:
            from mlx_audio.tts.utils import load_model
            with contextlib.redirect_stdout(io.StringIO()):
                self._model = load_model(model_path=MODEL)
        return self._model

    def say(self, spoken: str, lang: str, tries: int = 3, fresh: bool = False) -> np.ndarray:
        """One take of already-speakable text, trimmed. A take longer than believable is re-rendered and
        the shortest of up to `tries` kept. fresh: ignore the cache and keep the shortest of all tries."""
        ref, ref_text = self._ref(lang)
        stamp = f"{MODEL}|{ref.resolve()}|{ref.stat().st_mtime_ns}|{ref_text}|{lang}|{spoken}"
        key = hashlib.sha1(stamp.encode()).hexdigest()[:16]
        hit = self.cache / f"{key}.f32"
        if hit.exists() and not fresh:
            return np.fromfile(hit, np.float32)
        from mlx_audio.tts.generate import generate_audio
        best = None
        for _ in range(tries):
            prefix = self.cache / f"tmp_{key}"
            for old in self.cache.glob(prefix.name + "_*.wav"):
                old.unlink()
            model = self._load()
            with contextlib.redirect_stdout(io.StringIO()):            # mlx-audio prints every take
                generate_audio(text=spoken, model=model, ref_audio=str(ref), ref_text=ref_text,
                               lang_code=lang, file_prefix=str(prefix), verbose=False)
            parts = sorted(self.cache.glob(prefix.name + "_*.wav"))
            if not parts:
                raise RuntimeError(f"the model wrote no audio for: {spoken}")
            clip = trim(np.concatenate([decode(p) for p in parts]))
            for p in parts:
                p.unlink()
            if best is None or len(clip) < len(best):
                best = clip
            if not fresh and len(clip) / RATE <= expected_max(spoken, lang):
                break
        if len(best) / RATE > expected_max(spoken, lang):
            print(f"warning: every take ran long ({len(best) / RATE:.1f} s) for: {spoken}\n"
                  f"  not cached; listen to it, and shorten the line or re-run if it has a made-up tail",
                  file=sys.stderr)
        else:
            best.astype(np.float32).tofile(hit)
        return best

    def read(self, text: str, lang: str, lexicon: dict[str, str] | None = None, gap: float = 0.25,
             fresh: bool = False) -> np.ndarray:
        """A passage: sentence by sentence, levelled, with short pauses between sentences."""
        pieces = []
        for sentence in chunks(text, lang):
            spoken = speakable(sentence, lang, lexicon)
            if not re.search(r"\w", spoken):
                continue
            pieces += [fade(level(self.say(spoken, lang, fresh=fresh))), silence(gap)]
        return np.concatenate(pieces[:-1]) if pieces else silence(0.1)
