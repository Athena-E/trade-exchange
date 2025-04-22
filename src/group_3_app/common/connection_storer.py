from abc import ABC, abstractmethod
from group_3_app.connection_handler import ConnectionHandler
from google.protobuf.message import Message
from typing import TypeVar
ProtoMessage = TypeVar('ProtoMessage', bound=Message)

class ConnectionStorer(ABC):

    @abstractmethod
    def add_connection_handler(self, connection_handler: ConnectionHandler):
        return

    @abstractmethod
    def remove_connection_handler(self, connection_handler: ConnectionHandler):
        return

    @abstractmethod
    def broadcast_message(self, message_type: int, message: ProtoMessage):
        return
