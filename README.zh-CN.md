# voice-dub · 用自己的声音配音

[English](README.md)

一个在本地运行的 Agent 技能：录 10 秒自己的声音，就能用你的声音朗读文稿，或给视频、动画、幻灯片配音，
中英文都支持。基于 Qwen3-TTS 和 [mlx-audio](https://github.com/Neywa-Labs/mlx-audio)，全程在你的 Mac 上运行，
音频不会上传到任何地方。

适用于 Claude Code、Codex、Gemini 以及其他支持 `SKILL.md` 的 Agent。你只要说「用我的声音给这个视频配音」
或「把这段稿子读出来」，剩下的交给 Agent；正式配音前，它会先出一段试听让你确认。

## 使用前提

- Apple 芯片的 Mac（M1 及以上）。MLX 不支持 Intel Mac、Windows 和 Linux。
- [Homebrew](https://brew.sh)，然后 `brew install ffmpeg uv`
- 约 3.5 GB 磁盘空间：模型约 3 GB，Python 环境约 0.5 GB

## 安装

```bash
git clone https://github.com/GenLI3202/voice-dub.git
cd voice-dub
sh install.sh
```

`install.sh` 把技能复制到 `~/.claude/skills`、`~/.agents/skills`（Codex），以及已有的 Gemini 技能目录，
然后运行 `skill/voice-dub/scripts/setup.sh`：在 `~/.voice-dub/venv` 建一个装好 mlx-audio 的 Python 3.12
环境，并下载模型。更新时再运行一次即可。想直接改这份代码，用 `sh install.sh --link` 改用软链接安装。

装好后新开一个 Agent 会话，它才会认到这个技能。

## 录下你的声音（只需一次）

可以直接让 Agent 带你录，也可以自己运行。找个安静的房间，把电脑放在面前的桌上：

```bash
python3 ~/.claude/skills/voice-dub/scripts/record.py --lang zh     # 英文用 --lang en
```

它会自动选内置麦克风，显示一句话，按回车后倒数 3 秒开始录音。按平时说话的语速读一遍，读完保持安静，
等它自己停下。首次运行会弹出麦克风权限提示，点「允许」；如果第一次录出来是无声的，再运行一次即可。

已经有一段自己说话的清晰录音（比如语音备忘录，6–15 秒）？可以直接导入，`--text` 写录音里一字不差的原话：

```bash
python3 ~/.claude/skills/voice-dub/scripts/record.py --lang zh --import memo.m4a --text "录音里一字不差的原话。"
```

录完会自动检查音量和时长；以后想复查已存的声音，运行
`python3 ~/.claude/skills/voice-dub/scripts/record.py --check`。一段参考音就能说两种语言，另一种语言也是你的音色，只是略带口音；
想两种都最自然，就各录一段。录音技巧和常见问题见 [recording.md](skill/voice-dub/references/recording.md)。

## 怎么用

直接让 Agent 处理，也可以用安装好的虚拟环境手动运行脚本：

```bash
PY=~/.voice-dub/venv/bin/python
S=~/.claude/skills/voice-dub/scripts

$PY $S/say.py "你好，这是我的声音。" --out hello.wav                        # 一句话
$PY $S/say.py --file script.md --out narration.m4a                          # 整篇稿子
$PY $S/dub.py --srt talk.srt --video talk.mp4 --out talk_dubbed.mp4 --only 1-4   # 试听：前 4 条字幕
$PY $S/dub.py --srt talk.srt --video talk.mp4 --out talk_dubbed.mp4              # 完整配音
```

- `dub.py` 按每条字幕的起始时间对齐配音，并替换视频原声。某句配音超出了到下一条字幕的空档，会标记
  `OVERRUN`，方便你给那句多留点时间。
- 英文数字会转成英文读法（`0.65` → zero point six five），全大写缩写逐个字母读（`SOC` → S O C）；
  中文里的符号会换成词（`≥` → 大于等于）。其他读错的词用词表纠正：`--lexicon words.json`，内容如 `{"NASA": "nasa"}`。
- 生成过的句子有缓存，再跑一遍只生成改过的句子；加 `--fresh` 全部重新生成。
- `--voice <名字>` 可以分开存好几个人的声音（比如两个人共用一台 Mac）。

## 文件在哪

```
skill/voice-dub/
  SKILL.md               给 Agent 的说明
  scripts/setup.sh       Python 环境和模型
  scripts/record.py      录制或导入参考音（只需要 python3 和 ffmpeg）
  scripts/say.py         文字 → 音频
  scripts/dub.py         字幕 → 配音音轨 → 配好音的视频
  scripts/voice.py       共用：声音、文字规则、带缓存的生成
  references/recording.md
~/.voice-dub/            你的数据，不在仓库里：venv/、voices/<名字>/、cache/<名字>/
```

环境变量：`VOICE_DUB_HOME`（默认 `~/.voice-dub`）和 `VOICE_DUB_MODEL`（默认
`mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit`）。

测试（不需要模型）：`~/.voice-dub/venv/bin/python -m unittest discover -s tests`

## 只用你自己的声音

请只克隆你自己的声音，或已获本人同意的声音。不要从别人的录音里克隆声音，也不要做冒充其他真实人物的音频。
技能会让 Agent 拒绝这类请求。

## 致谢和许可

- 模型：[Qwen3-TTS](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base)，Qwen 团队，Apache 2.0；
  8-bit MLX 版本由 [mlx-community](https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit) 转换。
- 推理：[mlx-audio](https://github.com/Neywa-Labs/mlx-audio)，Prince Canuma，MIT。
- 本技能：[MIT](LICENSE)。
