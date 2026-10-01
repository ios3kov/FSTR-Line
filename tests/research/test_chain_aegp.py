"""Real new sources; SDK/OS boundaries remain explicit. No Adobe code is loaded."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'research/ae-notifications/chain-probe'
CXX = ['xcrun', 'clang++'] if sys.platform == 'darwin' else ['clang++']


def run(args, **kw):
    result = subprocess.run(args, capture_output=True, text=True, timeout=60, **kw)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return result


class AegpProbeTests(unittest.TestCase):
    def test_bundle_receipt_is_fail_closed_and_identified(self):
        path = SRC / 'build_probe.py'
        spec = importlib.util.spec_from_file_location('fstr_chain_build_probe', path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        row = module.bundle_receipt('abc123', 'fstr-chain-aegp-abc123-disabled', False)
        self.assertEqual(row['schemaVersion'], 1)
        self.assertEqual(row['kind'], 'FSTRChainProbeResearch')
        self.assertEqual(row['sourceCommit'], 'abc123')
        self.assertFalse(row['privateProbeOptIn'])
        self.assertEqual(row['AEGP_load'], 'NOT RUN')
        self.assertEqual(row['SYNC-001'], 'NOT RUN')
        self.assertFalse(row['handoffApproved'])

    def test_compiled_pipl_validation_is_fail_closed(self):
        path = SRC / 'build_probe.py'
        spec = importlib.util.spec_from_file_location('fstr_chain_build_probe_pipl', path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        valid = '''resource 'PiPL' (16000) {
            { Kind { AEGP }, Name { "FSTR Chain Probe" },
              Category { "General Plugin" },
              CodeMacARM64 { "EntryPointFunc" } }
        };'''
        module.validate_pipl_dump(valid)
        for broken in (
            valid.replace('AEGP', 'AEEffect'),
            valid.replace('FSTR Chain Probe', 'Wrong'),
            valid.replace('EntryPointFunc', 'OtherEntry'),
            valid + valid,
        ):
            with self.assertRaises(ValueError):
                module.validate_pipl_dump(broken)

    def test_event_dispatch_optimized_and_sanitized(self):
        with tempfile.TemporaryDirectory() as td:
            exe = str(Path(td) / 'dispatch')
            for flags in (['-O2'], ['-O1', '-g', '-fsanitize=address,undefined']):
                run(CXX + ['-std=c++17', '-Wall', '-Wextra', '-Werror', *flags,
                    '-I', str(SRC), str(ROOT / 'tests/research/chain_dispatch_control.cpp'), '-o', exe])
                row = json.loads(run([exe], env={**os.environ, 'ASAN_OPTIONS':'detect_leaks=0',
                    'UBSAN_OPTIONS':'halt_on_error=1'}).stdout)
                self.assertEqual(row['status'], 'PASS')
                self.assertEqual(row['AdobeRuntime'], 'NOT RUN')

    @unittest.skipUnless(os.environ.get('FSTR_AE_SDK_ROOT'),
        'External licensed SDK required; do not substitute fake SDK declarations')
    def test_actual_sdk_entry_and_hooks(self):
        sdk = Path(os.environ['FSTR_AE_SDK_ROOT']) / 'Examples/Headers'
        self.assertTrue((sdk / 'AE_GeneralPlug.h').is_file())
        with tempfile.TemporaryDirectory() as td:
            exe = str(Path(td) / 'sdk-control')
            # Linux is a C++/declaration control through the SDK's own Android
            # conditional branch. It is NOT a macOS ABI, plugin, or AE build.
            platform = [] if sys.platform == 'darwin' else ['-D__ANDROID__']
            for enabled, scenarios in ((1, ['normal','suppressed','partial','wrong-host','wrong-thread','pin-fail','death-fail']),
                                       (0, ['disabled'])):
                run(CXX + ['-std=c++17', '-Wall','-Wextra','-Werror','-O1','-g',
                    '-fsanitize=address,undefined', *platform,
                    '-DFSTR_PROBE_BUILD_ID="sdk-control"', f'-DFSTR_ENABLE_PRIVATE_CHAIN_PROBE={enabled}',
                    '-I', str(sdk), '-I', str(sdk / 'SP'), '-I', str(SRC),
                    str(ROOT / 'tests/research/chain_aegp_control.cpp'), '-o', exe])
                for scenario in scenarios:
                    row = json.loads(run([exe, scenario], env={**os.environ,
                        'ASAN_OPTIONS':'detect_leaks=0', 'UBSAN_OPTIONS':'halt_on_error=1'}).stdout)
                    self.assertEqual(row['status'], 'PASS')

    @unittest.skipUnless(sys.platform == 'darwin', 'Actual Apple loader compile/control requires macOS')
    def test_macos_binding_refuses_non_ae_process(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / 'host.cpp'; exe = str(Path(td) / 'host')
            source.write_text('#include "binding.hpp"\n#include <cassert>\nint main(){'
                'fstr::research::Binding b; const char* reason=nullptr;'
                'assert(!fstr::research::bind_loaded_ae(b,reason));'
                'assert(reason && !b.insert && !b.remove);}\n')
            run(CXX + ['-std=c++17','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations',
                '-I',str(SRC),str(source),str(SRC/'binding_macos.cpp'),
                '-framework','CoreFoundation','-o',exe])
            run([exe])

if __name__ == '__main__':
    unittest.main()
