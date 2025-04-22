from dataclasses import dataclass
import socket
import selectors
import errno
import logging
from typing import Callable
from connection import message_codec
from connection.connection_handler import ConnectionHandler, ConnectionHandlerFactory, ConnectionHandlerType
from connection.ip_address import IpAddress
from enum import Enum

logger = logging.getLogger(__name__)

NO_TIMEOUT: int | None = None


class _TcpServerContextManager:
    def __init__(self, close_callback: Callable[[], None]) -> None:
        self.close_callback = close_callback
        
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close_callback()
        

class _ConnectionType(Enum):
    SERVER = 1
    CLIENT = 2


@dataclass
class _ConnectionData:
    connection_type: _ConnectionType
    handler_factory: ConnectionHandlerFactory
    handler: ConnectionHandler | None = None  # Only used for client connections


_LambdaConnectionHandlerFactory = Callable[[socket.socket, IpAddress, Callable[[], None]], ConnectionHandlerType]


class _LambdaConnectionHandlerFactoryWrapper(ConnectionHandlerFactory[ConnectionHandlerType]):
    def __init__(self, factory: _LambdaConnectionHandlerFactory) -> None:
        self.factory = factory
    
    def on_new_connection(self, socket_fd: socket.socket, ip_address: IpAddress,
                          close_callback: Callable[[], None]) -> ConnectionHandlerType:
        return self.factory(socket_fd, ip_address, close_callback)
    
    def on_connection_closed(self, connection_handler: ConnectionHandlerType) -> None:
        pass


class TcpConnectionManager:
    def __init__(self) -> None:
        self.socket_selector = selectors.DefaultSelector()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.socket_selector.close()

    def listen(self, ip_address: IpAddress, handler_factory: ConnectionHandlerFactory | _LambdaConnectionHandlerFactory) -> _TcpServerContextManager:
        """
        Starts a non-blocking TCP/IP server on the specified host and port.
        """
        if callable(handler_factory):
            handler_factory = _LambdaConnectionHandlerFactoryWrapper(handler_factory)
        
        logger.info(f"Starting server on {ip_address}")
        server_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow address reuse
        server_socket.bind((ip_address.host, ip_address.port))
        server_socket.listen()
        server_socket.setblocking(False)
        logger.info(f'Listening on {ip_address}')
        
        connection_data = _ConnectionData(_ConnectionType.SERVER, handler_factory)
        self.socket_selector.register(server_socket, selectors.EVENT_READ, data=connection_data)
        logger.info(f"Server started")
        
        close_callback = lambda: self._close_socket(server_socket, ip_address)
        return _TcpServerContextManager(close_callback)

    def connect(self, ip_address: IpAddress, 
                handler_factory: ConnectionHandlerFactory[ConnectionHandlerType] | _LambdaConnectionHandlerFactory) -> ConnectionHandlerType:
        if callable(handler_factory):
            handler_factory = _LambdaConnectionHandlerFactoryWrapper(handler_factory)
        
        logger.info(f"Connecting to {ip_address}")
        conn_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
        result = conn_socket.connect_ex((ip_address.host, ip_address.port))
        if result != 0:
            raise ConnectionError(f"Failed to connect to {ip_address}: {errno.errorcode[result]}")
        
        logger.info(f"Connected to {ip_address}")
        connection_handler = self._on_new_connection(conn_socket, ip_address, handler_factory)
        return connection_handler

    def wait_for_events(self, timeout_in_seconds: float | None = NO_TIMEOUT) -> int:
        """
        Check for events on the server socket and client sockets.
        Call this method in a loop to keep the server running.
        @param timeout_in_seconds: The time in seconds to wait for events before returning. Zero means non-blocking.
        @return: The number of events that occurred.
        """
        logger.debug(f"Checking for socket events with timeout {timeout_in_seconds}")
        events = self.socket_selector.select(timeout=timeout_in_seconds)
        logger.debug(f"Received {len(events)} events")
        for key, mask in events:
            assert isinstance(key.data, _ConnectionData)
            connection_data = key.data
            if connection_data.connection_type == _ConnectionType.SERVER:
                assert isinstance(key.fileobj, socket.socket)
                assert connection_data.handler_factory is not None
                self._accept_client(key.fileobj, connection_data.handler_factory)
            elif mask & selectors.EVENT_READ:
                self._read_from_socket(key)
            else:
                raise ValueError(f"Unexpected event mask {mask}")
        logger.debug(f"Done checking for socket events")
        return len(events)

    def _accept_client(self, socket_fd: socket.socket, handler_factory: ConnectionHandlerFactory) -> None:
        client_socket, address_info = socket_fd.accept()
        logger.info(f"Accepted connection from {address_info}")
        
        assert isinstance(address_info, tuple) and len(address_info) == 2
        ip_address = IpAddress(host=address_info[0], port=address_info[1])
        self._on_new_connection(client_socket, ip_address, handler_factory)

    def _on_new_connection(self, client_socket_fd: socket.socket, ip_address: IpAddress, 
                           handler_factory: ConnectionHandlerFactory[ConnectionHandlerType]) -> ConnectionHandlerType:
        logger.debug(f"Setting up client connection with {ip_address}")
        client_socket_fd.setblocking(False)
        
        close_callback = lambda: self._close_socket(client_socket_fd, ip_address)
        client_connection = handler_factory.on_new_connection(client_socket_fd, ip_address, close_callback)
        
        connection_data = _ConnectionData(_ConnectionType.CLIENT, handler_factory, handler=client_connection)
        self.socket_selector.register(client_socket_fd, selectors.EVENT_READ, data=connection_data)
        
        logger.debug(f"Done setting up client connection with {ip_address}")
        return client_connection

    def _read_from_socket(self, key: selectors.SelectorKey) -> None:
        socket_fd: socket.socket = key.fileobj  # type: ignore
        connection_data: _ConnectionData = key.data
        assert connection_data.connection_type == _ConnectionType.CLIENT
        assert connection_data.handler is not None
        client_connection = connection_data.handler
        ip_address = client_connection.ip_address
        logger.debug(f"Reading from socket of {ip_address}")
        
        try:
            message_type, message = message_codec.read_message(socket_fd)
            logger.debug(f"Received message type {message_type} with length {len(message)}")
        except (BrokenPipeError, ConnectionResetError) as e:
            logger.warning(f"Error while reading from {ip_address}: {str(e)}. Client will be disconnected")
            self._close_socket(socket_fd, ip_address)
            return

        try:
            client_connection.handle_message(message_type, message)
        except Exception as e:
            logger.exception(f"Error while handling message from {ip_address}. Client will be disconnected")
            self._close_socket(socket_fd, ip_address)
            return
        logger.debug(f"Done handling message")

    def _close_socket(self, socket_fd: socket.socket, ip_address: IpAddress) -> None:
        logger.debug(f"Closing socket on {ip_address}...")
        connection_data: _ConnectionData = self.socket_selector.get_key(socket_fd).data
        self.socket_selector.unregister(socket_fd)
        socket_fd.close()
        logger.info(f"Socket on {ip_address} closed")
        
        if connection_data.connection_type == _ConnectionType.CLIENT:
            assert connection_data.handler is not None
            client_connection = connection_data.handler
            client_connection.on_disconnect()
            connection_data.handler_factory.on_connection_closed(client_connection)
