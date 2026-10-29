#!/bin/zsh
set -e
cd "${0:A:h}"
echo "Launching My pod promax from: $PWD"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3 not found. Install Python 3.10+ from python.org.'
  exit 1
fi
if [[ ! -x .venv/bin/python ]]; then
  echo 'Creating an isolated Python environment...'
  python3 -m venv .venv
fi
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python -c 'import streamlit, mutagen, yt_dlp; print("Dependencies ready")'
echo 'Open http://localhost:8501 in your browser if it does not open automatically.'
./.venv/bin/python -m streamlit run app.py
