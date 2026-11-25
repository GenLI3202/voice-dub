"""Text and subtitle rules, no model needed. Run with the voice-dub Python (it has numpy and num2words):

    ~/.voice-dub/venv/bin/python -m unittest discover -s tests
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skill" / "voice-dub" / "scripts"))

import dub  # noqa: E402
import say  # noqa: E402
import record  # noqa: E402
import voice as vd  # noqa: E402


class Speakable(unittest.TestCase):
    def test_english_numbers_and_acronyms(self):
        self.assertEqual(vd.speakable("SOC 0.65 for 4 h", "en"), "S O C zero point six five for four hours")
        self.assertEqual(vd.speakable("6,700 km, 50%", "en"), "six thousand, seven hundred km, fifty percent")
        self.assertEqual(vd.speakable("the 3rd lap", "en"), "the third lap")
        self.assertEqual(vd.speakable("2.50 in 1h", "en"), "two point five zero in one hour")

    def test_chinese_symbols(self):
        self.assertEqual(vd.speakable("δ ≥ 0", "zh"), "德尔塔 大于等于 0")
        self.assertEqual(vd.speakable("「先」做 3~5 组，占 20%", "zh"), "先做 3到5 组，占 百分之20")

    def test_lexicon_first(self):
        lex = {"MLX": "M L X", "Qwen": "Q wen"}
        self.assertEqual(vd.speakable("Qwen on MLX", "en", lex), "Q wen on M L X")

    def test_language(self):
        self.assertEqual(vd.detect_lang("Hello 世界"), "zh")
        self.assertEqual(vd.detect_lang("Hello world"), "en")


class Chunks(unittest.TestCase):
    def test_short_sentences_merge(self):
        self.assertEqual(vd.chunks("One. Two. Three.", "en"), ["One. Two. Three."])

    def test_long_text_splits_at_sentences(self):
        text = "。".join(["这是一个很长的句子用来测试分段" * 3] * 4) + "。"
        parts = vd.chunks(text, "zh")
        self.assertGreater(len(parts), 1)
        self.assertEqual("".join(parts), text)

    def test_decimal_is_not_a_sentence_end(self):
        self.assertEqual(vd.chunks("It is 0.65 now. Next.", "en"), ["It is 0.65 now. Next."])


class Srt(unittest.TestCase):
    def test_parse(self):
        body = "﻿1\r\n00:00:01,000 --> 00:00:03,500\r\n<i>Hello</i>\r\nthere\r\n\r\n" \
               "2\r\n00:00:04.2 --> 00:00:06,000 X1:0\r\n{\\an8}第二句\r\n"
        with tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False, encoding="utf-8") as f:
            f.write(body)
        cues = dub.read_srt(Path(f.name))
        self.assertEqual([(c.index, c.start, c.end, c.text) for c in cues],
                         [(1, 1.0, 3.5, "Hello there"), (2, 4.2, 6.0, "第二句")])


class SrtEdges(unittest.TestCase):
    def parse(self, body):
        with tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False, encoding="utf-8") as f:
            f.write(body)
        return dub.read_srt(Path(f.name))

    def test_empty_cue_does_not_swallow_the_next(self):
        cues = self.parse("1\n00:00:01,000 --> 00:00:02,000\n\n2\n00:00:03,000 --> 00:00:04,000\nHello &amp; bye\n")
        self.assertEqual([(c.index, c.text) for c in cues], [(2, "Hello & bye")])


class Markdown(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(say.plain("## Title"), "Title")
        self.assertEqual(say.plain("- **bold** and [a link](http://x) in snake_case_name"),
                         "bold and a link in snake_case_name")


class Recording(unittest.TestCase):
    def test_pick_builtin_mic(self):
        devices = [(0, "Microsoft Teams Audio"), (1, "iPhone Microphone"), (2, "MacBook Air Microphone")]
        self.assertEqual(record.pick_mic(devices, None), (2, "MacBook Air Microphone"))
        self.assertEqual(record.pick_mic(devices, "1"), (1, "iPhone Microphone"))

    def test_problems(self):
        self.assertEqual(record.problems({"seconds": 10, "peak_db": -6, "mean_db": -24}), [])
        self.assertTrue(record.problems({"seconds": 10, "peak_db": -91, "mean_db": -91}))
        self.assertTrue(record.problems({"seconds": 3, "peak_db": -6, "mean_db": -24}))


if __name__ == "__main__":
    unittest.main()
