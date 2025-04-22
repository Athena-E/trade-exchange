import logging
import socket
from typing import Callable, List
from connection.connection_handler import ConnectionHandler, ConnectionHandlerFactory
from connection.ip_address import IpAddress
from connection import message_codec
from group_3_app.info_service.info_service import InfoService
from generated.proto.info_pb2 import MessageType, CreateInstrumentRequest, OrderBookSubscribeRequest, SubscriptionType
from generated.proto.common_pb2 import LoginRequest
from generated.proto.order_book_pb2 import MessageType as OrderBookServiceMessageType
from generated.proto.order_book_pb2 import OnOrderInserted, OnOrderCancelled, CreateOrderBookResponse
from generated.proto.order_book_pb2 import OnTrade as ObOnTrade
from group_3_app.common.connection_storer import ConnectionStorer
logger = logging.getLogger(__name__)

class InfoServiceConnectionHandler(ConnectionHandler):

    def __init__(self, socket_fd: socket.socket, ip_address: IpAddress, close_callback: Callable[[], None], service: InfoService):
        super().__init__(socket_fd, ip_address, close_callback)
        self.service = service

    def handle_message(self, message_type: int, message: bytes) -> None:
        """Handles incoming messages."""
        logger.info(f'Received message of type {message_type} from {self.ip_address}')
        if message_type == MessageType.LOGIN_REQUEST:
            login_request = self._deserialize_message(LoginRequest, message)
            response = self.service.login_request(login_request)
            logger.info(f"User '{login_request.username}' logged in from {self.ip_address}")
            self.send_message(MessageType.LOGIN_RESPONSE, response)
        return None

    def on_disconnect(self) -> None:
        """Handles cleanup when a client disconnects."""
        logger.info(f'Client {self.ip_address} disconnected')

class InfoServiceConnectionHandlerFactory(ConnectionHandlerFactory[InfoServiceConnectionHandler], ConnectionStorer):

    def __init__(self):
        self.connection_handlers = []
        self.create_instrument_request_id_to_connection_handler = {}
        self.service = None

    def add_connection_handler(self, connection_handler: ConnectionHandler):
        self.connection_handlers.append(connection_handler)

    def remove_connection_handler(self, connection_handler: ConnectionHandler):
        self.connection_handlers.remove(connection_handler)

    def broadcast_message(self, message_type, message):
        logger.info(f'Info Service braodcasting message: {message}')
        for connection_handler in self.connection_handlers:
            connection_handler.send_message(message_type, message)

    def add_create_instrument_request_connection_handler(self, create_instrument_request_id: int, connection_handler: ConnectionHandler):
        self.create_instrument_request_id_to_connection_handler[create_instrument_request_id] = connection_handler

    def on_new_connection(self, socket_fd: socket.socket, ip_address: IpAddress, close_callback: Callable[[], None]) -> InfoServiceConnectionHandler:
        info_service_connection_handler = InfoServiceConnectionHandler(socket_fd, ip_address, close_callback, self.service)
        self.add_connection_handler(info_service_connection_handler)
        return info_service_connection_handler

    def on_connection_closed(self, info_service_connection_handler: InfoServiceConnectionHandler):
        self.remove_connection_handler(info_service_connection_handler)
