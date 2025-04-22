import logging
from connection.connection_handler import ConnectionHandler, ConnectionHandlerFactory
from connection import message_codec
from connection.ip_address import IpAddress
import socket
from typing import Callable, List, Optional, TypeVar
from google.protobuf.message import Message
from generated.proto.order_book_pb2 import CreateOrderBookRequest, CreateOrderBookResponse, InsertOrderRequest, InsertOrderResponse, CancelOrderRequest, CancelOrderResponse, MessageType
from group_3_app.common.connection_storer import ConnectionStorer
from group_3_app.orderbook_service.orderbook_service import OrderBookService
logger = logging.getLogger(__name__)
ProtoMessage = TypeVar('ProtoMessage', bound=Message)

class OrderBookConnectionHandler(ConnectionHandler):

    def __init__(self, socket_fd, ip_address, close_callback, orderbook_service: OrderBookService):
        super().__init__(socket_fd, ip_address, close_callback)
        self.service = orderbook_service

    def handle_message(self, message_type: int, message: bytes) -> None:
        try:
            logger.info(f'Received message type {message_type} from {self.ip_address}')
            if message_type == MessageType.CREATE_ORDER_BOOK_REQUEST:
                request = self._deserialize_message(CreateOrderBookRequest, message)
                response = self.service.create_order_book(request)
                self.send_message(MessageType.CREATE_ORDER_BOOK_RESPONSE, response)
            return None
        except Exception as e:
            logger.exception(f'Error while handling message: {e}')

    def on_disconnect(self) -> None:
        logger.info(f'Client {self.ip_address} disconnected')

class OrderBookConnectionHandlerFactory(ConnectionHandlerFactory[OrderBookConnectionHandler], ConnectionStorer):

    def __init__(self):
        self.connection_handlers = []
        self.service = None

    def on_new_connection(self, socket_fd: socket.socket, ip_address: IpAddress, close_callback: Callable[[], None]) -> OrderBookConnectionHandler:
        orderbook_connection_handler = OrderBookConnectionHandler(socket_fd, ip_address, close_callback, self.service)
        self.add_connection_handler(orderbook_connection_handler)
        return orderbook_connection_handler

    def on_connection_closed(self, connection_handler: OrderBookConnectionHandler):
        self.remove_connection_handler(connection_handler)

    def add_connection_handler(self, connection_handler: ConnectionHandler):
        self.connection_handlers.append(connection_handler)

    def remove_connection_handler(self, connection_handler: ConnectionHandler):
        if connection_handler in self.connection_handlers:
            self.connection_handlers.remove(connection_handler)
            logger.info(f'Removed connection handler for {connection_handler.ip_address}')
        return None

    def broadcast_message(self, message_type: int, message: ProtoMessage):
        for connection in self.connection_handlers:
            connection.send_message(message_type, message)
