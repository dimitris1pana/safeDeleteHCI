#!/usr/bin/env python3
"""SafeDelete filesystem engine. Never run with elevated privileges."""
import argparse
import contextlib
import ctypes
import errno
import fcntl
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import uuid

class SafeError(Exception):
    pass

class PacedOutput:
    """Flush terminal output a line at a time; leave prompts responsive."""
    def __init__(self, stream, delay):
        self.stream = stream
        self.delay = delay

    def write(self, text):
        for part in text.splitlines(keepends=True):
            self.stream.write(part)
            self.stream.flush()
            if part.endswith('\n'):
                time.sleep(self.delay)
        return len(text)

    def __getattr__(self, name):
        return getattr(self.stream, name)

def configure_output():
    try:
        delay = float(os.environ.get('SAFEDELETE_OUTPUT_DELAY', '0.06'))
        if not 0 <= delay <= 1:
            delay = 0.06
    except ValueError:
        delay = 0.06
    if delay:
        for name in ('stdout', 'stderr'):
            stream = getattr(sys, name)
            if stream.isatty():
                setattr(sys, name, PacedOutput(stream, delay))

def checked_dir(path, create=False):
    """Walk with directory descriptors; never follow a symlink component."""
    path = os.path.abspath(path)
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.split('/')[1:]:
            if not part:
                continue
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise

def save(fd, record):
    tmp = '.manifest-' + uuid.uuid4().hex
    f = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    try:
        with os.fdopen(f, 'w') as out:
            json.dump(record, out, ensure_ascii=True)
            out.flush()
            os.fsync(out.fileno())
        os.rename(tmp, 'manifest.json', src_dir_fd=fd, dst_dir_fd=fd)
        os.fsync(fd)
    finally:
        try:
            os.unlink(tmp, dir_fd=fd)
        except FileNotFoundError:
            pass

def read(fd):
    f = os.open('manifest.json', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
    with os.fdopen(f) as stream:
        r = json.load(stream)
    if r.get('version') != 1 or r.get('state') not in ('prepared', 'stored', 'restoring', 'purging', 'restored'):
        raise SafeError('Invalid manifest; manual inspection required')
    if not isinstance(r.get('original'), str) or not os.path.isabs(r['original']):
        raise SafeError('Invalid original path')
    if not isinstance(r.get('expires'), (int, float)):
        raise SafeError('Invalid expiration')
    return r

def exists(fd, name):
    try:
        return os.stat(name, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        return None

def move(srcfd, src, dstfd, dst):
    # Both backends atomically refuse existing destinations, including symlinks.
    libc = ctypes.CDLL(None, use_errno=True)
    symbol, flags = ('renameatx_np', 4) if sys.platform == 'darwin' else ('renameat2', 1)
    fn = getattr(libc, symbol, None)
    if fn is None:
        raise SafeError(symbol + ' is required; no unsafe fallback is used')
    fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    fn.restype = ctypes.c_int
    if fn(srcfd, os.fsencode(src), dstfd, os.fsencode(dst), flags) != 0:
        e = ctypes.get_errno()
        raise OSError(e, os.strerror(e))
    os.fsync(srcfd)
    os.fsync(dstfd)

def mac_mounts():
    # Darwin's 64-bit statfs ABI (sys/mount.h); no parsing of human-readable paths.
    class StatFS(ctypes.Structure):
        _fields_ = [('bsize', ctypes.c_uint32), ('iosize', ctypes.c_int32),
                    ('counts', ctypes.c_uint64 * 5), ('fsid', ctypes.c_int32 * 2),
                    ('owner', ctypes.c_uint32), ('type', ctypes.c_uint32),
                    ('flags', ctypes.c_uint32), ('subtype', ctypes.c_uint32),
                    ('fstype', ctypes.c_char * 16), ('mounted_on', ctypes.c_char * 1024),
                    ('mounted_from', ctypes.c_char * 1024), ('reserved', ctypes.c_uint32 * 8)]
    libc = ctypes.CDLL(None, use_errno=True)
    fn = getattr(libc, 'getmntinfo$INODE64', None) or libc.getmntinfo
    mounts = ctypes.POINTER(StatFS)()
    fn.argtypes = [ctypes.POINTER(ctypes.POINTER(StatFS)), ctypes.c_int]
    fn.restype = ctypes.c_int
    count = fn(ctypes.byref(mounts), 2)  # MNT_NOWAIT
    if count <= 0:
        raise SafeError('Unable to inspect mounted filesystems; refusing directory operation')
    return [os.fsdecode(mounts[i].mounted_on) for i in range(count)]

def refuse_mounts(path):
    if sys.platform == 'darwin':
        for mount in mac_mounts():
            if mount == path or mount.startswith(path + '/'):
                raise SafeError('Mount points and directories containing mounts are refused')
        return
    with open('/proc/self/mountinfo') as mounts:
        for line in mounts:
            raw = line.split()[4]
            mount = re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), raw)
            if mount == path or mount.startswith(path + '/'):
                raise SafeError('Mount points and directories containing mounts are refused')

