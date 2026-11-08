# SafeDelete project structure

This guide explains the source project, the installed application, and the
quarantine data. They live in separate locations and serve different purposes.

## 1. Source project

```text
safedelete/
├── README.md
├── QUICK_REFERENCE.md
├── PROJECT_STRUCTURE.md
├── DESIGN.md
├── TODO.md
├── LICENSE
├── .gitignore
├── install.sh
├── uninstall.sh
├── bin/
│   └── safedelete
├── lib/
│   ├── safedelete.sh
│   ├── engine.py
│   └── manage_install.py
└── tests/
    ├── test_safedelete.py
    ├── run-native.sh
    └── run-linux.sh
```

### Files in the project root

| File | What it does | When to use or edit it |
| --- | --- | --- |
| `README.md` | Main documentation: requirements, commands, safeguards, recovery limits, installation, persistent PATH, upgrade, uninstall, and HCI mapping. | Read for full usage and behavior details. Update when features change. |
| `QUICK_REFERENCE.md` | Short installation and everyday command guide, including Bash library usage. | Start here to install and try SafeDelete quickly. |
| `PROJECT_STRUCTURE.md` | This guide to files, folders, and application flow. | Read before navigating the source or choosing a contribution. |
| `DESIGN.md` | Educational HCI design document, including objectives and hierarchical task analysis. | Study the interaction design. It describes design intent; check the implementation and README for current behavior. |
| `TODO.md` | Student PR proposals with HCI concepts, acceptance criteria, safety requirements, and contribution guidance. | Choose a task or propose an improvement. Unchecked tasks are proposals, not implemented features. |
| `LICENSE` | Terms for using, modifying, and distributing the project. | Read before redistributing or reusing the code. |
| `.gitignore` | Tells Git to ignore generated Python caches and compiled Python files. | Update when additional generated files need excluding. It does not delete existing files. |
| `install.sh` | Bash setup entry point. Checks OS, user privileges, Bash and Python requirements; delegates installation or upgrade to Python; prints setup and usage instructions. | Run `bash install.sh`, or `bash install.sh --upgrade` for an existing installation. |
| `uninstall.sh` | Bash removal entry point. Accepts a prefix and optional `--yes`, then delegates removal to Python. | Run `bash uninstall.sh`. Confirmation is required unless explicitly skipped. |

### `bin/` — terminal entry point

| File | What it does |
| --- | --- |
| `bin/safedelete` | Executable Bash script. Finds the project's own `lib/safedelete.sh`, sources it, and forwards command arguments to the `safedelete` function. |

From the source folder, run `./bin/safedelete --help`. This uses the downloaded
source, which may differ from an older installed copy.

### `lib/` — reusable functions and implementation

| File | What it does |
| --- | --- |
| `lib/safedelete.sh` | Bash library. Defines wrapper functions and calls the Python engine. It locates the engine relative to the library rather than relying on the current working directory. |
| `lib/engine.py` | Implements command parsing, terminal output, path validation, confirmation, quarantine, restore, listing, expiration, and permanent purge. Contains the native Linux/macOS filesystem backends and quarantine locking. |
| `lib/manage_install.py` | Implements installation, upgrade, and uninstall. Copies an explicit set of application files, generates the installed launcher, validates existing installations, stages upgrades, and removes recognized application files while preserving quarantine. |

The Bash library exposes these functions:

| Function | Command it calls |
| --- | --- |
| `safedelete` | Python engine with the supplied arguments |
| `safedelete_delete` / `safe_delete` | `delete` |
| `safedelete_restore` / `undo_delete` | `restore` |
| `safedelete_list` / `list_deleted` | `list` |
| `safedelete_purge` | `purge` for one ID |
| `safedelete_purge_expired` / `purge_expired` | `purge-expired` |

Source the library from Bash to use these functions. The installed terminal
command can also be launched from zsh; sourcing the Bash library is intended for
Bash sessions and scripts.

Inside `engine.py`, responsibilities are grouped as follows:

| Code | Responsibility |
| --- | --- |
| `SafeError` | Represents an expected application failure with an explanatory message. |
| `PacedOutput`, `configure_output` | Add configurable pauses between terminal output lines; leave captured output immediate. |
| `checked_dir`, `exists` | Open/check filesystem locations using directory descriptors and avoid following symlink parents. |
| `save`, `read` | Write and read each quarantined item's JSON metadata. |
| `move` | Perform native atomic no-overwrite moves: Linux `renameat2` or macOS `renameatx_np`. |
| `mac_mounts`, `refuse_mounts` | Inspect mount locations and refuse mounted directories or trees containing mounts. |
| `refuse_active_file` | Check for detectable process use through Linux `/proc` or macOS `lsof`. This is best effort, not a lock against other programs. |
| `confirm`, `valid_id` | Require explicit approval and validate deletion ID syntax. |
| `entry`, `clean_entry` | Open an entry safely and remove its metadata/directory after an operation completes. |
| `run` | Dispatch and execute delete, list, restore, purge, or purge-expired. |
| `main` | Parse arguments, check requirements, open the quarantine, and acquire its lock. |
| Script exception handlers | Print failure/recovery guidance and return an exit status. |

