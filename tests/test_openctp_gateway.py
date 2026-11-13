"""BDD/TDD coverage for OpenCTP's wider contract universe; no API connection."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from vnpy.event import EventEngine
from vnpy.trader.constant import Exchange, Product
try:
    from vnpy_ctp.gateway.ctp_gateway import (
        CtpGateway,
        THOST_FTDC_PC_Futures,
        THOST_FTDC_PC_Options,
        THOST_FTDC_PC_Combination,
        symbol_contract_map,
    )
    from scripts.openctp_gateway import OpenCtpGateway, OpenCtpTdApi
except ModuleNotFoundError as exc:
    if exc.name != "vnpy_ctp":
        raise
    CTP_AVAILABLE = False
else:
    CTP_AVAILABLE = True


def instrument(**overrides: object) -> dict:
    data = {
        "InstrumentID": "ag2612",
        "ExchangeID": "SHFE",
        "InstrumentName": "Silver futures",
        "ProductClass": THOST_FTDC_PC_Futures,
        "VolumeMultiple": 15,
        "PriceTick": 1,
        "MinLimitOrderVolume": 1,
        "MaxLimitOrderVolume": 500,
        "ProductID": "ag",
        "UnderlyingInstrID": "ag2612",
        "OptionsType": "1",
        "StrikePrice": 10000,
        "OpenDate": "20260101",
        "ExpireDate": "20261124",
    }
    data.update(overrides)
    return data


@unittest.skipUnless(CTP_AVAILABLE, "Optional vnpy_ctp gateway is required for adapter tests")
class OpenCtpContractAdapterBDD(unittest.TestCase):
    def setUp(self) -> None:
        self.original_contracts = symbol_contract_map.copy()
        symbol_contract_map.clear()
        self.gateway = SimpleNamespace(
            gateway_name="CTP",
            on_contract=Mock(),
            write_log=Mock(),
            write_error=Mock(),
        )
        # Construction does not create/init the native API or connect to any front.
        self.api = OpenCtpTdApi(self.gateway)

    def tearDown(self) -> None:
        symbol_contract_map.clear()
        symbol_contract_map.update(self.original_contracts)

    def test_given_a_future_when_received_then_upstream_contract_fields_and_cache_are_preserved(self) -> None:
        self.api.onRspQryInstrument(instrument(), {}, 1, False)
        contract = self.gateway.on_contract.call_args.args[0]
        self.assertEqual(contract.vt_symbol, "ag2612.SHFE")
        self.assertEqual(contract.product, Product.FUTURES)
        self.assertEqual(contract.size, 15)
        self.assertIs(symbol_contract_map["ag2612"], contract)
        self.assertFalse(self.api.contract_inited)

    def test_given_an_option_when_received_then_upstream_option_metadata_is_preserved(self) -> None:
        self.api.onRspQryInstrument(
            instrument(InstrumentID="ag2612C10000", ProductClass=THOST_FTDC_PC_Options), {}, 1, True
        )
        contract = self.gateway.on_contract.call_args.args[0]
        self.assertEqual(contract.product, Product.OPTION)
        self.assertEqual(contract.option_underlying, "ag2612")
        self.assertEqual(contract.option_strike, 10000)
        self.assertEqual(contract.option_expiry.strftime("%Y%m%d"), "20261124")
        self.assertTrue(self.api.contract_inited)

    def test_given_other_markets_or_products_when_received_then_they_are_filtered(self) -> None:
        for exchange in ("SSE", "SZSE", "TTS"):
            with self.subTest(exchange=exchange):
                self.api.onRspQryInstrument(instrument(ExchangeID=exchange), {}, 1, False)
        self.api.onRspQryInstrument(instrument(ProductClass=THOST_FTDC_PC_Combination), {}, 1, False)
        self.gateway.on_contract.assert_not_called()
        self.assertEqual(symbol_contract_map, {})
        self.assertFalse(self.api.contract_inited)

    def test_given_an_unsupported_final_record_when_received_then_cached_events_flush_in_upstream_order(self) -> None:
        self.api.onRspQryInstrument(instrument(), {}, 1, False)
        queued_order = {"kind": "order"}
        queued_trade = {"kind": "trade"}
        self.api.order_data.append(queued_order)
        self.api.trade_data.append(queued_trade)
        calls = []
        self.api.onRtnOrder = lambda data: calls.append(("order", data, self.api.contract_inited))
        self.api.onRtnTrade = lambda data: calls.append(("trade", data, self.api.contract_inited))

        self.api.onRspQryInstrument(instrument(ExchangeID="SSE"), {}, 1, True)

        self.assertTrue(self.api.contract_inited)
        self.assertEqual(calls, [("order", queued_order, True), ("trade", queued_trade, True)])
        self.assertEqual(self.api.order_data, [])
        self.assertEqual(self.api.trade_data, [])
        self.assertEqual(self.gateway.on_contract.call_count, 1)

    def test_given_an_empty_success_final_record_when_received_then_query_completes(self) -> None:
        self.api.onRspQryInstrument({}, {"ErrorID": 0, "ErrorMsg": ""}, 1, True)
        self.assertTrue(self.api.contract_inited)
        self.gateway.on_contract.assert_not_called()
        self.gateway.write_log.assert_called_once_with("合约信息查询成功")

    def test_given_a_query_error_when_received_then_it_is_reported_without_false_completion_or_cache_flush(self) -> None:
        queued_order = {"kind": "order"}
        self.api.order_data.append(queued_order)
        error = {"ErrorID": 7, "ErrorMsg": "query refused"}
        self.api.onRspQryInstrument({}, error, 1, True)
        self.assertFalse(self.api.contract_inited)
        self.assertEqual(self.api.order_data, [queued_order])
        self.gateway.write_error.assert_called_once_with("合约信息查询失败", error)
        self.gateway.on_contract.assert_not_called()

    def test_given_adapter_construction_when_registered_then_exactly_one_td_and_md_wrapper_are_created(self) -> None:
        with patch("scripts.openctp_gateway.OpenCtpTdApi") as td_type, patch(
            "scripts.openctp_gateway.CtpMdApi"
        ) as md_type:
            gateway = OpenCtpGateway(EventEngine(), "CTP")
        self.assertIsInstance(gateway, CtpGateway)
        td_type.assert_called_once_with(gateway)
        md_type.assert_called_once_with(gateway)
        self.assertIs(gateway.td_api, td_type.return_value)
        self.assertIs(gateway.md_api, md_type.return_value)
        self.assertEqual(gateway.count, 0)
        self.assertEqual(gateway.exchanges, [Exchange.CFFEX, Exchange.SHFE, Exchange.CZCE, Exchange.DCE, Exchange.INE, Exchange.GFEX])


if __name__ == "__main__":
    unittest.main()
