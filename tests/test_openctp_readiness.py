import unittest
from types import SimpleNamespace

from scripts.check_openctp_server import select_contracts, login_ready


class OpenCtpReadinessTDD(unittest.TestCase):
    def test_given_only_logins_when_checking_readiness_then_account_and_contracts_are_required(self) -> None:
        self.assertFalse(login_ready({"ready": True, "accounts": 0}))
        self.assertTrue(login_ready({"ready": True, "accounts": 1}))

    def test_given_preferred_gold_contracts_when_selecting_then_both_futures_and_options_are_subscribed(self) -> None:
        contracts = [
            SimpleNamespace(vt_symbol="au2612.SHFE"),
            SimpleNamespace(vt_symbol="au2612C1000.SHFE"),
        ]
        self.assertEqual(select_contracts(contracts, ["au2612.SHFE", "au2612C1000.SHFE"]), contracts)

    def test_given_an_unknown_subscription_when_selecting_then_validation_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing contracts"):
            select_contracts([], ["unknown.SHFE"])


if __name__ == "__main__":
    unittest.main()
