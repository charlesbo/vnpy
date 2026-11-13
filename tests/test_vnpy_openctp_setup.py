from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class OpenCtpSetupBDD(unittest.TestCase):
    """BDD acceptance checks for the local OpenCTP setup and Windows workflow."""

    @classmethod
    def setUpClass(cls) -> None:
        reports = sorted((ROOT / "docs").glob("02_*.md"))
        if len(reports) != 1:
            raise AssertionError(f"Expected one docs/02_*.md report, found {reports}")
        cls.report = reports[0].read_text(encoding="utf-8")

    def test_given_openctp_has_a_registered_account_when_server_is_started_then_credentials_are_externalized(self) -> None:
        script = (ROOT / "examples/client_server/run_openctp_server.py").read_text(encoding="utf-8")
        for name in ("OPENCTP_USER_ID", "OPENCTP_PASSWORD", "OPENCTP_TD_FRONT", "OPENCTP_MD_FRONT"):
            with self.subTest(name=name):
                self.assertIn(name, script)
        self.assertIn("RpcServiceApp", script)
        self.assertIn("tcp://trading.openctp.cn:30001", script)
        self.assertIn('"柜台环境": "测试"', script)

    def test_given_a_windows_operator_when_launching_the_rpc_client_then_no_local_ctp_connection_is_required(self) -> None:
        script = (ROOT / "examples/client_server/run_windows_client.py").read_text(encoding="utf-8")
        self.assertIn("RpcGateway", script)
        self.assertNotIn("CtpGateway", script)

    def test_given_the_client_checkout_when_updating_then_the_batch_pulls_master_and_relaunches_the_client(self) -> None:
        batch = (ROOT / "update_client.bat").read_text(encoding="utf-8").lower()
        self.assertIn("git pull --ff-only origin master", batch)
        self.assertIn(".venv\\scripts\\python.exe", batch)
        self.assertIn("run_windows_client.py", batch)

    def test_given_setup_results_when_published_then_report_documents_the_limits_and_commands(self) -> None:
        for phrase in (
            "Rocky Linux 9.3",
            "tcp://trading.openctp.cn:30001",
            "tcp://trading.openctp.cn:30011",
            "TTS",
            "setup_client.bat",
            "git pull --ff-only origin master",
            "update_client.bat",
            "已登录",
            "27024",
            "ssh -N",
            "systemctl --user",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.report)

    def test_given_windows_without_the_python_launcher_when_following_current_instructions_then_py_is_not_required(self) -> None:
        self.assertNotIn("py -3.11", self.report)
        self.assertIn("Python.Python.3.13", self.report)
        self.assertIn("Python 3.13.2", self.report)
        self.assertIn("-PythonPath", self.report)
        self.assertNotIn("本机没有 OpenCTP", self.report)

    def test_given_branch_cleanup_when_changes_are_merged_then_instructions_use_master(self) -> None:
        self.assertIn("master", self.report)
        self.assertNotIn("origin main", self.report)


if __name__ == "__main__":
    unittest.main()
