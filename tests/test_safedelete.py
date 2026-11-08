import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('engine', BASE / 'lib/engine.py')
e = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e)

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.root = self.base / 'quarantine'
        self.root.mkdir(mode=0o700)
        self.fd = e.checked_dir(str(self.root))
        self.source = self.base / 'some file'
        self.source.write_text('hello')
    def tearDown(self):
        os.close(self.fd)
        self.tmp.cleanup()
    def call(self, command, **kwargs):
        args = type('Args', (), dict(command=command, yes=True, ttl=60, path=str(self.source), **kwargs))()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            e.run(args, str(self.root), self.fd)
        return out.getvalue().strip()
    def portable_move(self, sfd, src, dfd, dst):
        if e.exists(dfd, dst) is not None:
            raise FileExistsError(dst)
        os.rename(src, dst, src_dir_fd=sfd, dst_dir_fd=dfd)
    def test_id_validation(self):
        for ident in ('../x', '', 'a'*31, 'A'*32, '/tmp'):
            with self.assertRaises(e.SafeError): e.valid_id(ident)
    def test_symlink_parent_refused(self):
        link = self.base / 'link'
        link.symlink_to(self.root)
        with self.assertRaises(OSError): e.checked_dir(str(link))
    def test_quarantine_refused(self):
        self.source = self.root
        with self.assertRaises(e.SafeError): self.call('delete')
    def test_dot_components_refused(self):
        self.source = str(self.base) + '/../oops'
        with self.assertRaises(e.SafeError): self.call('delete')
    def test_missing_source(self):
        self.source.unlink()
        with self.assertRaises(FileNotFoundError): self.call('delete')
    def test_active_file_refused(self):
        before = self.source.stat()
        with patch.object(e.sys, 'platform', 'linux'), \
             patch.object(e.os.path, 'isdir', return_value=True), \
             patch.object(e.os, 'listdir', side_effect=[['42'], ['3']]), \
             patch.object(e.os, 'readlink', return_value=str(self.source)), \
             patch.object(e.os, 'stat', return_value=before):
            with self.assertRaisesRegex(e.SafeError, 'process 42'):
                e.refuse_active_file(str(self.source), before)
        self.assertTrue(self.source.exists())
    def test_confirmation_required(self):
        with patch.object(sys.stdin, 'isatty', return_value=False):
            with self.assertRaises(e.SafeError): e.confirm(type('A', (), {'yes':False})(), 'Delete?')
    def test_roundtrip_and_metadata(self):
        with patch.object(e, 'move', self.portable_move), patch.object(e, 'refuse_mounts'):
            self.source.chmod(0o640)
            before = self.source.stat()
            ident = self.call('delete')
            self.assertFalse(self.source.exists())
            self.call('restore', id=ident)
            after = self.source.stat()
            self.assertEqual(self.source.read_text(), 'hello')
            self.assertEqual((before.st_ino, before.st_mtime_ns, stat.S_IMODE(before.st_mode)),
                             (after.st_ino, after.st_mtime_ns, stat.S_IMODE(after.st_mode)))
    def test_collision(self):
        with patch.object(e, 'move', self.portable_move):
            ident = self.call('delete')
            self.source.symlink_to('absent')
            with self.assertRaises(e.SafeError): self.call('restore', id=ident)
            self.assertTrue((self.root / ident / 'payload').exists())
    def test_expiration_guard(self):
        with patch.object(e, 'move', self.portable_move):
            ident = self.call('delete')
            with self.assertRaises(e.SafeError): self.call('purge', id=ident)
    def test_restore_deadline_preserves_payload(self):
        with patch.object(e, 'move', self.portable_move):
            ident = self.call('delete')
            with patch.object(e.time, 'time', return_value=time.time() + 120):
                with self.assertRaisesRegex(e.SafeError, 'deadline'):
                    self.call('restore', id=ident)
            self.assertTrue((self.root / ident / 'payload').exists())
    def test_deadline_crossed_during_confirmation(self):
        with patch.object(e, 'move', self.portable_move):
            ident = self.call('delete')
            future = time.time() + 120
            # Advance time only when confirmation completes.
            with patch.object(e.time, 'time', side_effect=[future - 120, future]), \
                 patch.object(e, 'confirm'):
                with self.assertRaisesRegex(e.SafeError, 'deadline'):
                    self.call('restore', id=ident)
            self.assertTrue((self.root / ident / 'payload').exists())
    def test_list_remaining_and_batch_purge(self):
        with patch.object(e, 'move', self.portable_move):
            old = self.call('delete')
            self.source.write_text('new')
            new = self.call('delete')
        with e.entry(self.fd, old) as fd:
            r = e.read(fd)
            r['expires'] = time.time() - 1
            e.save(fd, r)
        records = [json.loads(line) for line in self.call('list').splitlines()]
        expired = next(r for r in records if r['id'] == old)
        self.assertEqual(expired['remaining_seconds'], 0)
        self.assertTrue(expired['expired'])
        with patch.object(e, 'confirm', side_effect=e.SafeError('Cancelled')):
            with self.assertRaises(e.SafeError): self.call('purge-expired')
        self.assertTrue((self.root / old / 'payload').exists())
        self.call('purge-expired')
        self.assertFalse((self.root / old).exists())
        self.assertTrue((self.root / new / 'payload').exists())
    def test_symlink_roundtrip(self):
        self.source.unlink()
        self.source.symlink_to('missing-target')
        with patch.object(e, 'move', self.portable_move):
            ident = self.call('delete')
            self.call('restore', id=ident)
        self.assertEqual(os.readlink(self.source), 'missing-target')
    def test_interrupted_move_preserves_record(self):
        with patch.object(e, 'move', side_effect=OSError('injected failure')):
            with self.assertRaises(OSError): self.call('delete')
        ident = next(p.name for p in self.root.iterdir())
        with e.entry(self.fd, ident) as fd:
            self.assertEqual(e.read(fd)['state'], 'prepared')
        self.assertTrue(self.source.exists())
    def test_manifest_symlink_refused(self):
        ident = 'a'*32
        (self.root / ident).mkdir()
        (self.root / ident / 'manifest.json').symlink_to(self.source)
        with e.entry(self.fd, ident) as fd:
            with self.assertRaises(OSError): e.read(fd)

