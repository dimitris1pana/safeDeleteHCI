# SafeDelete By HCI lab University Of Piraeus

 *An idea by Konstantinos Giovas 3rd year student of the department of Informatics to be followed and developed further by the HCI lab at the University of Piraeus*
For fast installation and everyday terminal commands, see the [Quick Reference Guide](QUICK_REFERENCE.md).
For an explanation of every project file and folder, see [Project Structure](PROJECT_STRUCTURE.md).
For a short classroom usability evaluation, use the [Usability Questionnaire](USABILITY_QUESTIONNAIRE.md).

A reusable Linux and macOS Bash library and command-line tool that moves files and folders
into private quarantine, supports timed retention and explicit undo, and only
permanently deletes entries after their retention period expires.

## Requirements and setup

Linux with glibc `renameat2` and filesystem support for `RENAME_NOREPLACE`, or
macOS with `renameatx_np` and filesystem support for `RENAME_EXCL` (tested on APFS).
Bash 3.2+ and Python 3.11+ are required. Standard library only. Run as your regular user, never root.
Extract the entire project together; the CLI locates its library relative to itself.

```bash
chmod +x bin/safedelete
export SAFEDELETE_ROOT="$HOME/.local/share/safedelete"
export SAFEDELETE_TTL=86400  # seconds; default: one day
./bin/safedelete delete --ttl 3600 -- '/home/me/report.txt'
./bin/safedelete list
./bin/safedelete restore ENTRY_ID
./bin/safedelete purge ENTRY_ID
```

`delete`, `restore`, and `purge` ask you to type `YES` in a terminal. Without a
terminal they refuse to proceed unless you explicitly supply `--yes` after the
command. IDs are printed only after a successful delete; `list` emits one JSON
record per entry, including state, original path, expiration, and payload status.
Paths in prompts and JSON are escaped to avoid terminal control sequences.

For filenames starting with a dash, use `--` before the path. One path per call
keeps each result independent. Nonexistent paths are errors. TTL is an integer
from 1 to 315360000 seconds.

## Bash library

```bash
source /absolute/path/to/safedelete/lib/safedelete.sh
if id=$(safedelete_delete --yes --ttl 600 -- "$HOME/example.txt"); then
    safedelete_restore --yes "$id"
fi
safedelete_list
# Alternative per-call quarantine; global options precede the subcommand:
safedelete --root /mnt/data/my-quarantine delete --yes -- /mnt/data/item
```

Functions return the command status without changing shell options or installing
traps. `safedelete`, `safedelete_delete`, `safedelete_restore`,
`safedelete_list`, and `safedelete_purge` are public functions. The private
`_safedelete_home` variable must remain intact after sourcing.

Exit statuses: 0 success, 1 filesystem/validation/locking/confirmation failure,
2 invalid command syntax, 130 interrupted. Errors go to stderr. Failed mutations
can leave a recovery record; inspect `list` before retrying.

## Retention and purge

Expiration ends the recovery window and makes an entry **eligible** for purge.
Nothing is deleted in the background unless you configure the optional scheduler below.
Restore refuses expired entries, including when confirmation crosses the deadline. Clock
changes affect eligibility because expiration uses UTC Unix wall-clock time.
Purge is permanent, requires an exact entry ID, and still asks for confirmation.
There is no recursive arbitrary-path purge or early-purge override.

For deliberate scripted purge use `purge --yes ID` or `purge-expired --yes`.
The latter selects expired stored/purging entries while holding the quarantine lock.
This project does not install a scheduler automatically. Review
retention requirements before configuring unattended permanent deletion.

## Safeguards and metadata

* Private quarantine owned by the invoking user, exactly mode 0700; new records
  and locks use restrictive permissions. Existing roots are validated, not chmodded.
* All operations on one quarantine share a nonblocking exclusive advisory lock.
  A busy operation fails immediately; callers may retry. Separate roots do not
  share a lock.
* Directory descriptors and `O_NOFOLLOW` reject symlinks in every parent component.
  A final symlink is moved/restored as a symlink; its target is not followed.
  Dot components are refused for delete. Root, quarantine, its contents, and
  ancestors of quarantine cannot be deleted.
