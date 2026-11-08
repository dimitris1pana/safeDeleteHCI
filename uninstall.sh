#!/usr/bin/env bash
set -euo pipefail
if [[ ${1:-} == --help ]]; then
    echo 'Usage: bash uninstall.sh [PREFIX] [--yes]'
    echo 'Default PREFIX: $HOME/.local. Quarantined files are preserved.'
    exit 0
fi
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
prefix=$HOME/.local
if [[ $# -gt 0 && $1 != --yes ]]; then prefix=$1; shift; fi
python3 "$project_dir/lib/manage_install.py" uninstall "$prefix" "$@"
