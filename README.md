# voice-dub

[简体中文](README.zh-CN.md)

An agent skill that clones **your own voice** from a 10-second recording and uses it to read text aloud
or dub your videos, animations and slides, in Chinese or English. It runs entirely on your Mac
(Qwen3-TTS through [mlx-audio](https://github.com/Neywa-Labs/mlx-audio)); no audio is uploaded anywhere.

Works with Claude Code, Codex, Gemini and other agents that read `SKILL.md`. You say "dub this video in
my voice" or "read this script aloud"; the agent does the rest and asks you to listen to a short trial
first.

## What you need

- A Mac with Apple Silicon (M1 or later). MLX does not run on Intel Macs, Windows or Linux.
- [Homebrew](https://brew.sh), then `brew install ffmpeg uv`
- About 3.5 GB of disk: the model (~3 GB) and its Python environment (~0.5 GB)

## Install

```bash
git clone https://github.com/GenLI3202/voice-dub.git
cd voice-dub
sh install.sh
```

`install.sh` copies the skill into `~/.claude/skills`, `~/.agents/skills` (Codex) and Gemini's skills
folders if present, then runs `skill/voice-dub/scripts/setup.sh`: a Python 3.12 environment with
mlx-audio in `~/.voice-dub/venv`, and the model download. Re-run it to update. `sh install.sh --link`
links instead of copying, if you want to edit the checkout.

After installing, start a new agent session so it picks up the skill.

## Make your voice (once)

Ask your agent to set up your voice and it walks you through this, or run it yourself. In a quiet room,
with the laptop on a table in front of you:

```bash
python3 ~/.claude/skills/voice-dub/scripts/record.py --lang en     # or --lang zh
```

It picks the built-in microphone, shows a sentence, waits for Enter, counts down from 3 and records. Read
the sentence once at your normal pace, then stay quiet until it stops. The first time, macOS asks to let
your terminal use the microphone: allow it, and if that first take comes out silent, run it again.

Already have a clean clip of yourself (a voice memo, 6–15 s)? Import it, with exactly what you say in it:

```bash
python3 ~/.claude/skills/voice-dub/scripts/record.py --lang en --import memo.m4a --text "Exactly what I say."
```

Each recording is checked for length and loudness right away; to check saved voices later, run
`python3 ~/.claude/skills/voice-dub/scripts/record.py --check`. One reference works for both languages; the other one comes out in
your timbre with a slight accent. For the best result in both, record one of each. Tips and fixes:
[recording.md](skill/voice-dub/references/recording.md).

## Use it

Ask your agent, or run the scripts yourself with the skill's Python:

```bash
PY=~/.voice-dub/venv/bin/python
S=~/.claude/skills/voice-dub/scripts

$PY $S/say.py "Hello, this is my voice." --out hello.wav                   # a line
$PY $S/say.py --file script.md --out narration.m4a                         # a whole script
$PY $S/dub.py --srt talk.srt --video talk.mp4 --out talk_dubbed.mp4 --only 1-4   # trial: first 4 cues
$PY $S/dub.py --srt talk.srt --video talk.mp4 --out talk_dubbed.mp4              # full dub
```

- `dub.py` places each subtitle cue's speech at its start time and replaces the video's audio. A cue
  whose speech runs into the next one is printed as `OVERRUN`, so you can give that line more time.
- English numbers and acronyms are spelled out (`0.65` → "zero point six five", `SOC` → "S O C") and
  Chinese symbols become words (`≥` → 大于等于). Fix anything else with a lexicon file:
  `--lexicon words.json` containing `{"NASA": "nasa"}`.
- Takes are cached, so a re-run only renders changed lines. `--fresh` renders them again.
- `--voice <name>` keeps several voices apart (e.g. two people sharing a Mac).

## Where things are

```
skill/voice-dub/
  SKILL.md               the agent's instructions
  scripts/setup.sh       Python environment + model
  scripts/record.py      record or import your reference (python3 + ffmpeg only)
  scripts/say.py         text → audio
  scripts/dub.py         subtitles → voice track → dubbed video
  scripts/voice.py       shared: voices, text rules, cached rendering
  references/recording.md
~/.voice-dub/            your data, outside the repo: venv/, voices/<name>/, cache/<name>/
```

Environment variables: `VOICE_DUB_HOME` (default `~/.voice-dub`) and `VOICE_DUB_MODEL` (default
`mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit`).

Tests (no model needed): `~/.voice-dub/venv/bin/python -m unittest discover -s tests`

## Use your voice, and only yours

Clone your own voice, or someone's who has agreed to it. Don't clone a voice from someone else's
recordings, and don't make audio meant to pass as another real person. The skill tells the agent to
decline that.

## Credits and licence

- Model: [Qwen3-TTS](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base) by the Qwen team, Apache 2.0;
  8-bit MLX conversion by [mlx-community](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit).
- Inference: [mlx-audio](https://github.com/Neywa-Labs/mlx-audio) by Prince Canuma, MIT.
- This skill: [MIT](LICENSE).