@unittest.skipUnless(sys.platform in ('linux', 'darwin') and os.geteuid() != 0,
                     'Requires Linux or macOS and an unprivileged user')
class NativeIntegration(unittest.TestCase):
    def test_atomic_move_refuses_existing_destinations(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            fd = e.checked_dir(str(base))
            try:
                (base / 'source').write_text('preserve')
                for kind in ('file', 'directory', 'symlink'):
                    dest = base / kind
                    if kind == 'file': dest.write_text('existing')
                    elif kind == 'directory': dest.mkdir()
                    else: dest.symlink_to('missing')
                    with self.assertRaises(FileExistsError):
                        e.move(fd, 'source', fd, kind)
                    self.assertEqual((base / 'source').read_text(), 'preserve')
                e.move(fd, 'source', fd, 'moved')
                self.assertEqual((base / 'moved').read_text(), 'preserve')
            finally:
                os.close(fd)

    def test_installed_cli_and_library_with_spaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp).resolve() / 'prefix with spaces'
            result = subprocess.run(['/bin/bash', str(BASE / 'install.sh'), str(prefix)],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            cli = prefix / 'bin/safedelete'
            result = subprocess.run([str(cli), '--help'], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('purge-expired', result.stdout)
            result = subprocess.run(['/bin/bash', '-c',
                                     'source "$1/lib/safedelete/lib/safedelete.sh"; safedelete --help',
                                     'test', str(prefix)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run(['/bin/bash', str(BASE / 'install.sh'), str(prefix)],
                                    text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            quarantine = prefix / 'share/safedelete'
            quarantine.mkdir(parents=True)
            (quarantine / 'keep').write_text('recoverable')
            # Simulate the previous installer, including its original launcher.
            destination = prefix / 'lib/safedelete'
            original = subprocess.check_output(['/bin/bash', '-c',
                'printf \'#!/usr/bin/env bash\\nexec %q "$@"\\n\' "$1"',
                'test', str(destination / 'bin/safedelete')], text=True)
            cli.write_text(original)
            for name in ('lib/manage_install.py', 'uninstall.sh'):
                (destination / name).unlink()
            result = subprocess.run(['/bin/bash', str(BASE / 'install.sh'), '--upgrade', str(prefix)],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run(['/bin/bash', str(destination / 'uninstall.sh'), str(prefix)],
                                    input='', text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(cli.exists())
            result = subprocess.run(['/bin/bash', str(destination / 'uninstall.sh'), str(prefix), '--yes'],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(cli.exists())
            self.assertFalse(destination.exists())
            self.assertEqual((quarantine / 'keep').read_text(), 'recoverable')

    def test_installer_explains_missing_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            tools = Path(tmp).resolve()
            (tools / 'uname').symlink_to('/usr/bin/uname')
            env = dict(os.environ, PATH=str(tools))
            result = subprocess.run(['/bin/bash', str(BASE / 'install.sh')],
                                    env=env, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Python 3.11+ is required', result.stderr)
            if sys.platform == 'darwin':
                self.assertIn('brew install python', result.stderr)

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS mount table')
    def test_native_mount_table(self):
        self.assertIn('/', e.mac_mounts())
        with self.assertRaisesRegex(e.SafeError, 'Mount points'):
            e.refuse_mounts('/dev')

    def test_open_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp).resolve() / 'open file'
            source.write_text('keep')
            with source.open() as stream:
                with self.assertRaisesRegex(e.SafeError, 'in use'):
                    e.refuse_active_file(str(source), source.stat())

    def test_native_dangling_symlink_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            source = base / 'link'
            source.symlink_to('missing-target')
            cmd = [str(BASE / 'bin/safedelete'), '--root', str(base / 'q')]
            deleted = subprocess.run(cmd + ['delete', '--yes', '--', str(source)],
                                     text=True, capture_output=True)
            self.assertEqual(deleted.returncode, 0, deleted.stderr)
            restored = subprocess.run(cmd + ['restore', '--yes', deleted.stdout.strip()],
                                      text=True, capture_output=True)
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertEqual(os.readlink(source), 'missing-target')

    def test_cli_lifecycle_lock_and_purge(self):
        import fcntl
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            root = base / 'q'
            source = base / 'data'
            source.mkdir()
            (source / 'keep').write_text('payload')
            outside = base / 'outside'
            outside.write_text('safe')
            (source / 'link').symlink_to(outside)
            cmd = [str(BASE / 'bin/safedelete'), '--root', str(root)]
            def call(*args, ok=True):
                r = subprocess.run(cmd+list(args), text=True, capture_output=True)
                self.assertEqual(r.returncode == 0, ok, r.stderr)
                return r.stdout.strip()
            call('delete', str(source), ok=False)
            ident = call('delete', '--yes', '--ttl', '1', str(source))
            call('purge', '--yes', ident, ok=False)
            with open(root / '.lock', 'r+') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                call('list', ok=False)
            call('restore', '--yes', ident)
            self.assertEqual((source/'keep').read_text(), 'payload')
            ident = call('delete', '--yes', '--ttl', '1', str(source))
            time.sleep(1.1)
            call('purge', '--yes', ident)
            self.assertEqual(outside.read_text(), 'safe')
            self.assertFalse((root/ident).exists())

if __name__ == '__main__': unittest.main(verbosity=2)
