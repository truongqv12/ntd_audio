#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../backend"
export PYTHONPATH=src
uvicorn voiceforge.main:app --reload --host 0.0.0.0 --port 8000
