"""Pinned follow-up selection, synthetic refusal and owned Apple-image controls; NOT AE."""
import contextlib
import importlib.util
import io
import json
import plistlib
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'research/ae-notifications'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


q = load('details_queue', SRC / 'queue_static.py')
k = load('details_kit', SRC / 'queue_kit.py')
p = load('details_packager', ROOT / 'scripts/package-queue-research.py')
UID = '00000000-0000-4000-8000-000000000001'


def metadata(app):
    (app / 'Contents').mkdir(parents=True)
    values = {'CFBundleIdentifier': 'org.fstr.owned', 'CFBundleShortVersionString': 'fixture',
              'CFBundleVersion': 'fixture.1'}
    (app / 'Contents/Info.plist').write_bytes(plistlib.dumps(values))
    return {'aeBundleId': values['CFBundleIdentifier'], 'aeShortVersion': 'fixture',
            'aeBundleVersion': 'fixture.1', 'modules': {}}


def linked_details_control(collector, root):
    """Real Apple nm/objdump, fabricated function bodies/identity. No production-policy change."""
    app = root / 'Owned details.app'
    policy = metadata(app)
    for key, names in collector.CONTEXT_DETAILS_REQUIRED.items():
        names = names or ('_owned_other_module',)
        asm = app / ('Contents/' + key + '.s')
        asm.write_text('.text\n' + ''.join('.globl ' + name + '\n' + name + ':\nret\n' for name in names))
        binary = app / ('Contents/' + key + '.dylib')
        subprocess.run(['xcrun', 'clang', '-arch', 'arm64', '-dynamiclib', str(asm), '-o', str(binary)],
                       check=True, capture_output=True, timeout=30)
        uid = collector.arm64_uuid(subprocess.check_output(
            ['xcrun', 'dwarfdump', '--uuid', str(binary)], text=True, timeout=30))
        policy['modules'][key] = {'relativePath': str(binary.relative_to(app)),
                                  'sha256': collector.fingerprint(binary), 'uuid': uid}
    with mock.patch.dict(collector.CONTEXT_TABLE, {'moduleSha256': policy['modules']['BEE']['sha256']}):
        return collector.collect(app, policy, context_details=True)


class DetailsProfileTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve(); self.app = self.root / 'Owned details.app'
        self.policy = metadata(self.app); self.symbols = {}; self.calls = []
        for key, names in q.CONTEXT_DETAILS_REQUIRED.items():
            binary = self.app / 'Contents' / key; binary.write_bytes(key.encode())
            self.policy['modules'][key] = {'relativePath': 'Contents/' + key,
                                           'sha256': q.fingerprint(binary), 'uuid': UID}
            self.symbols[key] = {name: 0x1000 + 16*i for i, name in enumerate(names or ('_other',))}
        patch = mock.patch.dict(q.CONTEXT_TABLE, {'moduleSha256': self.policy['modules']['BEE']['sha256']})
        patch.start(); self.addCleanup(patch.stop)

    def runner(self, args, **bounds):
        self.calls.append(args)
        self.assertEqual(bounds['timeout'], 60)
        key = Path(args[-1]).name
        if args[-1] == '--version': text = 'owned fixture tool\n'
        elif args[1] == 'dwarfdump': text = f'UUID: {UID} (arm64) owned\n'
        elif args[1] == 'nm':
            text = ''.join(f'{address:016x} T {name}\n' for name, address in self.symbols[key].items())
        else:
            name = args[args.index('--dis-symname') + 1]
            text = f'{name}:\n{self.symbols[key][name]:x}\tret\n'
        return {'text': text, 'complete': True, 'exitCode': 0, 'reason': None,
                'bytes': len(text.encode()), 'sha256': q.digest(text.encode())}

    def collect(self, **kw):
        return q.collect(self.app, self.policy, self.runner, context_details=True, **kw)

    def assert_no_disassembly(self):
        self.assertFalse(any('--disassemble' in call for call in self.calls))

    def test_all_names_have_unique_received_provenance_and_no_old_bodies(self):
        evidence = json.loads((ROOT / 'docs/TEST_RECORDS/evidence/context-af0b8b9-review.json').read_text())
        inventory = {item['symbol']: item for item in evidence['inventory']}
        names = q.CONTEXT_DETAILS_REQUIRED['BEE']
        self.assertEqual(len(names), 8); self.assertEqual(len(set(names)), 8)
        self.assertFalse(set(names) & set(q.CONTEXT_REQUIRED['BEE']))
        self.assertFalse(set(names) & set(q.REQUIRED['BEE']))
        for name in names:
            self.assertEqual(inventory[name]['distinctAddressCount'], 1)
            self.assertFalse(inventory[name]['addressesTruncated'])
        self.assertEqual(q.CONTEXT_DETAILS_REQUIRED['AfterFXLib'], ())

    def test_complete_eight_bodies_no_table_or_notification_claim(self):
        reader = mock.Mock(side_effect=AssertionError('must not repeat range'))
        row = self.collect(read_range=reader)
        self.assertEqual(row['collectionStatus'], 'PASS', row)
        self.assertEqual(row['profile'], 'context-details'); self.assertEqual(row['expectedBodyCount'], 8)
        self.assertEqual(len(self.calls), 15); reader.assert_not_called()
        self.assertNotIn('commandTypeTable', row)
        self.assertEqual(set(row['claims'].values()), {'UNPROVEN'})
        self.assertFalse(row['privateInvocationAllowed']); self.assertEqual(row['SYNC-001'], 'NOT RUN')
        self.assertNotIn(str(self.root), json.dumps(row))
        self.assertFalse(any('lldb' in call for call in self.calls))

    def test_missing_or_ambiguous_function_blocks_before_any_body(self):
        name = q.CONTEXT_DETAILS_REQUIRED['BEE'][0]
        del self.symbols['BEE'][name]
        self.assertEqual(self.collect()['collectionStatus'], 'BLOCKED'); self.assert_no_disassembly()
        self.symbols['BEE'][name] = 0x1000
        original = self.runner
        def ambiguous(args, **kw):
            row = original(args, **kw)
            if args[1] == 'nm' and '-gU' not in args and Path(args[-1]).name == 'BEE':
                row['text'] += f'00009000 T {name}\n'
            return row
        self.runner = ambiguous
        self.assertTrue(self.collect()['reason'].startswith('AMBIGUOUS_REQUESTED_TEXT_SYMBOL'))
        self.assert_no_disassembly()

    def test_both_modules_verified_before_symbols(self):
        (self.app / 'Contents/AfterFXLib').write_bytes(b'changed')
        self.assertEqual(self.collect()['reason'], 'MODULE_HASH_MISMATCH:AfterFXLib')
        self.assertFalse(any('nm' in call for call in self.calls))

    def test_profile_conflicts_and_extras_are_refused_without_tools(self):
        self.assertEqual(self.collect(context_followup=True)['reason'], 'CONFLICTING_CONTEXT_PROFILES')
        self.assertEqual(self.collect(inspect_symbols=['BEE:_other'])['reason'], 'CONTEXT_PROFILE_DISALLOWS_EXTRA_SYMBOLS')
        self.policy['modules']['BEE']['sha256'] = 'f'*64
        self.assertEqual(self.collect()['reason'], 'CONTEXT_PROFILE_BUILD_MISMATCH')
        self.assertEqual(self.calls, [])
        self.assertEqual(q.collect(self.app, self.policy, self.runner, context_details=1)['reason'], 'INVALID_CONTEXT_PROFILE')

    def test_late_failed_body_cannot_leave_partial_pass(self):
        original = self.runner; last = q.CONTEXT_DETAILS_REQUIRED['BEE'][-1]
        def failed(args, **kw):
            row = original(args, **kw)
            if '--dis-symname' in args and last in args:
                row.update(complete=False, exitCode=1, reason='TOOL_FAILED')
            return row
        self.runner = failed
        row = self.collect(); self.assertEqual(row['collectionStatus'], 'BLOCKED')
        self.assertEqual(len(row['modules']['BEE']['bodies']), 7)

    def test_wrong_address_and_persistent_replacement_are_refused(self):
        original = self.runner
        def wrong(args, **kw):
            row = original(args, **kw)
            if '--dis-symname' in args: row['text'] = row['text'].replace('1000\t', '2000\t')
            return row
        self.runner = wrong
        self.assertEqual(self.collect()['reason'], 'REQUESTED_BODY_ADDRESS_MISMATCH')
        def replace(args, **kw):
            row = original(args, **kw)
            if q.CONTEXT_DETAILS_REQUIRED['BEE'][-1] in args:
                (self.app / 'Contents/BEE').write_bytes(b'changed')
            return row
        self.runner = replace
        self.assertEqual(self.collect()['reason'], 'MODULE_CHANGED_DURING_COLLECTION:BEE')

    def test_old_roots_selection_and_profile_extra_refusal_unchanged(self):
        self.assertEqual(q.requested_symbols([]), {key: list(names) for key, names in q.REQUIRED.items()})
        row = q.collect(self.app, self.policy, self.runner, context_followup=True, inspect_symbols=['BEE:_other'])
        self.assertEqual(row['reason'], 'CONTEXT_PROFILE_DISALLOWS_EXTRA_SYMBOLS')

    def test_bounded_inventory_includes_setup_lead_but_does_not_request_it(self):
        name = '__Z18BEE_WorkQueue_Initv'  # synthetic name, NOT an observed AE symbol
        self.symbols['BEE'][name] = 0x2000
        row = self.collect()
        self.assertIn(name, {item['symbol'] for item in row['modules']['BEE']['inventory']})
        self.assertNotIn(name, row['modules']['BEE']['bodies'])
        for i in range(q.MAX_LEADS): self.symbols['BEE'][f'__Z20BEE_WorkQueue_Test{i}v'] = 0x3000 + 4*i
        self.calls.clear()
        self.assertEqual(self.collect()['reason'], 'CANDIDATE_LIMIT:BEE'); self.assert_no_disassembly()

    @unittest.skipUnless(sys.platform == 'darwin', 'Apple linked-image/tool control; not Adobe AE')
    def test_real_linked_image_collects_all_eight_bodies(self):
        with tempfile.TemporaryDirectory() as td:
            row = linked_details_control(q, Path(td))
        self.assertEqual(row['collectionStatus'], 'PASS', row)
        self.assertEqual(row['expectedBodyCount'], 8)
        self.assertEqual(len(row['commands']), 15)


