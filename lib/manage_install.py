"""Install/upgrade/remove only a recognized SafeDelete installation."""
import argparse
import os
from pathlib import Path
import shutil
import sys
import tempfile

FILES = ('bin/safedelete', 'lib/engine.py', 'lib/safedelete.sh',
         'lib/manage_install.py', 'README.md', 'QUICK_REFERENCE.md', 'LICENSE', 'uninstall.sh')


def launcher_text(destination):
    # Single quotes work in Bash and preserve spaces and shell metacharacters.
    quoted = "'" + str(destination / 'bin/safedelete').replace("'", "'\"'\"'") + "'"
    return '#!/usr/bin/env bash\nexec ' + quoted + ' "$@"\n'


def validate(destination, launcher):
    if destination.is_symlink() or launcher.is_symlink():
        raise ValueError('Refusing symlink installation destinations')
    if not destination.is_dir() or not launcher.is_file():
        raise ValueError('A complete existing installation is required')
    # Accept the original installer launcher as well as the current one.
    import subprocess
    original = subprocess.check_output(
        ['/bin/bash', '-c', 'printf \'#!/usr/bin/env bash\\nexec %q "$@"\\n\' "$1"',
         'launcher', str(destination / 'bin/safedelete')], text=True)
    if launcher.read_text() not in (original, launcher_text(destination)):
        raise ValueError('Launcher was modified; refusing to overwrite/remove it')
    allowed = set(FILES) | {'bin', 'lib'}
    for path in destination.rglob('*'):
        if path.is_symlink() or str(path.relative_to(destination)) not in allowed:
            raise ValueError('Unexpected installation content; preserved for manual inspection: ' + str(path))
    for name in ('bin/safedelete', 'lib/engine.py', 'lib/safedelete.sh'):
        if not (destination / name).is_file():
            raise ValueError('Unrecognized installation; missing ' + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'upgrade', 'uninstall'))
    parser.add_argument('prefix')
    parser.add_argument('--source')
    parser.add_argument('--yes', action='store_true')
    args = parser.parse_args()
    if os.geteuid() == 0:
        raise ValueError('Run as your regular user, without sudo')
    prefix = Path(args.prefix)
    if not prefix.is_absolute():
        raise ValueError('PREFIX must be absolute')
    destination = prefix / 'lib/safedelete'
    launcher = prefix / 'bin/safedelete'
    if args.action != 'install':
        validate(destination, launcher)
    elif os.path.lexists(destination) or os.path.lexists(launcher):
        raise ValueError('Installation exists; run bash install.sh --upgrade [PREFIX]')
    if args.action == 'uninstall':
        print('Remove SafeDelete from ' + repr(str(prefix)) + '? Quarantined files will be preserved.')
        if not args.yes:
            if not sys.stdin.isatty() or input('Type YES to uninstall: ') != 'YES':
                raise ValueError('Cancelled; nothing removed')
        validate(destination, launcher)
        launcher.unlink()
        shutil.rmtree(destination)
        print('SafeDelete uninstalled. Quarantine and shell configuration were preserved.')
        print('Remove any SafeDelete cron entries manually; reinstall to recover quarantined items.')
        return
    source = Path(args.source).resolve()
    if source == destination.resolve():
        raise ValueError('Run installation from a separate downloaded project folder')
    (prefix / 'lib').mkdir(parents=True, exist_ok=True)
    launcher.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.safedelete-stage-', dir=prefix / 'lib') as staging:
        staged = Path(staging) / 'safedelete'
        staged.mkdir()
        for name in FILES:
            target = staged / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / name, target)
        staged_launcher = Path(staging) / 'launcher'
        staged_launcher.write_text(launcher_text(destination))
        staged_launcher.chmod(0o755)
        backup = Path(staging) / 'previous'
        if args.action == 'upgrade':
            validate(destination, launcher)
            destination.rename(backup)
        try:
            staged.rename(destination)
            os.replace(staged_launcher, launcher)
        except BaseException:
            if destination.exists():
                shutil.rmtree(destination)
            if backup.exists():
                backup.rename(destination)
            raise
    print('SafeDelete ' + ('upgraded' if args.action == 'upgrade' else 'installed') + '. Quarantine preserved.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as exc:
        print('safedelete setup: ' + str(exc), file=sys.stderr)
        sys.exit(1)
