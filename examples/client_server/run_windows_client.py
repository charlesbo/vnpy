"""Start the Windows VeighNa Trader client using the remote RPC gateway."""

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy_rpcservice import RpcGateway
from vnpy_optionmaster import OptionMasterApp
from vnpy_spreadtrading import SpreadTradingApp


def main() -> None:
    """Launch Trader with RPC, option-pricing and multi-leg spread applications."""
    app = create_qapp()
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    main_engine.add_gateway(RpcGateway)
    main_engine.add_app(OptionMasterApp)
    main_engine.add_app(SpreadTradingApp)

    window = MainWindow(main_engine, event_engine)
    window.showMaximized()
    app.exec()


if __name__ == "__main__":
    main()
