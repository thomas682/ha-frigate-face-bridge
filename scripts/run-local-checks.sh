#!/usr/bin/env sh
set -eu

cd "$(dirname "$0")/.."
python3 -m pip install -r frigate-face-bridge/requirements.txt pytest
python3 -m py_compile frigate-face-bridge/app/*.py
python3 -m pytest -q
python3 scripts/validate_function_docs.py
