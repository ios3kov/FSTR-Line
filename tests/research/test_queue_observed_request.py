"""Observed-name request contract only. Never launches or subscribes to Adobe AE."""
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'research/ae-notifications/Queue-Inspect-Observed.command'
REVIEW = ROOT / 'docs/TEST_RECORDS/evidence/queue-eef15f5-review.json'


class ObservedRequestTests(unittest.TestCase):
    def invoke(self, args, env=None):
        return subprocess.run(['/bin/bash', str(SCRIPT), *args], capture_output=True,
                              text=True, timeout=10, env=env)

    def test_bash_syntax(self):
        subprocess.run(['/bin/bash', '-n', str(SCRIPT)], check=True, timeout=10)

    def test_selections_match_exact_observed_inventory(self):
        rows = json.loads(REVIEW.read_text())['newInventoryLeads']
        selected = re.findall(r"--inspect-symbol '([^']+)'", SCRIPT.read_text())
        self.assertEqual(selected, [r['module'] + ':' + r['symbol'] for r in rows])
        self.assertEqual(len(selected), 12)
        self.assertEqual(len(set(selected)), 12)
        self.assertTrue(all(r['address'] and r['module'] == 'BEE' for r in rows))

    def test_no_kit_and_bad_arguments_refuse(self):
        with tempfile.TemporaryDirectory() as td:
            for args in ([td + '/missing'], [td, '--unknown'], [td, '--verify-only', 'extra']):
                with self.subTest(args=args):
                    self.assertEqual(self.invoke(args).returncode, 2)

    def test_wrong_payload_refused_before_execution(self):
        with tempfile.TemporaryDirectory() as td:
            kit = Path(td)
            marker = kit / 'must-not-run'
            (kit / 'Queue-AE.command').write_text('touch "' + str(marker) + '"\n')
            done = self.invoke([td])
            self.assertEqual(done.returncode, 2, done.stdout + done.stderr)
            self.assertFalse(marker.exists())

    def test_every_required_file_is_pinned(self):
        pairs = re.findall(r'^([0-9a-f]{64})  ([A-Za-z0-9_.-]+)$', SCRIPT.read_text(), re.M)
        self.assertEqual(len(pairs), 6)
        self.assertEqual({n for _, n in pairs}, {'Queue-AE.command', 'queue_kit.py', 'queue_static.py',
                                               'deep_targets.json', 'QUEUE-README.txt', 'build-manifest.json'})
        review = json.loads(REVIEW.read_text())
        pins = {n: digest for digest, n in pairs}
        self.assertEqual(pins['build-manifest.json'], review['manifestSha256'])
        self.assertEqual(pins['queue_static.py'], review['collectorSha256'])
        self.assertEqual(pins['deep_targets.json'], review['policySha256'])

    def test_forwarding_exit_code_and_paths_on_owned_fake_launcher(self):
        # Simulated successful hashing validates argv/quoting only, not real integrity.
        # Separate real-shasum refusal test above and exact-kit local verification apply.
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            kit = base / 'Кириллица "space"'
            kit.mkdir()
            tools = base / 'fake-tools'; tools.mkdir()
            checker = tools / 'shasum'
            checker.write_text('#!/bin/sh\ncat > /dev/null\nexit 0\n'); checker.chmod(0o755)
            launcher = kit / 'Queue-AE.command'
            launcher.write_text('#!/bin/bash\nprintf "%s\\n" "$@" > args.txt\nexit 7\n')
            env = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ.get('PATH', ''))
            expected = re.findall(r"--inspect-symbol '([^']+)'", SCRIPT.read_text())
            flags = [v for n in expected for v in ('--inspect-symbol', n)]
            for mode in ([], ['--verify-only']):
                with self.subTest(mode=mode):
                    done = self.invoke([str(kit), *mode], env)
                    self.assertEqual(done.returncode, 7, done.stdout + done.stderr)
                    self.assertEqual((kit / 'args.txt').read_text().splitlines(), mode + flags)


if __name__ == '__main__':
    unittest.main()
