"""Exercise the local RpcService/RpcClient request path without a CTP account."""

import time

from vnpy.event import EventEngine
from vnpy.rpc import RpcClient
from vnpy.trader.engine import MainEngine
from vnpy_rpcservice import RpcServiceApp


def main() -> None:
    request_address = "tcp://127.0.0.1:2014"
    publish_address = "tcp://127.0.0.1:4102"
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    rpc_engine = main_engine.add_app(RpcServiceApp)
    client = RpcClient()

    try:
        if not rpc_engine.start(request_address, publish_address):
            raise RuntimeError("RpcService failed to bind local ports")

        client.subscribe_topic("")
        client.start(request_address, publish_address)
        contracts = None
        last_error: Exception | None = None
        for _ in range(10):
            try:
                contracts = client.get_all_contracts()
                break
            except Exception as exc:
                last_error = exc
                time.sleep(0.2)

        if contracts is None:
            raise RuntimeError("RpcClient could not query RpcService") from last_error
        if contracts:
            raise AssertionError(f"Expected no contracts without a CTP account, found {len(contracts)}")
        print("PASS: local RpcClient queried RpcService; no CTP account was connected.")
    finally:
        client.stop()
        client.join()
        main_engine.close()


if __name__ == "__main__":
    main()