class DetailsPackageTests(unittest.TestCase):
    def test_mutually_exclusive_cli_profiles(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            k.main(['--context-followup', '--context-details'])
        self.assertEqual(caught.exception.code, 2)

    def test_exact_committed_package_launcher_identity_and_refusal(self):
        with tempfile.TemporaryDirectory(prefix='details path Юникод ') as td:
            root = Path(td); source = root / 'research/ae-notifications'; source.mkdir(parents=True)
            for name in p.NAMES: (source / name).write_bytes((SRC / name).read_bytes())
            (root / '.gitignore').write_text('dist/\n')
            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE, timeout=15)
            git('init', '-q'); git('add', '.')
            git('-c', 'user.name=Owned test', '-c', 'user.email=test@example.invalid',
                '-c', 'commit.gpgsign=false', 'commit', '-qm', 'owned details package control')
            built = p.build(root)
            with zipfile.ZipFile(built['archive']) as archive:
                self.assertEqual(set(archive.namelist()), {'FSTR-AE-Queue/' + name for name in (*p.NAMES, 'build-manifest.json')})
                for info in archive.infolist():
                    if info.filename.endswith('.command'): self.assertEqual(info.external_attr >> 16, 0o100755)
                archive.extractall(root / 'unpacked')
            kit = root / 'unpacked/FSTR-AE-Queue'
            manifest, _ = k.verify_kit(kit)
            self.assertEqual(manifest['sourceCommit'], built['sourceCommit'])
            def run(*args):
                return subprocess.run(['bash', str(kit / 'Queue-Details.command'), *args], capture_output=True, text=True, timeout=15)
            done = run('--verify-only'); self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(json.loads(done.stdout)['sourceCommit'], built['sourceCommit'])
            app = root / 'Owned.app'; app.mkdir()
            refused = run('--app', str(app), '--output', str(app / 'forbidden'))
            self.assertEqual(refused.returncode, 2); self.assertEqual(list(app.iterdir()), [])
            (kit / 'queue_static.py').write_bytes(b'raise AssertionError("must not execute")\n')
            done = run('--verify-only'); self.assertEqual(done.returncode, 2)
            self.assertIn('KIT_HASH_MISMATCH', done.stdout)


if __name__ == '__main__':
    unittest.main()
