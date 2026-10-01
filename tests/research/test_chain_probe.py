"""Compile/run the implemented native core; never load or attach to Adobe."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
INCLUDE = ROOT / 'research/ae-notifications/chain-probe'
CONTROL = ROOT / 'tests/research/chain_probe_control.cpp'


def compiler():
    return ['xcrun', 'clang++'] if sys.platform == 'darwin' else ['clang++']


class ChainProbeTests(unittest.TestCase):
    def run_native(self, flags):
        with tempfile.TemporaryDirectory(prefix='fstr-chain-native-') as td:
            exe = Path(td) / 'owned-chain'
            command = compiler() + ['-std=c++17', '-Wall', '-Wextra', '-Werror', '-pthread',
                                    *flags, '-I', str(INCLUDE), str(CONTROL), '-o', str(exe)]
            built = subprocess.run(command, capture_output=True, text=True, timeout=60)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            env = {**os.environ, 'ASAN_OPTIONS': 'halt_on_error=1:detect_leaks=0',
                   'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'}
            done = subprocess.run([str(exe)], capture_output=True, text=True, timeout=20, env=env)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertEqual(done.stderr, '')
            row = json.loads(done.stdout)
            self.assertEqual(row['status'], 'PASS')
            self.assertEqual(row['scenarios'], 10)
            self.assertEqual(row['AdobeRuntime'], 'NOT RUN')
            self.assertEqual(row['SYNC-001'], 'NOT RUN')

    def test_native_sanitized(self):
        self.run_native(['-O1', '-g', '-fno-omit-frame-pointer', '-fsanitize=address,undefined'])

    def test_native_optimized(self):
        self.run_native(['-O2'])

    def test_arm64_lowered_forwarding_without_sdk_or_private_calls(self):
        # No system/SDK includes are needed for this calling-convention check.
        # Inspect compiler-emitted arm64 assembly, never execute Adobe code.
        with tempfile.TemporaryDirectory(prefix='fstr-chain-arm64-') as td:
            source = Path(td) / 'shim.cpp'
            assembly = Path(td) / 'shim.s'
            source.write_text('#include "chain_abi.hpp"\nextern "C" int FSTR_Forward(void* c,int m,void* p)'
                              '{return fstr::research::continue_chain(c,m,p);}\n')
            built = subprocess.run(compiler() + ['-target', 'arm64-apple-macos11', '-ffreestanding',
                '-nostdinc++', '-std=c++17', '-O2', '-I', str(INCLUDE), '-S', str(source), '-o', str(assembly)],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(built.returncode, 0, built.stderr)
            text = assembly.read_text()
            self.assertRegex(text, r'ldr\s+x\d+,\s*\[x0\]')
            self.assertRegex(text, r'ldr\s+x\d+,\s*\[x\d+,\s*#(?:16|0x10)\]')
            self.assertRegex(text, r'br\s+x\d+')
            self.assertNotRegex(text, r'\b(?:str|stp|bl)\s')
            self.assertNotRegex(text, r'\b(?:mov|ldr|add)\s+[xw][012],')


if __name__ == '__main__':
    unittest.main()
