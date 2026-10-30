#!/usr/bin/env bash
set -e
cd "$(dirname "$(readlink -f "$0")")"
command -v python3 >/dev/null || { echo "Install Python 3.10+ and python3-venv."; exit 1; }
if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
./.venv/bin/python -m pip install -r requirements.txt
command -v ffmpeg >/dev/null || echo "Install FFmpeg (e.g. sudo apt install ffmpeg)."
exec ./.venv/bin/python -m streamlit run app.py
