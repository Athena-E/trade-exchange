from group_3_app.connection_handler import ConnectionHandler
from typing import List
from group_3_app.common.connection_storer import ConnectionStorer

class SubscriptionStorer(ConnectionStorer):

    def __init__(self):
        self.connection_handlers = {}

    def add_connection_handler(self, instrument_symbol: str, connection_handler: ConnectionHandler):
        self.connection_handlers[instrument_symbol].append(connection_handler)

    def remove_connection_handler(self, instrument_symbol: str, connection_handler: ConnectionHandler):
        self.connection_handlers[instrument_symbol].remove(connection_handler)

    def broadcast_message(self, message_type: int, message, instrument_symbol: str):
        subscribed_handlers = self.connection_handlers[instrument_symbol]
        for connection_handler in subscribed_handlers:
            connection_handler.send_message(message_type, message)

class TOBSubscriptions(SubscriptionStorer):
    __static_attributes__ = ()

class PDSubscriptions(SubscriptionStorer):
    __static_attributes__ = ()
