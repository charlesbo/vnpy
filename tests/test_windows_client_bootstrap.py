"""Execute the PowerShell bootstrap with isolated fake interpreters on Linux.

These tests run real PowerShell control flow, but stub Python and pip. They do
not prove Windows installation, dependency downloads, or Qt GUI behaviour.
Set PWSH to a PowerShell executable when it is not already on PATH.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PWSH = os.environ.get("PWSH") or shutil.which("pwsh")

FAKE_PYTHON = '''#!{python}
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
entry = {{"exe": sys.argv[0], "args": args, "cwd": os.getcwd()}}
with open(os.environ["BOOTSTRAP_CALL_LOG"], "a", encoding="utf-8") as stream:
    stream.write(json.dumps(entry) + "\\n")
if args[:1] == ["-c"] and "sys.version_info" in args[1]:
    versions = json.loads(os.environ.get("BOOTSTRAP_RUNTIME_MAP", "{{}}"))
    runtime = versions.get(sys.argv[0], {{"version": [3, 11], "bits": 64, "implementation": "cpython"}})
    print(json.dumps(runtime))
elif args[:2] == ["-m", "venv"]:
    if os.environ.get("BOOTSTRAP_FAIL_VENV"):
        sys.exit(17)
    target = Path(args[2]) / "Scripts" / "python.exe"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(Path(sys.argv[0]).read_text(encoding="utf-8"), encoding="utf-8")
    target.chmod(0o755)
elif args[:2] == ["-m", "pip"] and os.environ.get("BOOTSTRAP_FAIL_PIP"):
    print("simulated pip failure", file=sys.stderr)
    sys.exit(23)
'''


@unittest.skipUnless(PWSH and os.name == "posix", "Requires PowerShell and POSIX executable stubs; no Windows claim")
class WindowsClientBootstrapBDD(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = ROOT / "scripts/setup_windows_client.ps1"
        if not cls.source.is_file():
            raise AssertionError("Missing scripts/setup_windows_client.ps1")

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="vnpy-bootstrap-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "checkout with spaces"
        (self.repo / "scripts").mkdir(parents=True)
        self.script = self.repo / "scripts/setup_windows_client.ps1"
        shutil.copyfile(self.source, self.script)
        (self.repo / "pyproject.toml").write_text("[project]\nname = 'vnpy'\n", encoding="utf-8")
        client = self.repo / "examples/client_server/run_windows_client.py"
        client.parent.mkdir(parents=True)
        client.write_text("# client entry point\n", encoding="utf-8")
        self.log = self.base / "calls.jsonl"
        self.env = dict(os.environ)
        for name in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)", "SystemDrive"):
            self.env.pop(name, None)
        self.env.update({"PATH": "", "BOOTSTRAP_CALL_LOG": str(self.log), "POWERSHELL_TELEMETRY_OPTOUT": "1"})

    def fake_python(self, path: Path, *, version: tuple[int, int] = (3, 11), bits: int = 64) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(FAKE_PYTHON.format(python=sys.executable), encoding="utf-8")
        path.chmod(0o755)
        runtimes = json.loads(self.env.get("BOOTSTRAP_RUNTIME_MAP", "{}"))
        runtimes[str(path)] = {"version": list(version), "bits": bits, "implementation": "cpython"}
        self.env["BOOTSTRAP_RUNTIME_MAP"] = json.dumps(runtimes)
        return path

    def run_setup(self, python: Path | None = None) -> subprocess.CompletedProcess[str]:
        command = [str(PWSH), "-NoProfile", "-NonInteractive", "-File", str(self.script)]
        if python is not None:
            command.extend(["-PythonPath", str(python)])
        return subprocess.run(command, cwd=self.base, env=self.env, text=True, capture_output=True, timeout=30)

    def calls(self) -> list[dict]:
        if not self.log.is_file():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def test_given_an_explicit_python_with_spaces_when_setup_runs_then_checkout_is_editable_and_client_is_not_launched(self) -> None:
        python = self.fake_python(self.base / "Python with spaces/python.exe")
        result = self.run_setup(python)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self.calls()
        self.assertTrue(any(call["args"][:2] == ["-m", "venv"] for call in calls))
        self.assertTrue(any(call["args"][:4] == ["-m", "pip", "install", "-e"] and call["args"][4] == str(self.repo) for call in calls))
        self.assertTrue(any("vnpy_rpcservice==1.1.0" in call["args"] for call in calls))
        self.assertTrue(any("vnpy_optionmaster==1.3.0" in call["args"] for call in calls))
        self.assertTrue(any("vnpy_spreadtrading==1.4.0" in call["args"] for call in calls))
        self.assertTrue(all(call["cwd"] == str(self.repo) for call in calls))
        self.assertFalse(any(any(arg.endswith("run_windows_client.py") for arg in call["args"]) for call in calls))
        self.assertIn("update_client.bat", result.stdout)

    def test_given_no_py_launcher_when_python_is_in_its_standard_user_location_then_setup_finds_it(self) -> None:
        self.env["LOCALAPPDATA"] = str(self.base / "local app data")
        python = self.fake_python(Path(self.env["LOCALAPPDATA"]) / "Programs/Python/Python311/python.exe")
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls()[0]["exe"], str(python))

    def test_given_existing_python_313_when_setup_runs_then_no_311_installation_is_required(self) -> None:
        self.env["LOCALAPPDATA"] = str(self.base / "local app data")
        python = self.fake_python(
            Path(self.env["LOCALAPPDATA"]) / "Programs/Python/Python313/python.exe",
            version=(3, 13),
        )
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.calls()[0]["exe"], str(python))

    def test_given_python_is_only_on_path_when_setup_runs_then_it_is_runtime_validated(self) -> None:
        python = self.fake_python(self.base / "path bin/python.exe")
        self.env["PATH"] = str(python.parent)
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("sys.version_info", self.calls()[0]["args"][1])

    def test_given_wrong_explicit_python_version_when_setup_runs_then_it_stops_before_creating_a_venv(self) -> None:
        python = self.fake_python(self.base / "wrong/python.exe", version=(3, 12))
        result = self.run_setup(python)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CPython 3.11 or 3.13", result.stdout + result.stderr)
        self.assertFalse((self.repo / ".venv").exists())
        self.assertEqual(len(self.calls()), 1)

    def test_given_32_bit_python_when_setup_runs_then_it_refuses_an_incompatible_runtime(self) -> None:
        python = self.fake_python(self.base / "x86/python.exe", bits=32)
        result = self.run_setup(python)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("64-bit", result.stdout + result.stderr)
        self.assertFalse((self.repo / ".venv").exists())

    def test_given_python_is_missing_when_setup_runs_then_it_prints_installer_commands_without_installing_anything(self) -> None:
        result = self.run_setup()
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("https://www.python.org/downloads/windows/", output)
        self.assertIn("winget install --exact --id Python.Python.3.13 --architecture x64", output)
        self.assertFalse((self.repo / ".venv").exists())
        self.assertEqual(self.calls(), [])

    def test_given_an_existing_matching_venv_when_setup_repeats_then_it_is_reused(self) -> None:
        self.fake_python(self.repo / ".venv/Scripts/python.exe")
        result = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(any(call["args"][:2] == ["-m", "venv"] for call in self.calls()))

    def test_given_an_existing_incompatible_venv_when_setup_runs_then_it_does_not_replace_it(self) -> None:
        existing = self.fake_python(self.repo / ".venv/Scripts/python.exe", version=(3, 10))
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("existing .venv", result.stdout + result.stderr)
        self.assertTrue(existing.is_file())
        self.assertEqual(len(self.calls()), 1)

    def test_given_pip_fails_when_installing_then_setup_stops_and_does_not_report_ready(self) -> None:
        python = self.fake_python(self.base / "Python311/python.exe")
        self.env["BOOTSTRAP_FAIL_PIP"] = "1"
        result = self.run_setup(python)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("23", result.stdout + result.stderr)
        self.assertNotIn("Client environment is ready", result.stdout)
        self.assertEqual(sum(call["args"][:2] == ["-m", "pip"] for call in self.calls()), 1)

    def test_given_venv_creation_fails_when_setup_runs_then_no_pip_command_is_executed(self) -> None:
        python = self.fake_python(self.base / "Python311/python.exe")
        self.env["BOOTSTRAP_FAIL_VENV"] = "1"
        result = self.run_setup(python)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(any(call["args"][:2] == ["-m", "pip"] for call in self.calls()))

    def test_given_a_windows_store_alias_when_no_real_python_exists_then_it_is_not_executed(self) -> None:
        alias = self.fake_python(self.base / "Microsoft/WindowsApps/python.exe")
        self.env["PATH"] = str(alias.parent)
        result = self.run_setup()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])


class BootstrapBatchStaticChecks(unittest.TestCase):
    def test_batch_forwards_arguments_to_powershell_and_propagates_failure(self) -> None:
        """Static wrapper check only: cmd.exe is unavailable on this Linux host."""
        batch = (ROOT / "setup_client.bat").read_text(encoding="utf-8").lower()
        self.assertIn('powershell.exe -noprofile -executionpolicy bypass -file "%~dp0scripts\\setup_windows_client.ps1" %*', batch)
        self.assertIn("exit /b %errorlevel%", batch)


if __name__ == "__main__":
    unittest.main()