### `tests/` — verification

| File | What it does |
| --- | --- |
| `tests/test_safedelete.py` | Python unittest suite. Checks validation, cancellation requirements, expiration, metadata, interrupted operations, conflicts, and symlinks. Includes actual platform integration checks for filesystem moves, CLI lifecycle, installation/upgrade/uninstall, active files, and macOS mounts. Some logic tests simulate moves; native integration tests use the actual backend. |
| `tests/run-native.sh` | Runs the suite on Linux or macOS as a regular user. Recommended test entry point. |
| `tests/run-linux.sh` | Runs the same suite but refuses non-Linux hosts and root. Useful when specifically validating Linux. |

Run `./tests/run-native.sh` from the source project. A passing macOS run does not
establish that the Linux backend also passes, or vice versa.

### Generated local files

You may also see these in a working folder; they are not application source:

| File or folder | Meaning |
| --- | --- |
| `lib/__pycache__/`, `tests/__pycache__/` | Python-generated bytecode caches. Ignored by the current `.gitignore`; not needed in a PR or installation. |
| `*.pyc` inside those folders | Cached compiled Python modules. The filename can include the Python version. |
| `.DS_Store` | macOS Finder metadata. Not used by SafeDelete. |

## 2. How a command runs

```text
User types: safedelete delete -- "report.txt"
    → installed launcher in PREFIX/bin/
    → application bin/safedelete
    → Bash function in lib/safedelete.sh
    → Python lib/engine.py
    → validation and explicit confirmation
    → atomic move into quarantine and metadata update
    → deletion ID and recovery instructions
```

Calling `./bin/safedelete` from the source skips the installed launcher. Calling
a sourced function such as `safe_delete` starts at the Bash library step. All
routes delegate deletion safeguards to the same Python engine.

Installation takes a different route:

```text
bash install.sh [--upgrade] [PREFIX]
    → prerequisite checks in install.sh
    → lib/manage_install.py
    → staged application files and generated launcher
    → printed PATH instructions
```

## 3. Installed application

The default prefix is `~/.local`. A custom prefix replaces that part of the paths.
The current installer copies only the files listed in `manage_install.py`:

```text
~/.local/
├── bin/
│   └── safedelete                 # Generated launcher; points to the application
└── lib/
    └── safedelete/
        ├── README.md
        ├── QUICK_REFERENCE.md
        ├── LICENSE
        ├── uninstall.sh
        ├── bin/
        │   └── safedelete
        └── lib/
            ├── safedelete.sh
            ├── engine.py
            └── manage_install.py
```

`install.sh`, tests, `DESIGN.md`, `TODO.md`, and this structure guide remain in
the downloaded source project; they are not copied by the current installer.
Upgrade from an updated source folder using `bash install.sh --upgrade`.

PATH makes the launcher discoverable. Shell configuration files such as
`~/.zshrc`, `~/.bashrc`, and `~/.bash_profile` belong to the user's environment,
not this application folder. The installer prints guidance and does not edit them.

## 4. Quarantine and runtime data

The default quarantine is separate from installed code:

```text
~/.local/share/safedelete/
├── .lock
└── <32-character deletion ID>/
    ├── manifest.json
    └── payload
```

| Runtime item | Purpose |
| --- | --- |
| `.lock` | Used for an exclusive advisory lock so SafeDelete operations sharing this quarantine do not run concurrently. The file may remain after the lock is released. |
| ID directory | Groups one deleted item with its metadata. Multiple deletions create separate ID directories. |
| `manifest.json` | Stores the original absolute path, creation/expiration timestamps, operation state, version, device, and inode information. |
| `payload` | The moved file, directory, or symlink. A deleted directory keeps its contents inside this directory payload. |
| `.manifest-…` (temporary) | Temporary metadata file used while saving a manifest; normally removed after the atomic update. An interruption can leave temporary data requiring inspection. |

The root can be changed with `--root` or `SAFEDELETE_ROOT`. It must satisfy
quarantine permissions and filesystem checks. An interrupted operation may leave
metadata without a payload; see the README recovery states before retrying.

The optional cron example writes `~/.local/share/safedelete-purge.log`, outside
the quarantine. It is created only if you configure that redirection; the
application does not install cron jobs automatically.

Uninstall removes the recognized application and launcher. It preserves
quarantine, logs, shell configuration, and cron entries. Do not manually delete
quarantine if you still need its recoverable items.

## 5. Where to make a student contribution

- Help text, prompts, colors, and pacing: start in `lib/engine.py`.
- Bash function names and wrappers: start in `lib/safedelete.sh`.
- Prerequisite messages and setup guidance: start in `install.sh`.
- Upgrade or removal behavior: start in `lib/manage_install.py` and `uninstall.sh`.
- User instructions: edit `README.md` or `QUICK_REFERENCE.md`.
- HCI analysis and proposed exercises: read `DESIGN.md` and `TODO.md`.
- Behavior verification: add focused checks in `tests/test_safedelete.py`.

Keep each PR focused and follow the safety requirements in [TODO.md](TODO.md).
