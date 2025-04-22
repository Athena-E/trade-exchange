import logging
import socket
from typing import Callable
from connection import message_codec
from connection.connection_handler import ConnectionHandler, ConnectionHandlerFactory
from connection.ip_address import IpAddress

logger = logging.getLogger(__name__)


class PingPongClientHandler(ConnectionHandler):
    def on_disconnect(self) -> None:
        logger.info(f"Client {self.ip_address} disconnected")

    def handle_message(self, message_type: int, message: bytes) -> None:
        logger.info(f"Received message of type {message_type}")
        logger.debug(f"Message: {str(message)}")
        
        logger.info("Bouncing message back to client")
        encoded_message = message_codec.encode_message(message_type, message)
        self._send_message(encoded_message)
        logger.info("Message bounced back")


class PingPongClientHandlerFactory(ConnectionHandlerFactory[PingPongClientHandler]):
    def on_new_connection(self, socket_fd: socket.socket, ip_address: IpAddress, 
                          close_callback: Callable[[], None]) -> PingPongClientHandler:
        return PingPongClientHandler(socket_fd, ip_address, close_callback)

    def on_connection_closed(self, connection_handler: PingPongClientHandler):
        pass
