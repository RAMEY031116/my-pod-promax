#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if command -v python3.11 >/dev/null 2>&1; then PY=python3.11; elif command -v python3 >/dev/null 2>&1; then PY=python3; else echo "Install Python 3.10+ first"; exit 1; fi
if [ ! -d .venv ]; then "$PY" -m venv .venv; fi
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
