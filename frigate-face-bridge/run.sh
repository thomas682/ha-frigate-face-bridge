#!/usr/bin/env bash
set -euo pipefail

export ADDON_VERSION="${ADDON_VERSION:-0.14.0}"

python /app/main.py
