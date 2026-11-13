"""Limit OpenCTP's all-market contract feed to vn.py's futures/option scope."""

from vnpy.event import EventEngine
from vnpy.trader.constant import Product
from vnpy.trader.gateway import BaseGateway
from vnpy_ctp.gateway.ctp_gateway import (
    CtpGateway,
    CtpMdApi,
    CtpTdApi,
    EXCHANGE_CTP2VT,
    PRODUCT_CTP2VT,
)


class OpenCtpTdApi(CtpTdApi):
    """Keep upstream contract construction and query-completion behavior."""

    def onRspQryInstrument(self, data: dict, error: dict, reqid: int, last: bool) -> None:
        if error.get("ErrorID", 0):
            self.contract_inited = False
            self.gateway.write_error("合约信息查询失败", error)
            return

        product = PRODUCT_CTP2VT.get(data.get("ProductClass"))
        supported = (
            data.get("ExchangeID") in EXCHANGE_CTP2VT
            and product in {Product.FUTURES, Product.OPTION}
        )
        if supported:
            super().onRspQryInstrument(data, error, reqid, last)
        elif last:
            # Upstream needs a ProductClass even when the last response is empty.
            # A non-product record skips construction but still sets contract_inited
            # and replays/clears its cached order and trade callbacks in order.
            super().onRspQryInstrument({"ProductClass": ""}, error, reqid, True)


class OpenCtpGateway(CtpGateway):
    """Use the contract adapter without replacing any connected native API."""

    def __init__(self, event_engine: EventEngine, gateway_name: str) -> None:
        # CtpGateway's initializer allocates its own concrete TdApi. Initialize its
        # BaseGateway directly so only one trading and one market wrapper exist.
        BaseGateway.__init__(self, event_engine, gateway_name)
        self.td_api = OpenCtpTdApi(self)
        self.md_api = CtpMdApi(self)
        self.count = 0
