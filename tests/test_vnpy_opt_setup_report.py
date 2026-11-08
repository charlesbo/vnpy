from pathlib import Path
import unittest


DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"


class FeasibilityReportBDD(unittest.TestCase):
    """Acceptance scenarios for the vn.py deployment feasibility report."""

    @classmethod
    def setUpClass(cls) -> None:
        reports = sorted(DOCS_DIR.glob("01_*.md"))
        if len(reports) != 1:
            raise AssertionError(f"Expected one docs/01_*.md report, found {reports}")
        cls.report_path = reports[0]
        cls.report = cls.report_path.read_text(encoding="utf-8")

    def test_given_the_initial_report_when_added_then_it_has_the_requested_numbered_name(self) -> None:
        self.assertTrue(self.report_path.name.startswith("01_"))
        self.assertGreater(len(self.report), 5000)

    def test_given_the_linux_windows_requirement_when_architecture_is_described_then_roles_are_separated(self) -> None:
        for phrase in ("Linux", "Windows", "CTP", "RpcService", "RpcGateway", "行情", "下单"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.report)

    def test_given_chinese_futures_options_when_installation_is_described_then_prerequisites_and_gateway_scope_are_clear(self) -> None:
        for phrase in ("Ubuntu 22.04", "Python 3.10", "vnpy_ctp", "国内期货、期权", "账户权限"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.report)

    def test_given_remote_trading_when_network_design_is_described_then_rpc_trust_limits_are_explicit(self) -> None:
        for phrase in ("可信网络", "pickle", "公网", "VPN", "审计"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.report)

    def test_given_iterative_customization_when_release_process_is_described_then_updates_have_validation_and_recovery(self) -> None:
        for phrase in ("BDD", "仿真", "健康检查", "回滚", "客户端升级"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.report)

    def test_given_research_conclusions_when_published_then_official_sources_are_linked(self) -> None:
        for url in (
            "https://github.com/vnpy/vnpy/blob/master/README.md",
            "https://github.com/vnpy/vnpy_ctp/blob/master/README.md",
            "https://github.com/vnpy/vnpy_rpcservice/blob/master/README.md",
            "https://github.com/vnpy/vnpy_optionmaster/blob/master/README.md",
        ):
            with self.subTest(url=url):
                self.assertIn(url, self.report)


if __name__ == "__main__":
    unittest.main()
