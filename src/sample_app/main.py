import logging
from pathlib import Path
from application.application import BaseApplication
from connection.ip_address import IpAddress
from connection.tcp_connection_manager import TcpConnectionManager
from sample_app.connection_handler import PingPongClientHandlerFactory

logger = logging.getLogger(__name__)


class SampleApplication(BaseApplication):
    def _start(self) -> None:
        logger.info("Starting the sample application...")
        connection_handler_factory = PingPongClientHandlerFactory()
        tcp_connection_manager = TcpConnectionManager()
        
        server_ip_address = IpAddress(
            host=self._config["listenOn"]["host"],
            port=self._config["listenOn"]["port"])
        logger.info(f"Starting server on {server_ip_address}")
        with tcp_connection_manager.listen(server_ip_address, connection_handler_factory):
            logger.info("Server started.")
            logger.info("Running event loop until interrupted.")
            while True:
                tcp_connection_manager.wait_for_events()


def main() -> None:
    config_schema_path = Path(__file__).parent.parent / "application" / "config_schema.json"
    app = SampleApplication(config_schema=config_schema_path, app_name="sample_app")
    app.run()


if __name__ == "__main__":
    main()
