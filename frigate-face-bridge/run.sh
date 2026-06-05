#!/usr/bin/env bash
set -euo pipefail

export ADDON_VERSION="${ADDON_VERSION:-0.12.1}"

python /app/main.py
