#!/usr/bin/env bash
set -euo pipefail

export ADDON_VERSION="${ADDON_VERSION:-0.15.2}"

python /app/main.py
