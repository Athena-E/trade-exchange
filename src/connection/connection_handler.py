import logging
import socket
from abc import ABC, abstractmethod
from typing import Callable, Generic, Type, TypeVar

from connection import message_codec
from connection.ip_address import IpAddress
from google.protobuf.message import Message

logger = logging.getLogger(__name__)

ProtoMessage = TypeVar('ProtoMessage', bound=Message)

class ConnectionHandler(ABC):
    def __init__(self, socket_fd: socket.socket, ip_address: IpAddress, 
                 close_callback: Callable[[], None]) -> None:
        self.socket_fd = socket_fd
        self.ip_address = ip_address
        self.close_callback = close_callback

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        logger.info(f"Closing connection to {self.ip_address}...")
        self.close_callback()

    @abstractmethod
    def handle_message(self, message_type: int, message: bytes) -> None:
        pass

    @abstractmethod
    def on_disconnect(self) -> None:
        pass

    def send_message(self, message_type: int, message: ProtoMessage) -> None:
        logger.info(f"Preparing to send message of type {message_type} to {self.ip_address}...")
        logger.debug(f"Message: {message}")
        try:
            serialized_message = message.SerializeToString()
            encoded_message = message_codec.encode_message(message_type, serialized_message)
            self._send_message(encoded_message)
            logger.info(f"Sent message successfully")
        except socket.error as e:
            logger.exception(f"Failed to send message to {self.ip_address}")
            logger.info(f"Closing connection to {self.ip_address}...")
            self.close_callback()

    def _send_message(self, encoded_message: bytes) -> None:
        logger.debug(f"Sending message of {len(encoded_message)} bytes")
        self.socket_fd.sendall(encoded_message)

    @staticmethod
    def _deserialize_message(proto_message_type: type[ProtoMessage], message: bytes) -> ProtoMessage:
        proto_message = proto_message_type()
        proto_message.ParseFromString(message)
        logger.debug(f"Deserialized message of type {proto_message_type.__name__}: {proto_message}")
        return proto_message
    

ConnectionHandlerType = TypeVar('ConnectionHandlerType', bound=ConnectionHandler)

class ConnectionHandlerFactory(ABC, Generic[ConnectionHandlerType]):
    @abstractmethod
    def on_new_connection(self, socket_fd: socket.socket, ip_address: IpAddress, 
                          close_callback: Callable[[], None]) -> ConnectionHandlerType:
        pass

    @abstractmethod
    def on_connection_closed(self, connection_handler: ConnectionHandlerType) -> None:
        pass

class LambdaConnectionHandlerFactory(ConnectionHandlerFactory[ConnectionHandlerType]):
    def __init__(self, on_new_connection_lambda: Callable[[socket.socket, IpAddress, Callable[[], None]], ConnectionHandlerType]) -> None:
        self._on_new_connection_lambda = on_new_connection_lambda

    def on_new_connection(self, socket_fd: socket.socket, ip_address: IpAddress, close_callback: Callable[[], None]) -> ConnectionHandlerType:
        return self._on_new_connection_lambda(socket_fd, ip_address, close_callback)

    def on_connection_closed(self, connection_handler: ConnectionHandlerType) -> None:
        # No-op by default; can be extended if needed
        pass
