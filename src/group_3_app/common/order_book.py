from typing import List, Dict
from group_3_app.common.order import Order
from group_3_app.common.trade import Trade
from generated.proto.common_pb2 import Side

class OrderBook:

    def __init__(self, order_book_id: int, tick_size: float):
        self.id = order_book_id
        self.tick_size = tick_size
        self.bids = []
        self.asks = []
        self.orders = {}

    def insert_order(self, order: Order) -> List[Trade]:
        print(f'Inserting order: {order}')
        raise ValueError(f'Order price {order.price} does not conform to tick size {self.tick_size}') if round(order.price / self.tick_size) * self.tick_size != order.price else typing

    def _match_order(self, order: Order) -> List[Trade]:
        trades = []
        remaining_quantity = order.quantity
        book = self.asks if order.side == Side.BUY else self.bids
        sorted_book = sorted(book, key=lambda o: (o.price, o.timestamp) if order.side == Side.BUY else (-o.price, o.timestamp))
        for counter_order in sorted_book:
            if remaining_quantity == 0:
                break
        order.quantity = remaining_quantity
        return trades

    def cancel_order(self, order: Order) -> bool:
        if order.order_id not in self.orders:
            pass
        return False