def refuse_active_file(path, before):
    """Best-effort process check; visibility is not a process lock."""
    if stat.S_ISLNK(before.st_mode):
        return  # Moving the link does not move the file a process has open.
    if sys.platform == 'darwin':
        command = ['/usr/sbin/lsof', '-t']
        command += ['+D', path] if stat.S_ISDIR(before.st_mode) else ['--', path]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=15)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SafeError('Cannot check active files with lsof; close applications and retry') from exc
        if result.stdout.strip():
            raise SafeError('Item is in use; close the file or stop its program, then retry')
        if result.returncode not in (0, 1) or result.stderr.strip():
            raise SafeError('lsof could not complete the active-file check; check permissions and retry')
        return
    if not os.path.isdir('/proc'):
        return
    directory = stat.S_ISDIR(before.st_mode)
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        process = '/proc/' + pid
        try:
            refs = [process + '/exe', process + '/cwd']
            refs += [process + '/fd/' + name for name in os.listdir(process + '/fd')]
        except (PermissionError, FileNotFoundError, ProcessLookupError):
            continue
        for ref in refs:
            try:
                target = os.readlink(ref)
                info = os.stat(ref)
            except (PermissionError, FileNotFoundError, ProcessLookupError):
                continue
            if ((info.st_dev, info.st_ino) == (before.st_dev, before.st_ino)
                    or directory and target.startswith(path + '/')):
                raise SafeError(f'Item is in use by process {pid}; close the file or stop the program, then retry')

def confirm(args, action):
    if args.yes:
        return
    if not sys.stdin.isatty():
        raise SafeError('Confirmation requires a terminal; pass --yes explicitly for scripts')
    if input(action + '\nType YES to continue: ') != 'YES':
        raise SafeError('Cancelled')

def valid_id(value):
    if not re.fullmatch('[0-9a-f]{32}', value):
        raise SafeError('Invalid entry ID')
    return value

@contextlib.contextmanager
def entry(rootfd, ident):
    valid_id(ident)
    fd = os.open(ident, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=rootfd)
    try:
        yield fd
    finally:
        os.close(fd)

def clean_entry(rootfd, ident, fd):
    os.unlink('manifest.json', dir_fd=fd)
    os.rmdir(ident, dir_fd=rootfd)
    os.fsync(rootfd)

