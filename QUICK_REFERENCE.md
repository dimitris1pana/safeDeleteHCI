# SafeDelete — Quick Reference

## Install once

Requires **Linux or macOS, Bash 3.2+, and Python 3.11+**. Run as your regular user.
From the downloaded or cloned SafeDelete project folder:

```bash
bash install.sh
export PATH="$HOME/.local/bin:$PATH"
safedelete --help
```

This is a local, one-command installation, similar to installing a command-line
package. It installs the command and Bash library under `~/.local` and prints
setup instructions. No npm or pip is required; the project is not currently
published to a package registry. After installation, you can run `safedelete`
from any directory and remove the downloaded project folder.

To keep the command available in future Bash terminals, add this line **once**
to `~/.bashrc` for Bash or `~/.zshrc` for macOS’s default zsh:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then open a new terminal. macOS’s bundled Bash is sufficient; the command also
works from zsh. Login Bash may use `~/.bash_profile` instead.

On macOS, install Python if needed (requires Homebrew already installed):

```bash
brew install python
python3 --version
```

Or use the [Python macOS installer](https://www.python.org/downloads/macos/).
SafeDelete’s installer stops with guidance if Python 3.11+ is missing.

Missing prerequisites on Debian/Ubuntu?

```bash
sudo apt update
sudo apt install bash python3
python3 --version  # must be 3.11 or newer
```

Run the installer and SafeDelete without sudo. For other distributions and
additional setup details, see [README.md](README.md#install-and-bash-help).

## Use immediately

```bash
# Delete with the default 24-hour recovery window
safedelete delete -- "report.txt"

# Or choose a 10-minute recovery window (seconds)
safedelete delete --ttl 600 -- "old folder"

# Find IDs, original paths, and remaining_seconds
safedelete list

# Undo before the deadline; replace ID with the printed deletion ID
safedelete restore ID

# Permanently remove expired items
safedelete purge-expired

# Help for any command
safedelete --help
safedelete delete --help
```

Terminal output, including help, pauses briefly between lines (0.06 seconds).
Piped or captured output stays immediate. Adjust or disable the delay:

```bash
SAFEDELETE_OUTPUT_DELAY=0.1 safedelete --help
SAFEDELETE_OUTPUT_DELAY=0 safedelete --help
```

Type **YES** when prompted to approve. Any other response cancels. Always quote
paths containing spaces; `--` also handles filenames beginning with `-`. Use
`name` or an absolute path rather than `./name` or `../name`.

Delete prints an ID and an undo command. List shows a snapshot of time left.
Restore never overwrites an existing destination. Expired items cannot be
restored; permanent cleanup runs only when requested or explicitly scheduled.
Stop programs using a file before deleting it; process detection is best effort.

## Add as a Bash library

After the default installation, source the library in your Bash script or Bash terminal (run `bash` first if using zsh):

```bash
source "$HOME/.local/lib/safedelete/lib/safedelete.sh"
safe_delete -- "$HOME/report.txt"
list_deleted
undo_delete ID
purge_expired
```

For a script that deliberately skips confirmation:

```bash
source "$HOME/.local/lib/safedelete/lib/safedelete.sh"
if id=$(safe_delete --yes --ttl 600 -- "$HOME/report.txt"); then
    undo_delete --yes "$id"
fi
```

`--yes` explicitly authorizes the action. Use it carefully, especially for purge.

## Installation options and troubleshooting

```bash
# Install under a custom absolute prefix
bash install.sh "$HOME/tools"
export PATH="$HOME/tools/bin:$PATH"

# Check which command your shell finds
command -v safedelete

# Run the default installation directly if PATH is not set
"$HOME/.local/bin/safedelete" --help
```

An existing installation is preserved: the installer refuses to overwrite it.
Use `bash install.sh --upgrade` to update the installed copy, or choose another prefix. Quarantine defaults to
`~/.local/share/safedelete`; keep it intact while items remain recoverable.
For optional automatic cleanup, see [the cron instructions](README.md#optional-automatic-expiration-cleanup).


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
