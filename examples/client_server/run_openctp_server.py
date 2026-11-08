"""Run a headless CTP + RPC service against OpenCTP's TTS 7x24 environment."""

import argparse
import importlib.metadata
import logging
import os
import re
import signal
import socket
import tempfile
from pathlib import Path
from threading import Event

LOGGER = logging.getLogger("openctp_server")
OPENCTP_TD_DEFAULT = "tcp://trading.openctp.cn:30001"
OPENCTP_MD_DEFAULT = "tcp://trading.openctp.cn:30011"
RPC_PORTS = (2014, 4102)


def parse_endpoint(endpoint: str) -> tuple[str, int]:
    """Return hostname and port for a CTP TCP endpoint."""
    protocol, address = endpoint.split("://", maxsplit=1)
    if protocol != "tcp":
        raise ValueError(f"Unsupported endpoint protocol: {protocol}")
    host, port = address.rsplit(":", maxsplit=1)
    return host, int(port)


def check_tcp_endpoint(endpoint: str, timeout: float = 5.0) -> None:
    """Raise OSError if a remote TCP front is not reachable."""
    host, port = parse_endpoint(endpoint)
    with socket.create_connection((host, port), timeout=timeout):
        LOGGER.info("TCP reachable: %s", endpoint)


def check_tts_libraries(api_dir: Path, ctp_version: str) -> None:
    """Require both loaded CTP shared libraries to be matching OpenCTP TTS builds."""
    path = api_dir
    expected = ".".join(ctp_version.split(".")[:3])
    for library in ("libthostmduserapi_se.so", "libthosttraderapi_se.so"):
        content = (path / library).read_bytes()
        versions = set(re.findall(rb"openctp-tts v([0-9]+\.[0-9]+\.[0-9]+)", content))
        if versions != {expected.encode("ascii")}:
            found = sorted(item.decode("ascii") for item in versions)
            raise RuntimeError(f"{library} must be OpenCTP TTS {expected}; found {found or 'a non-TTS library'}")
        LOGGER.info("Verified OpenCTP TTS %s library: %s", expected, library)


def check_tts_api_runtime(ctp_version: str) -> None:
    """Create both native APIs without logging in and verify the trader API version."""
    from vnpy_ctp.api.vnctpmd import MdApi
    from vnpy_ctp.api.vnctptd import TdApi

    expected = ".".join(ctp_version.split(".")[:3])
    with tempfile.TemporaryDirectory() as api_dir:
        td_api = TdApi()
        td_api.createFtdcTraderApi(f"{api_dir}/", False)
        try:
            actual = td_api.getApiVersion()
            if actual != f"openctp-tts v{expected}":
                raise RuntimeError(f"Unexpected trader API version: {actual}")
            LOGGER.info("Trader API runtime reports %s", actual)
        finally:
            td_api.release()

        md_api = MdApi()
        md_api.createFtdcMdApi(f"{api_dir}/", False)
        md_api.release()
        LOGGER.info("Market-data API native library loaded without login")


def check_installation() -> int:
    """Check native gateway imports and public OpenCTP front connectivity."""
    import vnpy
    import vnpy_ctp
    import vnpy_rpcservice
    from vnpy_ctp import CtpGateway
    import vnpy_ctp.api
    from vnpy_rpcservice import RpcGateway, RpcServiceApp

    LOGGER.info("vn.py=%s; vnpy_ctp=%s; vnpy_rpcservice=%s", vnpy.__version__, vnpy_ctp.__version__, vnpy_rpcservice.__version__)
    LOGGER.info("Loaded CtpGateway=%s, RpcGateway=%s, RpcServiceApp=%s", CtpGateway, RpcGateway, RpcServiceApp)
    ctp_version = importlib.metadata.version("vnpy_ctp")
    check_tts_libraries(Path(vnpy_ctp.api.__file__).parent, ctp_version)
    check_tts_api_runtime(ctp_version)
    for endpoint in (os.getenv("OPENCTP_TD_FRONT", OPENCTP_TD_DEFAULT), os.getenv("OPENCTP_MD_FRONT", OPENCTP_MD_DEFAULT)):
        check_tcp_endpoint(endpoint)
    LOGGER.info("Install/front connectivity checks passed; no account login or orders were attempted.")
    return 0


def log_event(event: object) -> None:
    """Write gateway and RPC events to stdout without exposing credentials."""
    log = event.data
    LOGGER.info("%s %s", log.time, log.msg)


def build_ctp_setting() -> dict[str, str]:
    """Build CTP settings from environment variables, never from source files."""
    user_id = os.getenv("OPENCTP_USER_ID", "").strip()
    password = os.getenv("OPENCTP_PASSWORD", "")
    if not user_id or not password:
        raise RuntimeError("Set OPENCTP_USER_ID and OPENCTP_PASSWORD from your OpenCTP account before connecting.")

    return {
        "用户名": user_id,
        "密码": password,
        "经纪商代码": os.getenv("OPENCTP_BROKER_ID", "9999"),
        "交易服务器": os.getenv("OPENCTP_TD_FRONT", OPENCTP_TD_DEFAULT),
        "行情服务器": os.getenv("OPENCTP_MD_FRONT", OPENCTP_MD_DEFAULT),
        "产品名称": "",
        "授权编码": "",
        "产品信息": "",
        "柜台环境": "测试",
    }


def build_rpc_addresses(bind_ip: str) -> tuple[str, str]:
    """Bind RPC only to loopback or an explicitly selected private interface."""
    if bind_ip in {"0.0.0.0", "::"}:
        raise ValueError("Wildcard RPC binds are refused; use 127.0.0.1 or a private/VPN interface address.")
    return f"tcp://{bind_ip}:{RPC_PORTS[0]}", f"tcp://{bind_ip}:{RPC_PORTS[1]}"


def main() -> int:
    """Start the local trading process and its RPC endpoints."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check imports and OpenCTP TCP ports; do not log in")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.check:
        return check_installation()

    setting = build_ctp_setting()
    bind_ip = os.getenv("OPENCTP_RPC_BIND_IP", "127.0.0.1").strip()
    rep_address, pub_address = build_rpc_addresses(bind_ip)

    from vnpy.event import EventEngine
    from vnpy.trader.engine import MainEngine
    from vnpy.trader.event import EVENT_LOG
    from vnpy_ctp import CtpGateway
    from vnpy_rpcservice import RpcServiceApp
    from vnpy_rpcservice.rpc_service.engine import EVENT_RPC_LOG, RpcEngine

    event_engine = EventEngine()
    event_engine.register(EVENT_LOG, log_event)
    event_engine.register(EVENT_RPC_LOG, log_event)
    main_engine = MainEngine(event_engine)
    main_engine.add_gateway(CtpGateway)
    rpc_engine: RpcEngine = main_engine.add_app(RpcServiceApp)

    if not rpc_engine.start(rep_address, pub_address):
        main_engine.close()
        raise RuntimeError("Could not start RpcService")

    main_engine.connect(setting, "CTP")
    stopped = Event()
    signal.signal(signal.SIGINT, lambda *_: stopped.set())
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    LOGGER.info("OpenCTP gateway and RPC service started; Ctrl+C for graceful shutdown.")
    try:
        while not stopped.wait(1):
            pass
    finally:
        main_engine.close()
        LOGGER.info("OpenCTP gateway and RPC service stopped.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        LOGGER.error("Startup failed: %s", exc)
        raise