def run(args, root, rootfd):
    if args.command == 'purge-expired':
        # Reuse the per-entry checks under the same quarantine lock.
        eligible = []
        for ident in sorted(os.listdir(rootfd)):
            if re.fullmatch('[0-9a-f]{32}', ident):
                with entry(rootfd, ident) as fd:
                    r = read(fd)
                    if time.time() >= r['expires'] and r['state'] in ('stored', 'purging'):
                        eligible.append(ident)
        if not eligible:
            print('No expired items to purge.', file=sys.stderr)
            return
        confirm(args, 'Permanently purge these expired IDs: ' + ', '.join(eligible) + '?')
        for ident in eligible:
            run(argparse.Namespace(command='purge', id=ident, yes=True), root, rootfd)
        return
    if args.command == 'delete':
        if args.ttl < 1 or args.ttl > 315360000:
            raise SafeError('TTL must be 1..315360000 seconds')
        # Refuse ambiguous dot components before normalization.
        if any(p in ('.', '..') for p in args.path.split('/')):
            raise SafeError('Dot path components are refused')
        path = os.path.abspath(args.path.rstrip('/') or '/')
        if path == '/' or path == root or root.startswith(path + '/') or path.startswith(root + '/'):
            raise SafeError('Refusing root, quarantine, its contents, or an ancestor')
        parent, name = os.path.split(path)
        pfd = checked_dir(parent)
        try:
            before = os.stat(name, dir_fd=pfd, follow_symlinks=False)
            if before.st_dev != os.fstat(rootfd).st_dev:
                raise SafeError('Cross-filesystem move refused; choose a quarantine on the source filesystem')
            if stat.S_ISDIR(before.st_mode):
                refuse_mounts(path)
            refuse_active_file(path, before)
            confirm(args, 'Quarantine ' + repr(path) + '?')
            refuse_active_file(path, before)
            ident = uuid.uuid4().hex
            os.mkdir(ident, 0o700, dir_fd=rootfd)
            with entry(rootfd, ident) as fd:
                r = dict(version=1, original=path, expires=time.time()+args.ttl,
                         created=time.time(), state='prepared', device=before.st_dev, inode=before.st_ino)
                save(fd, r)
                # If interrupted, prepared + payload is recoverable with restore.
                move(pfd, name, fd, 'payload')
                r['state'] = 'stored'
                save(fd, r)
            print(ident)
            print(f'Stored {path!r}. Recovery time: {args.ttl} seconds. '
                  f'Undo: safedelete restore {ident}', file=sys.stderr)
        finally:
            os.close(pfd)
    elif args.command == 'list':
        for ident in sorted(os.listdir(rootfd)):
            if re.fullmatch('[0-9a-f]{32}', ident):
                with entry(rootfd, ident) as fd:
                    r = read(fd)
                    r.update(id=ident, payload_present=exists(fd, 'payload') is not None,
                             expired=time.time() >= r['expires'],
                             remaining_seconds=max(0, int(r['expires'] - time.time())))
                    print(json.dumps(r, ensure_ascii=True))
    else:
        ident = valid_id(args.id)
        with entry(rootfd, ident) as fd:
            r = read(fd)
            payload = exists(fd, 'payload')
            if args.command == 'restore':
                if time.time() >= r['expires']:
                    raise SafeError('Recovery deadline passed; restore is unavailable. Use list to inspect the entry')
                if r['state'] == 'purging':
                    raise SafeError('Purge has started; partial data cannot be restored safely')
                if payload is None:
                    raise SafeError('No payload; inspect original path and manifest before manual recovery')
                parent, name = os.path.split(r['original'])
                pfd = checked_dir(parent)
                try:
                    if exists(pfd, name) is not None:
                        raise SafeError('Restore destination exists; refusing overwrite')
                    confirm(args, 'Restore to ' + repr(r['original']) + '?')
                    if time.time() >= r['expires']:
                        raise SafeError('Recovery deadline passed while waiting for confirmation')
                    r['state'] = 'restoring'
                    save(fd, r)
                    move(fd, 'payload', pfd, name)
                    r['state'] = 'restored'
                    save(fd, r)
                finally:
                    os.close(pfd)
                clean_entry(rootfd, ident, fd)
                print('Restored ' + repr(r['original']), file=sys.stderr)
            else:
                if time.time() < r['expires']:
                    raise SafeError('Entry has not expired')
                if r['state'] not in ('stored', 'purging'):
                    raise SafeError('Incomplete operation; inspect manually before purge')
                confirm(args, 'Permanently purge entry ' + ident + '?')
                r['state'] = 'purging'
                save(fd, r)
                if payload is not None:
                    if stat.S_ISDIR(payload.st_mode):
                        if not shutil.rmtree.avoids_symlink_attacks:
                            raise SafeError('This Python lacks symlink-safe recursive deletion')
                        refuse_mounts(os.path.join(root, ident, 'payload'))
                        shutil.rmtree('payload', dir_fd=fd)
                    else:
                        os.unlink('payload', dir_fd=fd)
                clean_entry(rootfd, ident, fd)
                print('Permanently purged ' + ident, file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(prog='safedelete', description=__doc__, epilog=
        'Examples: safedelete delete --ttl 3600 -- "report.txt"; '
        'safedelete list; safedelete restore ID. '
        'Quote paths with spaces. Use COMMAND --help for details. '
        'Cancel confirmation with any response other than YES. See README.md for installation and Bash help.')
    parser.add_argument('--root', default=os.environ.get('SAFEDELETE_ROOT', os.path.expanduser('~/.local/share/safedelete')))
    sub = parser.add_subparsers(dest='command', required=True)
    delete = sub.add_parser('delete', help='Quarantine one file or directory with timed undo')
    delete.add_argument('--ttl', type=int, default=os.environ.get('SAFEDELETE_TTL', '86400'))
    delete.add_argument('--yes', action='store_true')
    delete.add_argument('path')
    sub.add_parser('list', help='Show IDs, escaped paths, state, and remaining_seconds as JSON lines')
    expired = sub.add_parser('purge-expired', help='Permanently remove expired stored entries (asks for confirmation)')
    expired.add_argument('--yes', action='store_true', help='Explicitly authorize unattended permanent removal')
    for command in ('restore', 'purge'):
        p = sub.add_parser(command, help=('Undo before the deadline' if command == 'restore' else 'Permanently remove one expired entry'))
        p.add_argument('--yes', action='store_true')
        p.add_argument('id')
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        raise SafeError('Python 3.11 or newer is required')
    if sys.platform not in ('linux', 'darwin'):
        raise SafeError('SafeDelete requires Linux or macOS')
    if os.geteuid() == 0:
        raise SafeError('Do not run SafeDelete as root')
    root = os.path.abspath(args.root)
    fd = checked_dir(root, create=True)
    try:
        s = os.fstat(fd)
        if s.st_uid != os.geteuid() or stat.S_IMODE(s.st_mode) != 0o700:
            raise SafeError('Quarantine must be owned by you with mode 0700')
        lock = os.open('.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=fd)
        try:
            ls = os.fstat(lock)
            if not stat.S_ISREG(ls.st_mode) or ls.st_uid != os.geteuid() or ls.st_nlink != 1:
                raise SafeError('Unsafe lock file')
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            run(args, root, fd)
        finally:
            os.close(lock)
    finally:
        os.close(fd)

if __name__ == '__main__':
    configure_output()
    try:
        main()
    except KeyboardInterrupt:
        print('safedelete: interrupted; inspect list before retrying', file=sys.stderr)
        sys.exit(130)
    except (SafeError, OSError, ValueError, KeyError, TypeError) as exc:
        print('safedelete: ' + str(exc), file=sys.stderr)
        print('Check the path, permissions, and entry ID with safedelete list. '
              'Use safedelete --help for commands; inspect list before retrying a failed operation.', file=sys.stderr)
        sys.exit(1)
