#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
case $(uname -s) in
    Linux|Darwin) ;;
    *) echo 'Run on Linux or macOS.' >&2; exit 1 ;;
esac
[[ $EUID != 0 ]] || { echo 'Run as a non-root user.' >&2; exit 1; }
python3 -m unittest discover -s tests -v
