---
name: voice-dub
description: Clone the user's own voice from a 10-second recording and use it to read text aloud or dub explainer videos, animations and slides (Qwen3-TTS Base through mlx-audio, fully local on Apple Silicon Macs). Use whenever the user asks to add voice-over, narration, 配音, 旁白, 讲解语音 or TTS in their own voice, to read a script aloud in their voice, or to set up or re-record their cloned voice — Chinese or English. Not for music, sound effects, preset synthetic voices, or anyone's voice but the user's own (or one they have the speaker's consent for).
---

# Voice dub with your own cloned voice

Everything runs on the user's Mac; no audio leaves it. Scripts are in `scripts/` next to this file
(`SKILL_DIR/scripts`). Data lives in `VOICE_DUB_HOME` (default `~/.voice-dub`):

```
~/.voice-dub/
  venv/                 Python with mlx-audio (made by setup.sh)
  voices/<name>/        zh.wav + zh.txt, en.wav + en.txt  (reference clip + its exact transcript)
  cache/<name>/         rendered takes, so re-runs only render changed text
```

`PY` below means `~/.voice-dub/venv/bin/python` (or `$VOICE_DUB_HOME/venv/bin/python`).

## Consent

Clone only the user's own voice, or a voice whose speaker has agreed to it. Do not clone a voice from
someone else's video, call or voicemail, and do not make audio meant to pass as another real person.
If the user asks for that, decline and offer their own voice instead.

## 0. First use: set up

Check `~/.voice-dub/venv/bin/python` exists. If not:

```bash
bash SKILL_DIR/scripts/setup.sh
```

It needs an Apple Silicon Mac, `ffmpeg` and `uv` (it says how to install what is missing), installs
mlx-audio into `~/.voice-dub/venv` and downloads the model (about 3 GB, once). Run it in the
background; it takes a few minutes.

## 1. First use: record the reference

Check for a voice: `python3 SKILL_DIR/scripts/record.py --check`. With none, record one. The user has to
speak and see the countdown, so **do not run the microphone recording yourself** (your tool output is not
shown live). Write the real path in place of `SKILL_DIR` in every command you give the user.

1. Ask which language they will narrate in most (zh or en). One reference is enough; the other language
   then comes out in the same timbre with a slight accent. For the best English *and* Chinese, record both.
2. Show them the sentence they will read (`record.py --lang zh --print-text`) and tell them: quiet room,
   laptop on a table, normal speaking voice, read it once at their usual pace, then stay quiet until it
   stops. Ask them to run this in a terminal window and tell you when it is done:
   ```bash
   python3 SKILL_DIR/scripts/record.py --lang zh
   ```
   It picks the built-in mic, waits for Enter, counts down 3 s, records 14 s, trims the silence and saves
   `voices/me/zh.wav` + `zh.txt`. The first run makes macOS ask for microphone access; if that take comes
   out silent, they allow it and run the command again.
3. They already have a good recording (voice memo, podcast clip of themselves, 6–15 s of clean speech)?
   Import it instead; the transcript must be word for word what is said:
   ```bash
   python3 SKILL_DIR/scripts/record.py --lang en --import memo.m4a --text "Exactly what I say in it."
   ```
4. Run `record.py --check`. It flags silent (wrong mic or no microphone permission for the terminal),
   quiet, clipped, too short or too long clips. If they changed words while reading, fix the `.txt`.
5. Once `setup.sh` has finished, render a test line in the language they chose and give it to them to
   play (send the file if your app can; otherwise give the path, `afplay <path>` plays it). Wait for their
   OK before real work:
   ```bash
   PY SKILL_DIR/scripts/say.py "这是我的声音，听起来还像我吗？" --out /tmp/voice-test.wav
   PY SKILL_DIR/scripts/say.py "This is my voice. Does it sound like me?" --out /tmp/voice-test.wav
   ```
   Not like them? See `references/recording.md` and re-record.

More voices or more people on one Mac: `--voice <name>` on every script.

## 2. Read text aloud

```bash
PY SKILL_DIR/scripts/say.py --file script.md --out narration.m4a      # or: say.py "text" --out x.wav
```

Paragraphs get a 0.7 s pause (`--pause`), sentences 0.25 s. Language is detected per paragraph (any
Chinese character → zh); force it with `--lang`. Output format follows the extension (.wav .mp3 .m4a).

## 3. Dub a video from subtitles

1. **Get timed text.** Prefer an existing `.srt`. For an animation you generate (Manim, Motion Canvas,
   a slide deck), have the code write an SRT with one cue per narration line at the time it appears.
2. **Trial first**: 2–4 cues (`--only 1-4`, or one cue: `--only 3`); give the MP4 to the user before
   the full run. `--video` replaces the video's audio track entirely: if it has music or sound the user
   wants to keep, say so first, or leave out `--video` to get only the voice track to mix themselves.
   ```bash
   PY SKILL_DIR/scripts/dub.py --srt X.srt --video X.mp4 --out /tmp/trial.mp4 --only 1-4
   ```
3. **Full run**, output next to the source as `<name>_dubbed.mp4`. `<name>_dubbed_dub/` holds
   `voice.wav` and `report.json` (working files; do not commit them unless asked). Without `--video` it
   writes just the voice track.
4. **Fix overruns.** `OVERRUN` means speech is longer than the gap to the next cue. Give that line more
   time in the source (hold the frame longer, move the next cue) and re-render, or shorten the sentence.
   Do not speed the voice up unless the user asks.
5. Give the user the result and name any overruns left.

## Text rules (applied by the scripts)

- **English:** numbers become words (`0.65` → "zero point six five", `3rd` → "third", `6,700` →
  "six thousand, seven hundred"), 2–5 letter all-caps words are spelled out (`SOC` → "S O C"),
  `4 h` → "four hours", `%` `≥` `→` and similar become words. Otherwise a Chinese reference makes digits
  come out in Chinese.
- **Chinese:** Greek letters and relation signs become words (δ 德尔塔, ≥ 大于等于), `20%` → 百分之20,
  `3~5` → 3到5, 「」 removed. Digits stay digits (read in Chinese).
- **Anything that still reads wrong** (names, brands, an acronym said as a word like "NASA"): put it in a
  lexicon file `{"NASA": "nasa", "Qwen": "Q wen"}` and pass `--lexicon file.json`; it is applied first.
- Formulas do not belong in spoken text. When a caption is mostly symbols, write a spoken paraphrase in a
  separate narration SRT instead of reading the symbols.

## Quality notes

- A take that runs much longer than the text should (the model sometimes adds a made-up tail) is
  rendered again, up to 3 times, keeping the shortest. Re-roll a take you do not like with `--fresh`
  (it ignores the cache for that run).
- Takes are cached in `~/.voice-dub/cache/<voice>/` by model, reference, language and text; re-recording
  the reference invalidates them. Delete the folder to free space.
- A reference recorded in one language and used for the other keeps the timbre with a slight accent. If
  the user narrates mostly in English with a Chinese reference (or the reverse), suggest recording a
  second reference in that language.
- Another model: set `VOICE_DUB_MODEL` (an mlx-audio Qwen3-TTS **Base** model; Base models clone, the
  CustomVoice/VoiceDesign ones do not). Use the full repo name including `12Hz`; a short name fails with a
  misleading 401.
