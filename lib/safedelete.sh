# Safe to source: does not change shell options or install traps.
# Requires Bash 3.2+, Python 3.11+, Linux or macOS.
_safedelete_home=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)
safedelete() { python3 "$_safedelete_home/lib/engine.py" "$@"; }
safedelete_delete() { safedelete delete "$@"; }
safedelete_restore() { safedelete restore "$@"; }
safedelete_list() { safedelete list "$@"; }
safedelete_purge() { safedelete purge "$@"; }
safedelete_purge_expired() { safedelete purge-expired "$@"; }
# Assignment vocabulary; prefixed names above remain available.
safe_delete() { safedelete_delete "$@"; }
undo_delete() { safedelete_restore "$@"; }
list_deleted() { safedelete_list "$@"; }
purge_expired() { safedelete_purge_expired "$@"; }
