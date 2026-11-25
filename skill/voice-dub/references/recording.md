# Recording a good reference

The model copies whatever it hears in the reference: the voice, but also the room, the mic and the mood.
Ten clean seconds beat a minute of noisy ones.

## Do

- A quiet, soft room (a bedroom beats a kitchen; curtains and a sofa absorb echo).
- Laptop on a table, you about 40–60 cm from it, facing the screen. The built-in mic is fine.
- Your normal narrating voice: the tone you want in the videos. Calm and clear, not a performance.
- Read the sentence once through, without stopping. A small slip is fine if the transcript says what you
  actually said.
- 6–15 seconds of speech. `record.py` records 14 s and trims the silence at both ends.

## Avoid

- Background music, fans, keyboard clicks, a second voice.
- Bluetooth headsets and phone "continuity" mics: they record at low quality or, on some Macs, silence.
- Whispering, shouting, laughing, or reading much faster than you talk.

## When it sounds wrong

| What you hear | Likely cause | Fix |
|---|---|---|
| Silence, or `record.py --check` says "almost silent" | wrong mic, or the terminal app has no microphone permission | `record.py --mics`, then `--mic <number>`; System Settings → Privacy & Security → Microphone → allow your terminal |
| Echoey or hissy voice | room or distance | record closer, in a softer room |
| Words skipped, odd rhythm, wrong words at the start | the transcript does not match the recording | fix `~/.voice-dub/voices/<name>/<lang>.txt` word for word |
| A different-sounding person | reference too short or too expressive | record 10–15 s in a steady voice |
| Strong accent in the other language | the reference is in one language only | record a reference in that language too (`--lang en` / `--lang zh`) |

## Checking a clip

```bash
python3 ~/.claude/skills/voice-dub/scripts/record.py --check
```

It prints each saved clip's length and loudness. A good clip is 6–15 s with a peak between −25 and
−0.3 dB; around −90 dB means the file is silent. Listen with `afplay ~/.voice-dub/voices/me/zh.wav`.
