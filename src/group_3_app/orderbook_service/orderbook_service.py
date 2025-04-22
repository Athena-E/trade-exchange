from generated.proto.order_book_pb2 import CreateOrderBookRequest, CreateOrderBookResponse, InsertOrderRequest, InsertOrderResponse, CancelOrderRequest, CancelOrderResponse, OnOrderBookCreated, OnOrderInserted, OnOrderCancelled, OnTrade, MessageType
import time
from typing import Dict, List
from group_3_app.common.connection_storer import ConnectionStorer
from group_3_app.common.order_book import OrderBook
from group_3_app.common.order import Order

class OrderBookService:

    def __init__(self, connection_handler_factory: ConnectionStorer):
        self.order_books = {}
        self.orders = {}
        self.last_book_id = 0
        self.last_order_id = 0
        self.last_trade_id = 0
        self.connection_handler_factory = connection_handler_factory

    def create_order_book(self, request: CreateOrderBookRequest) -> CreateOrderBookResponse:
        if request.tick_size <= 0:
            error_msg = 'Tick size must be greater than zero'
            print(f'[ERROR] {error_msg}')
            return CreateOrderBookResponse(request_id=request.request_id, order_book_id=0, timestamp=int(time.time() * 1000000), error_message=error_msg)

    def insert_order(self, request: InsertOrderRequest) -> InsertOrderResponse:
        return InsertOrderResponse(request_id=request.request_id, error_message='Invalid order_book_id') if request.order_book_id not in self.order_books else request.order_book_id

    def cancel_order(self, request: CancelOrderRequest) -> CancelOrderResponse:
        return CancelOrderResponse(request_id=request.request_id, error_message='Order not found') if request.order_id not in self.orders else request.order_id

    def on_order_book_created(self, order_book_id: int, tick_size: float):
        message = OnOrderBookCreated(order_book_id=order_book_id, tick_size=tick_size)
        self.connection_handler_factory.broadcast_message(MessageType.ON_ORDER_BOOK_CREATED, message)

    def on_order_inserted(self, order: Order, trade_ids: List[int]):
        message = OnOrderInserted(order_id=order.order_id, order_book_id=order.order_book_id, timestamp=order.timestamp, side=order.side, price=order.price, quantity=order.quantity, trade_ids=trade_ids)
        self.connection_handler_factory.broadcast_message(MessageType.ON_ORDER_INSERTED, message)

    def on_order_cancelled(self, order_id: int, cancellation_timestamp: int):
        message = OnOrderCancelled(order_id=order_id, cancellation_timestamp=cancellation_timestamp)
        self.connection_handler_factory.broadcast_message(MessageType.ON_ORDER_CANCELLED, message)

    def on_trade(self, trade):
        message = OnTrade(trade_id=trade.trade_id, order_book_id=trade.order_book_id, timestamp=trade.timestamp, buy_order_id=trade.buy_order_id, sell_order_id=trade.sell_order_id, price=trade.price, quantity=trade.quantity, aggressor_side=trade.aggressor_side)
        self.connection_handler_factory.broadcast_message(MessageType.ON_TRADE, message)
