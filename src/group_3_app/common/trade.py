from generated.proto.common_pb2 import Side

class Trade:

    def __init__(self, trade_id: int, order_book_id: int, timestamp: int, buy_order_id: int, sell_order_id: int, price: float, quantity: int, aggressor_side: Side):
        self.trade_id = trade_id
        self.order_book_id = order_book_id
        self.timestamp = timestamp
        self.buy_order_id = buy_order_id
        self.sell_order_id = sell_order_id
        self.price = price
        self.quantity = quantity
        self.aggressor_side = aggressor_side
