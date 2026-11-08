#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
[[ $(uname -s) == Linux && $EUID != 0 ]] || { echo 'Run on Linux as a non-root user.' >&2; exit 1; }
python3 -m unittest discover -s tests -v
