from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import test_app_collection as base


class BudgetTests(unittest.TestCase):
    def test_failed_worker_consumes_byte_budget(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = base.fixture(Path(temporary))
            main = app / 'Contents/MacOS/AEFixture'
            (app / 'Contents/other').write_bytes(main.read_bytes())
            calls = []
            def fail(path, *args):
                calls.append(path)
                raise ValueError('injected failure')
            result = base.collector.collect(app, inspector=fail, max_bytes=main.stat().st_size)
            self.assertEqual(len(calls), 1)
            self.assertEqual(result['collectionStatus'], 'FAIL')
            self.assertTrue(result['limits'])

    def test_timeout_never_downgrades_previous_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = base.fixture(Path(temporary))
            (app / 'Contents/other').write_bytes((app / 'Contents/MacOS/AEFixture').read_bytes())
            calls = []
            def fail(path, *args):
                calls.append(path)
                if len(calls) == 1:
                    raise ValueError('injected failure')
                raise subprocess.TimeoutExpired('owned-worker', 1)
            result = base.collector.collect(app, inspector=fail)
            self.assertEqual(result['collectionStatus'], 'FAIL')
            self.assertEqual([x['status'] for x in result['modules']], ['FAIL', 'BLOCKED'])

    def test_unreadable_subdirectory_is_not_silent_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            app = base.fixture(Path(temporary))
            def walk(*args, **kwargs):
                kwargs['onerror'](PermissionError('fixture'))
                return iter(())
            with mock.patch.object(base.collector.os, 'walk', walk):
                result = base.collector.collect(app, inspector=base.fake_inspect)
            self.assertEqual(result['collectionStatus'], 'BLOCKED')
            self.assertEqual(len(result['modules']), 1)


if __name__ == '__main__':
    unittest.main()
