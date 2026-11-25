#!/usr/bin/env bash
# One-time setup for voice-dub: a Python environment with mlx-audio, the voices folder, and the model.
#   bash setup.sh            # everything
#   bash setup.sh --no-model # skip the model download (it happens on first use instead)
set -euo pipefail

VD_HOME="${VOICE_DUB_HOME:-$HOME/.voice-dub}"
MODEL="${VOICE_DUB_MODEL:-mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit}"

if [[ "$(uname -s)" != Darwin || "$(uname -m)" != arm64 ]]; then
  echo "voice-dub runs the model with MLX, which needs a Mac with Apple Silicon (M1 or later)." >&2
  if [[ "$(uname -s)" == Darwin ]] && [[ "$(sysctl -n sysctl.proc_translated 2>/dev/null)" == 1 ]]; then
    echo "This terminal runs under Rosetta (Intel mode). Open a native terminal and run setup again." >&2
  fi
  exit 1
fi
missing=()
command -v ffmpeg >/dev/null || missing+=("ffmpeg  →  brew install ffmpeg")
command -v uv >/dev/null || missing+=("uv      →  brew install uv")
if ((${#missing[@]})); then
  printf 'Missing:\n' >&2
  printf '  %s\n' "${missing[@]}" >&2
  exit 1
fi

mkdir -p "$VD_HOME/voices"
if [[ ! -x "$VD_HOME/venv/bin/python" ]]; then
  uv venv "$VD_HOME/venv" --python 3.12
fi
VIRTUAL_ENV="$VD_HOME/venv" uv pip install --quiet "mlx-audio>=0.6.4,<0.7" "num2words>=0.5.13"

if [[ "${1:-}" != "--no-model" ]]; then
  echo "Downloading $MODEL (about 3 GB, once)…"
  "$VD_HOME/venv/bin/python" -c "from huggingface_hub import snapshot_download; snapshot_download('$MODEL')"
fi

echo
echo "Ready. Python: $VD_HOME/venv/bin/python"
echo "Next: record your reference voice with scripts/record.py (see SKILL.md)."
