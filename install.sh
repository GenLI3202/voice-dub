#!/bin/sh
# Install the voice-dub skill for Claude Code, Codex and Gemini, then set up its Python and model.
#   sh install.sh          copy the skill into each agent's skills folder (re-run to update)
#   sh install.sh --link   link instead of copy (for editing this checkout)
# Your recorded voices live in ~/.voice-dub and are never touched by this script.
set -e
REPO="$(cd "$(dirname "$0")" && pwd)"
SRC="$REPO/skill/voice-dub"
NAME="voice-dub"
MODE="${1:-copy}"

install_to() {
  dest="$1/$NAME"
  if [ -L "$dest" ] && [ "$(cd "$dest" && pwd -P)" = "$(cd "$SRC" && pwd -P)" ]; then
    echo "already linked: $dest"
    return
  fi
  if [ -e "$dest" ] && [ ! -f "$dest/scripts/voice.py" ]; then
    echo "skipped: $dest exists and is not this skill (move it away and re-run)" >&2
    return
  fi
  mkdir -p "$1"
  rm -rf "$dest"
  if [ "$MODE" = "--link" ]; then
    ln -s "$SRC" "$dest"
  else
    cp -R "$SRC" "$dest"
    find "$dest" -name __pycache__ -type d -prune -exec rm -rf {} +
  fi
  echo "installed: $dest"
}

install_to "$HOME/.claude/skills"                                          # Claude Code
install_to "$HOME/.agents/skills"                                          # Codex
[ -d "$HOME/.gemini/config" ] && install_to "$HOME/.gemini/config/skills"  # Antigravity
[ -d "$HOME/.gemini/skills" ] && install_to "$HOME/.gemini/skills"         # Gemini CLI

bash "$SRC/scripts/setup.sh"
