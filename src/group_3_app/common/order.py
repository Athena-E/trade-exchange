from typing import List, Optional
from generated.proto.common_pb2 import Side

class Order:

    def __init__(self, order_id: int, order_book_id: int, timestamp: int, side: Side, price: float, quantity: int, on_behalf_of_username: str=None):
        self.order_id = order_id
        self.order_book_id = order_book_id
        self.timestamp = timestamp
        self.side = side
        self.price = price
        self.quantity = quantity
        self.trade_ids = []
        self.on_behalf_of_username = on_behalf_of_username