* Atomic same-filesystem rename preserves inode, content, permissions, ownership,
  timestamps except rename-related ctime, ACLs, xattrs, and hardlink relationships
  as supported by the filesystem. Cross-filesystem moves fail; choose a separate
  quarantine on that filesystem. This avoids incomplete copy-and-delete fallbacks.
* Restore uses the platform atomic no-replace rename and never overwrites an existing
  file, directory, or dangling symlink. Original parents must already exist and
  contain no symlinks. Resolve conflicts yourself, then retry.
* Mount points and trees containing mounts are refused. Purge checks mounts again
  and uses Python's descriptor-based symlink-resistant recursive removal.
* Manifests use an atomic replace and fsync; payload moves and entry removal also
  fsync directories. Unsupported filesystem operations fail closed.

## Recovery and limits

Each entry holds `manifest.json` and `payload`. The manifest records a state:

| State | Meaning / action |
| --- | --- |
| prepared | Move may not have happened. If payload exists, restore can recover it; otherwise inspect the original. Purge refuses. |
| stored | Normal quarantine; restore, or purge after expiration. |
| restoring | Interrupted restore. If payload remains, retry restore; otherwise inspect the original before manually cleaning the record. |
| restored | Payload moved successfully; interrupted record cleanup may remain. Inspect original and clean record manually. |
| purging | Permanent removal started and may be partial. Only retry purge; restore refuses. |

Do not edit manifests casually. Keep original paths and payloads intact during
manual recovery. Failures leave evidence rather than guessing which copy to remove.
The tool does not automatically discard incomplete records or roll back permanent
purge. Disk-full, permissions errors, signals, and unsupported filesystems are
reported, but no filesystem tool can promise recovery after every hardware failure.

Threat model: cooperative processes under the same account, with stable trusted
source parents and private quarantine parents. The descriptor operations prevent
symlink traversal and serialize SafeDelete operations, but a malicious process
with the same UID can modify your files, rename ancestors, replace entries, or
change mounts. Do not use this as an isolation boundary for hostile writable
folders, privileged service input, or attacker-controlled manifests. External
writers are not locked; stop them before deletion. Hardlinked files and open file
descriptors can still change quarantined content. Quarantine is undo storage, not
a backup or immutable snapshot. Secure data erasure is not provided.

## Tests

```bash
./tests/run-native.sh
```

The native runner refuses root and unsupported hosts. `tests/run-linux.sh` remains
available for Linux-only runs. It runs portable state-machine
checks plus real CLI integration exercising confirmation, locking, rename-based
restore, expiration, directory purge, and preservation of a symlink target.

```bash
python3 -m unittest discover -s tests -v
bash -n install.sh bin/safedelete lib/safedelete.sh tests/run-linux.sh tests/run-native.sh
```

The portable checks simulate rename to test logic on other platforms; they do not
validate native atomic-rename behavior. The native integration suite exercises
the actual backend on Linux or macOS; run it on each platform you use.


## Install and Bash help

Run from the extracted project directory on Linux or macOS, as your regular user:

```bash
bash --version
python3 --version  # must be 3.11 or newer
bash install.sh --help
bash install.sh
export PATH="$HOME/.local/bin:$PATH"
safedelete --help
safedelete delete --help
```

The installer copies the CLI and its library into `~/.local/lib/safedelete` and
creates `~/.local/bin/safedelete`. It refuses to overwrite existing installations.
For another destination, use `bash install.sh /absolute/prefix`.
To update an existing copy, use `bash install.sh --upgrade [PREFIX]` (omit `[PREFIX]` for the default). Add the printed PATH command to `~/.bashrc` (Bash) or `~/.zshrc` (zsh) with a text editor to make it persistent. Installation
does not change your shell startup files or replace `rm`.

If Bash or Python is missing, these are common Linux package-manager commands
(package availability depends on your distribution release):

```bash
# Debian / Ubuntu
sudo apt update
sudo apt install bash python3
# Fedora
sudo dnf install bash python3
# Arch Linux
sudo pacman -S bash python
```

Check `python3 --version` afterward. Older distributions may need an OS upgrade
or a supported Python 3.11+ installation. Use sudo only for package management;
run SafeDelete and its installer without sudo.

Useful Bash commands:

| Command | Purpose |
| --- | --- |
| `pwd` | Show the current directory |
| `ls -la` | Show files, including hidden names |
| `cd "$HOME/Documents"` | Change directory |
| `help cd` / `help read` | Read Bash builtin help |
| `command -v safedelete` | Check which installed command will run |
| `printf '%s\n' "$PATH"` | Inspect command search locations |
| `safedelete --help` | See available actions |

Always quote paths: `safedelete delete -- "notes draft.txt"`. Use `--` before a
filename beginning with `-`. Avoid `./name` and `../name` because dot components
are deliberately refused; use `name` or an absolute path. Tab completion can help
enter filenames. Ctrl+C interrupts an operation; inspect `list` before retrying.

Try a disposable file:

```bash
printf 'practice\n' > "$HOME/safedelete-practice.txt"
safedelete delete --ttl 600 -- "$HOME/safedelete-practice.txt"
# Type YES to approve, or any other response to cancel.
safedelete list
safedelete restore PASTE_THE_PRINTED_ID
```

Deletion writes only the ID to stdout so Bash can capture it; progress, recovery
instructions, restoration, and permanent-purge feedback go to stderr. `list`
includes `remaining_seconds` (a snapshot, not a background timer), path, ID,
expiration, and state. Refresh it for a changing countdown:

```bash
watch -n 1 "$HOME/.local/bin/safedelete list"  # optional Linux watch utility
```

After cancellation, run `ls -la -- /absolute/parent` to inspect nearby filenames,
then retry with the intended name. Invalid confirmation cancels without moving
the target; there is no implicit affirmative response.

## Optional automatic expiration cleanup

To permanently purge expired items without a prompt, explicitly run:

```bash
safedelete purge-expired --yes
```

For unattended cleanup, use `crontab -e` and add the following line, replacing
`/home/YOUR_USER` with your actual absolute home path. This authorizes permanent
removal every minute. Cron must be installed and running; it may not be present
in containers or minimal distributions.

```cron
* * * * * /home/YOUR_USER/.local/bin/safedelete purge-expired --yes >> /home/YOUR_USER/.local/share/safedelete-purge.log 2>&1
```

The example uses the default quarantine. If you use another root, insert
`--root /absolute/quarantine` before `purge-expired`. Cleanup happens on the next
successful scheduler run, not at an exact second. Check the log for errors;
remove the line with `crontab -e` to disable automatic removal. Incomplete records
are preserved for inspection. Once permanent purge begins, undo is unavailable.

## Assignment and HCI mapping

| Responsibility | Implementation / observable behavior |
| --- | --- |
| `safe_delete(path)` | Bash `safe_delete -- PATH` / `safedelete delete -- PATH`; validates and confirms before quarantine |
| `undo_delete(id)` | Bash `undo_delete ID` / `safedelete restore ID`; refuses expired entries and destination conflicts |
| `list_deleted()` | Bash `list_deleted` / `safedelete list`; IDs, paths, state, and seconds left |
| `confirm_delete(path)` | Internal Python `confirm`; requires exact YES, otherwise cancels |
| `validate_path(path)` | Internal delete checks, `checked_dir`, and `refuse_mounts`; filesystem operations report permission failures |
| `purge_expired()` | Bash `purge_expired` / `safedelete purge-expired`; exact confirmation or explicit `--yes` |
| `handle_error(code)` | CLI exception handler and exit statuses; explains failure and points to list/help |

Source `lib/safedelete.sh` to use the Bash functions. Validation, confirmation,
and error handling stay inside the engine rather than being separately callable
Bash functions, so callers cannot accidentally bypass the checks by composing them.

| HCI principle | Demonstration |
| --- | --- |
| Error prevention | Protected paths, symlink-parent rejection, no overwrite, confirmation |
| User control and freedom | Cancel confirmation; restore by ID before deadline |
| Visibility of status | Quarantine ID, remaining seconds, explicit stored/restored/purged feedback |
| Feedback | Completion messages and actionable failure messages |
| Consistency | Predictable subcommands, exit statuses, and YES prompts |
| Recognition rather than recall | List displays IDs and original paths; delete prints an undo command |
| Error recovery | Preserve recovery records, refuse collisions, suggest list/help |

