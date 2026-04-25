#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../backend"
export PYTHONPATH=.
dramatiq src.voiceforge.tasks
