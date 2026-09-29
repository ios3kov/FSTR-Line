"""Compile/run our ownership model; never loads an Adobe library or plugin."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class LifetimeControlTests(unittest.TestCase):
    def test_disconnect_and_owner_lifetime(self):
        compiler = shutil.which("c++")
        self.assertIsNotNone(compiler, "C++ compiler required for lifetime gate")
        source = Path(__file__).with_name("lifetime_control.cpp")
        with tempfile.TemporaryDirectory(prefix="fstr-lifetime-") as folder:
            binary = Path(folder) / "lifetime-control"
            args = [compiler, "-std=c++17", "-pthread", "-Wall", "-Wextra", "-Werror"]
            if os.environ.get("FSTR_LIFETIME_SANITIZERS") == "1":
                args += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
            build = subprocess.run(args + [str(source), "-o", str(binary)],
                                   capture_output=True, text=True, timeout=45)
            self.assertEqual(build.returncode, 0, build.stderr[-8000:])
            run = subprocess.run([str(binary)], capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr[-8000:])
            self.assertEqual(run.stderr, "")
            self.assertEqual(json.loads(run.stdout), {
                "kind": "owned-lifetime-model", "checks": 4,
                "result": "PASS", "aeRuntime": "NOT RUN",
            })


if __name__ == "__main__":
    unittest.main()
