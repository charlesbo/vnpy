from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class OptionsClientWorkbenchBDD(unittest.TestCase):
    def test_given_client_setup_when_options_workbench_is_installed_then_optional_apps_are_version_pinned(self) -> None:
        script = (ROOT / "scripts/setup_windows_client.ps1").read_text(encoding="utf-8")
        self.assertIn("vnpy_optionmaster==1.3.0", script)
        self.assertIn("vnpy_spreadtrading==1.4.0", script)
        self.assertIn("vnpy_rpcservice==1.1.0", script)
        self.assertIn("PRICING_MODELS", script)
        self.assertIn("calculate_greeks", script)

    def test_given_option_apps_are_installed_when_client_starts_then_both_apps_are_loaded_over_rpc(self) -> None:
        script = (ROOT / "examples/client_server/run_windows_client.py").read_text(encoding="utf-8")
        for phrase in (
            "from vnpy_rpcservice import RpcGateway",
            "from vnpy_optionmaster import OptionMasterApp",
            "from vnpy_spreadtrading import SpreadTradingApp",
            "main_engine.add_gateway(RpcGateway)",
            "main_engine.add_app(OptionMasterApp)",
            "main_engine.add_app(SpreadTradingApp)",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, script)
        self.assertNotIn("CtpGateway", script)

    def test_given_an_external_network_when_connection_is_documented_then_rpc_stays_private(self) -> None:
        report = (ROOT / "docs/02_vnpy_openctp_deployment_and_client_update.md").read_text(encoding="utf-8")
        for phrase in (
            "100.64.0.0/10",
            "Tailscale",
            "ssh -N",
            "127.0.0.1:2014",
            "127.0.0.1:4102",
            "不要把 `2014/4102` 直接暴露到公网",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, report)

    def test_given_option_and_futures_combinations_when_workflow_is_described_then_pricing_and_execution_limits_are_clear(self) -> None:
        report = (ROOT / "docs/02_vnpy_openctp_deployment_and_client_update.md").read_text(encoding="utf-8")
        for phrase in (
            "OptionMaster",
            "SpreadTrading",
            "Black-76",
            "Binomial-Tree",
            "Greeks",
            "多腿",
            "部分成交",
            "服务端不需要重复实现定价模型",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, report)


if __name__ == "__main__":
    unittest.main()
