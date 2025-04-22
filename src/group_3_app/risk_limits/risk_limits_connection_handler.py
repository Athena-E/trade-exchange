import logging
from typing import Dict
import socket
from typing import Callable
from connection import message_codec
from connection.connection_handler import ConnectionHandler, ConnectionHandlerFactory
from connection.ip_address import IpAddress
from group_3_app.risk_limits.risk_limits_service import RiskLimitsService
from generated.proto.risk_limits_pb2 import MessageType as RiskLimitsMessageType, InsertOrderRequest, CancelOrderRequest, SetUserRiskLimitsRequest, GetInstrumentRiskLimitsRequest, SetInstrumentRiskLimitsRequest, GetUserRiskLimitsRequest
from generated.proto.info_pb2 import MessageType as InfoMessageType, OnInstrument
from generated.proto.order_book_pb2 import CancelOrderResponse as ObCancelOrderResponse, MessageType as OrderBookServiceMessageType, InsertOrderResponse as OBInsertOrderResponse
logger = logging.getLogger(__name__)

class RiskLimitsConnectionHandler(ConnectionHandler):

    def __init__(self, socket_fd: socket.socket, ip_address: IpAddress, close_callback: Callable[[], None], service: RiskLimitsService):
        super().__init__(socket_fd, ip_address, close_callback)
        self.service = service
        self.username = None

    def handle_message(self, message_type: int, message: bytes) -> None:
        """Handles incoming messages"""
        logger.info(f'Received message of type {message_type}')
        logger.debug(f'Message: {str(message)}')
        if message_type == RiskLimitsMessageType.LOGIN_REQUEST:
            self.username = message.username
            self.service.add_client(message.username, self)
            logger.info(f"User '{self.username}' logged in from {self.ip_address}")
        return None

    def _send_proto(self, message_type: int, proto_msg) -> None:
        encoded = message_codec.encode_message(message_type, proto_msg.SerializeToString())
        self._send_message(encoded)

    def on_disconnect(self) -> None:
        """Handles cleanup when a client disconnects"""
        logger.info(f'Client {self.ip_address} disconnected')
        if self.username:
            self.service.remove_client(self.ip_address)
            logger.info(f"User '{self.username}' removed from active connections")
        return None

class RiskLimitsConnectionHandlerFactory(ConnectionHandlerFactory[RiskLimitsConnectionHandler]):

    def __init__(self):
        self.service = None
        self.insert_order_request_id_to_connection_handler = {}
        self.cancel_order_request_id_to_connection_handler = {}

    def on_new_connection(self, socket_fd: socket.socket, ip_address: IpAddress, close_callback: Callable[[], None]) -> RiskLimitsConnectionHandler:
        return RiskLimitsConnectionHandler(socket_fd, ip_address, close_callback, self.service)

    def on_connection_closed(self, connection_handler: RiskLimitsConnectionHandler):
        return

    def add_insert_order_request_connection_handler(self, request_id: int, connection_handler: RiskLimitsConnectionHandler):
        self.insert_order_request_id_to_connection_handler[request_id] = connection_handler
