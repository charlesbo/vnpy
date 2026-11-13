"""Check an existing OpenCTP service via RPC queries and quote subscriptions only."""

import argparse
import json
import time
from threading import Event, Lock
from typing import Any


def login_ready(status: dict) -> bool:
    return bool(status.get("ready") and status.get("accounts", 0) > 0)


def select_contracts(contracts: list, symbols: list[str]) -> list:
    by_symbol = {contract.vt_symbol: contract for contract in contracts}
    missing = sorted(set(symbols) - by_symbol.keys())
    if missing:
        raise ValueError(f"Missing contracts: {missing}")
    return [by_symbol[symbol] for symbol in symbols]


def main() -> None:
    from vnpy.rpc import RpcClient
    from vnpy.trader.event import EVENT_TICK
    from vnpy.trader.object import SubscribeRequest

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", default="tcp://127.0.0.1:2014")
    parser.add_argument("--publish", default="tcp://127.0.0.1:4102")
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--subscribe", nargs="*", default=[])
    args = parser.parse_args()
    wanted = set(args.subscribe)
    seen: dict[str, dict] = {}
    lock = Lock()
    quotes_received = Event()

    class CheckClient(RpcClient):
        def callback(self, topic: str, event: Any) -> None:
            if event is None or event.type != EVENT_TICK:
                return
            tick = event.data
            if tick.vt_symbol not in wanted:
                return
            with lock:
                seen[tick.vt_symbol] = {"last_price": tick.last_price, "quote_time": tick.datetime.isoformat()}
                if wanted <= seen.keys():
                    quotes_received.set()

    client = CheckClient()
    client.subscribe_topic("")
    client.start(args.request, args.publish)
    try:
        deadline = time.monotonic() + args.timeout
        while True:
            status = client.get_server_status(timeout=5000)
            if login_ready(status):
                break
            if time.monotonic() >= deadline:
                raise TimeoutError(f"OpenCTP service not ready: {status}")
            time.sleep(0.5)

        if wanted:
            contracts = client.get_all_contracts(timeout=10000)
            for contract in select_contracts(contracts, args.subscribe):
                client.subscribe(SubscribeRequest(contract.symbol, contract.exchange), contract.gateway_name, timeout=5000)
            if not quotes_received.wait(max(0, deadline - time.monotonic())):
                with lock:
                    missing = sorted(wanted - seen.keys())
                raise TimeoutError(f"No pushed tick received for {missing}")

        with lock:
            quotes = dict(seen)
        print(json.dumps({"status": client.get_server_status(timeout=5000), "pushed_quotes": quotes}, ensure_ascii=False, indent=2))
    finally:
        client.stop()
        client.join()


if __name__ == "__main__":
    main()