Moves use atomic rename: an item is reported as stored after the operation,
without a misleading percentage bar for an indivisible move. A successful move
preserves the item in quarantine; this is not a separate backup copy.

Before and after confirmation, SafeDelete checks accessible Linux `/proc` process
executables, working directories, and file descriptors. macOS uses its built-in
`/usr/sbin/lsof`, including recursive directory inspection, with a 15-second
timeout; an incomplete check refuses the move. Final symlinks are moved without
checking their targets. Detected use blocks the
move and identifies the PID. This is best effort: permissions can hide processes
and another process can open the item after the check. Stop programs using the
file or directory before deleting it. If available, `lsof -- /absolute/file`
can assist inspection; it is not a guarantee against another process opening it
later. Process exclusion would require cooperation from the writing application.


## Make PATH persistent

After the default installation, run the commands for your shell **once** so
`safedelete` is available in future terminal sessions. If the export line already
exists in the file, skip the `echo` command to avoid duplicates.

**Bash on Linux:**

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Bash in macOS Terminal (normally a login shell):**

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bash_profile
source ~/.bash_profile
```

**zsh (the default macOS shell):**

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Check that the command is available:

```bash
command -v safedelete
safedelete --help
```

For a custom installation prefix, replace `$HOME/.local/bin` with that prefix's
`bin` directory. Bash login shells read `~/.bash_profile` (or `~/.bash_login`,
or `~/.profile`, using the first existing file), while interactive non-login Bash
shells read `~/.bashrc`. If your setup uses a different startup file, put the PATH
line there. These commands update your shell configuration; the installer only
prints guidance and does not edit it automatically.

## macOS Terminal setup

The included CLI works from zsh (the default macOS shell) and Bash. It runs with
Apple's bundled Bash 3.2; installing a newer Bash is unnecessary. The Bash library
functions must be sourced from Bash scripts or a Bash session.

```bash
python3 --version  # requires 3.11+
# If needed, with Homebrew already installed:
brew install python
bash install.sh
export PATH="$HOME/.local/bin:$PATH"
safedelete --help
```

Alternatively, install Python 3.11+ from [python.org](https://www.python.org/downloads/macos/).
The installer detects missing/older Python and prints installation guidance; it
does not install system packages automatically. Add the PATH line once to
`~/.zshrc` for zsh or `~/.bashrc` for Bash (login Bash may use `~/.bash_profile`).

macOS uses atomic `renameatx_np(..., RENAME_EXCL)` for no-overwrite moves and the
native `getmntinfo` mount table. Filesystems lacking exclusive rename are refused.
This is private quarantine storage, separate from Finder Trash. Existing
symlink-parent safeguards still apply: use `/private/tmp/...` rather than the
`/tmp` symlink, for example. macOS privacy controls may require granting your
terminal access to the target folder. Recursive active-file checks can take time
for large directories and cannot see every process. The cron example requires
cron configuration on macOS too; no background job is installed automatically.

Validation on the development Mac: 23 tests passed, including native no-overwrite
rename, CLI quarantine/restore/purge, symlink preservation, open-file detection,
mount inspection, and installation with a prefix containing spaces. Linux must
still be checked on a Linux host.


## Upgrade or uninstall

An installed copy does not automatically pick up edits in the downloaded project.
From the updated project folder, run:

```bash
bash install.sh --upgrade
```

For a custom installation, append the original prefix:
`bash install.sh --upgrade "$HOME/tools"`. Close other SafeDelete commands before
upgrading or uninstalling. If you sourced the Bash library, source it again or
open a new Bash session after upgrading.

To uninstall the default installation:

```bash
bash "$HOME/.local/lib/safedelete/uninstall.sh"
# Or, from the downloaded project folder:
bash uninstall.sh
```

Type **YES** to confirm. Use `bash uninstall.sh /absolute/prefix` for a custom
installation; `--yes` explicitly skips the prompt for scripts. Upgrade and
uninstall validate the installed files and refuse modified launchers or unexpected
content. Quarantine (including recoverable items), logs, PATH settings, and cron
entries are preserved. Remove any SafeDelete cron entries yourself. Reinstall
to restore quarantined items while their recovery windows are still open.
