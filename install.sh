#!/usr/bin/env bash
# Install a private copy; no sudo and no shell startup changes.
set -euo pipefail
if [[ ${1:-} == --help ]]; then
    echo 'Usage: bash install.sh [--upgrade] [PREFIX]'
    echo 'Default PREFIX: $HOME/.local. Then add PREFIX/bin to PATH.'
    exit 0
fi
action=install
if [[ ${1:-} == --upgrade ]]; then action=upgrade; shift; fi
[[ $# -le 1 ]] || { echo 'Usage: bash install.sh [--upgrade] [PREFIX]' >&2; exit 2; }
platform=$(uname -s)
[[ ( $platform == Linux || $platform == Darwin ) && $EUID != 0 ]] || { echo 'Install on Linux or macOS as a regular user; do not use sudo.' >&2; exit 1; }
(( BASH_VERSINFO[0] > 3 || (BASH_VERSINFO[0] == 3 && BASH_VERSINFO[1] >= 2) )) || { echo 'Bash 3.2+ required.' >&2; exit 1; }
if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
    echo 'Python 3.11+ is required. Install it, then rerun this installer.' >&2
    if [[ $platform == Darwin ]]; then
        echo 'With Homebrew installed: brew install python' >&2
        echo 'Or install Python 3.11+ from https://www.python.org/downloads/macos/' >&2
    else
        echo 'Debian/Ubuntu: sudo apt update && sudo apt install python3 (check version afterward)' >&2
    fi
    exit 1
fi
startup_file=~/.bashrc
[[ ${SHELL:-} == */zsh ]] && startup_file=~/.zshrc
project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
prefix=${1:-$HOME/.local}
[[ $prefix == /* ]] || { echo 'PREFIX must be an absolute path.' >&2; exit 1; }
install_dir="$prefix/lib/safedelete"
launcher="$prefix/bin/safedelete"
python3 "$project_dir/lib/manage_install.py" "$action" "$prefix" --source "$project_dir"
printf '\nSafeDelete installed: %s\n\n1. Run now (also add this line once to %s):\n' "$launcher" "$startup_file"
printf 'export PATH=%q:"$PATH"\n' "$prefix/bin"
printf '\n2. Try these commands:\n'
printf '  safedelete --help\n  safedelete delete -- "report.txt"\n  safedelete list\n  safedelete restore ID\n'
printf '\n3. Use as a library from Bash (run bash first if using zsh):\nsource %q\n' "$install_dir/lib/safedelete.sh"
printf '\nType YES to confirm; any other response cancels. Default recovery: 24 hours.\n'
printf 'Quick guide: %s\n' "$install_dir/QUICK_REFERENCE.md"
printf '\nUpgrade later: bash install.sh --upgrade\n'
printf 'Uninstall: bash %q %q\n' "$install_dir/uninstall.sh" "$prefix"
