"""Start the Windows VeighNa Trader client using the remote RPC gateway."""

from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import MainWindow, create_qapp
from vnpy_rpcservice import RpcGateway


def main() -> None:
    """Launch the GUI; configure the RPC server address in the Connect dialog."""
    app = create_qapp()
    event_engine = EventEngine()
    main_engine = MainEngine(event_engine)
    main_engine.add_gateway(RpcGateway)

    window = MainWindow(main_engine, event_engine)
    window.showMaximized()
    app.exec()


if __name__ == "__main__":
    main()
