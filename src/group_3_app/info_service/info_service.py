from typing import List
from group_3_app.common.order import Order
from group_3_app.common.order_book import OrderBook
from generated.proto.common_pb2 import Instrument, LoginRequest, LoginResponse
from generated.proto.info_pb2 import CreateInstrumentRequest, CreateInstrumentResponse, OrderBookSubscribeRequest, OrderBookSubscribeResponse, SubscriptionType, OnPriceDepthBook, OnTopOfBook, OnInstrument, PriceLevel, MessageType
from generated.proto.order_book_pb2 import CreateOrderBookResponse, CreateOrderBookRequest, OnOrderInserted, OnOrderCancelled, CreateOrderBookRequest, MessageType as OrderBookServiceMessageType
from generated.proto.info_pb2 import OnTrade as InfoOnTrade
from generated.proto.order_book_pb2 import OnTrade as OBOnTrade
from generated.proto.order_book_pb2 import MessageType as OrderBookServiceMessageType
import time
import logging
import sys
from group_3_app.info_service.subscriptions import PDSubscriptions, TOBSubscriptions
from group_3_app.common.connection_storer import ConnectionStorer
logger = logging.getLogger(__name__)

class InfoService:

    def __init__(self, connection_storer: ConnectionStorer):
        self.orderbook_connection_handler = None
        self.tob_subscribers = TOBSubscriptions()
        self.pd_subscribers = PDSubscriptions()
        self.connection_storer = connection_storer
        self.top_of_books = {}
        self.order_books = {}
        self.order_book_ids_to_instruments = {}
        self.order_ids_to_order_book_ids = {}
        self.next_create_order_book_request_id = 0
        self.create_order_book_request_id_to_create_instrument_request = {}

    def login_request(self, login_request: LoginRequest) -> LoginResponse:
        message = LoginResponse(request_id=login_request.request_id, error_message='')
        return message

    def create_instrument_request(self, create_instrument_request: CreateInstrumentRequest):
        self.create_order_book_request_id_to_create_instrument_request[self.next_create_order_book_request_id] = create_instrument_request
        self.send_create_order_book_request(create_instrument_request)

    def create_order_book_response(self, create_order_book_response: CreateOrderBookResponse):
        create_instrument_request = self.create_order_book_request_id_to_create_instrument_request[create_order_book_response.request_id]
        order_book_id = create_order_book_response.order_book_id
        new_instrument = create_instrument_request.instrument
        logger.info(f'New Instrument: {new_instrument}')
        tick_size = create_instrument_request.tick_size
        self.__add_new_instrument_mappings(new_instrument, order_book_id, tick_size)
        created_timestamp = int(time.time() * 1000000)
        message = OnInstrument(instrument=new_instrument, created_timestamp=created_timestamp, tick_size=tick_size, order_book_id=order_book_id)
        self.connection_storer.broadcast_message(MessageType.ON_INSTRUMENT, message)
        logger.debug('info service clients notified of new instrument')
        self.__respond_to_create_instrument_request(create_instrument_request, order_book_id, created_timestamp)

    def __add_new_instrument_mappings(self, new_instrument: Instrument, order_book_id: int, tick_size: int) -> Instrument:
        instrument_symbol = new_instrument.symbol
        self.order_books[order_book_id] = OrderBook(order_book_id, tick_size)
        self.top_of_books[order_book_id] = (None, None)
        self.order_book_ids_to_instruments[order_book_id] = instrument_symbol
        logger.info(f'new instrument -{instrument_symbol}- added to info service')

    def __respond_to_create_instrument_request(self, create_instrument_request: CreateInstrumentRequest, order_book_id: int, created_timestamp: int):
        create_instrument_response = CreateInstrumentResponse(request_id=create_instrument_request.request_id, error_message='', created_timestamp=created_timestamp, order_book_id=order_book_id)
        instrument_request_connection_handler = self.connection_storer.create_instrument_request_id_to_connection_handler[create_instrument_request.request_id]
        instrument_request_connection_handler.send_message(MessageType.CREATE_INSTRUMENT_RESPONSE, create_instrument_response)
        logger.info(f'Info Service sent create instrument response for order book id {order_book_id}')

    def order_book_subscribe_request(self, order_book_subscribe_request: OrderBookSubscribeRequest) -> OrderBookSubscribeResponse:
        if order_book_subscribe_request.subscription_type == SubscriptionType.TOP_OF_BOOK:
            logger.info('new top of book subscriber added')
        return OrderBookSubscribeResponse(request_id=order_book_subscribe_request.request_id, error_message='')

    def on_order_inserted(self, on_order_inserted: OnOrderInserted):
        order_book_id = on_order_inserted.order_book_id
        self.order_ids_to_order_book_ids[on_order_inserted.order_id] = order_book_id
        logger.info(f'Adding new order to order book with id {order_book_id}')
        order_book = self.order_books[order_book_id]
        order_book.insert_order()
        logger.info(f'Order added to order book with id {order_book_id}')
        if self.__update_top_of_book(order_book):
            logger.info('Inserting order caused top of book to change')
            self.__on_top_of_book(order_book_id)
        self.__on_price_depth_book()

    def on_order_cancelled(self, on_order_cancelled: OnOrderCancelled):
        order_book_id = self.order_ids_to_order_book_ids[on_order_cancelled.order_id]
        order_book = self.order_books[order_book_id]
        logger.info(f'Cancelling order in order book with id {order_book_id}')
        order_book.cancel_order()
        if self.__update_top_of_book(order_book):
            logger.info('Cancelling order cause top of book to change')
            self.__on_top_of_book(order_book_id)
        self.__on_price_depth_book()

    def on_trade(self, ob_on_trade: OBOnTrade) -> None:
        logger.info(f'Info Service broadcasting on trade message for trade id {ob_on_trade.trade_id}')
        message = InfoOnTrade(trade_id=ob_on_trade.trade_id, instrument_symbol=self.order_book_ids_to_instruments[ob_on_trade.order_book_id], timestamp=ob_on_trade.timestamp, price=ob_on_trade.price, quantity=ob_on_trade.quantity, aggressor_side=ob_on_trade.aggressor_side)
        self.connection_storer.broadcast_message(MessageType.ON_TRADE, message)

    def __update_top_of_book(self, order_book: OrderBook) -> bool:
        logger.debug('Info service checking for update to top of book')
        new_best_bid = order_book.get_best_bid()
        new_best_ask = order_book.get_best_ask()
        old_best_bid, old_best_ask = self.top_of_books[order_book.id]
        if new_best_bid != old_best_bid or new_best_ask != old_best_ask:
            self.top_of_books[order_book.id] = (new_best_bid, new_best_ask)
        return True

    def __on_top_of_book(self, order_book_id: int) -> None:
        timestamp = int(time.time() * 1000000)
        instrument_symbol = self.order_book_ids_to_instruments[order_book_id]
        new_best_bid = self.top_of_books[order_book_id][0]
        new_best_ask = self.top_of_books[order_book_id][1]
        bid_price_level = PriceLevel(price=new_best_bid.price, quantity=new_best_bid.quantity)
        ask_price_level = PriceLevel(price=new_best_ask.price, quantity=new_best_ask.quantity)
        message = OnTopOfBook(instrument_symbol=instrument_symbol, timestamp=timestamp, best_bid=bid_price_level, best_ask=ask_price_level)
        logger.info('Info Service multi casting a change in top of book')
        self.tob_subscribers.broadcast_message(MessageType.ON_TOP_OF_BOOK, message, instrument_symbol)

    def __on_price_depth_book(self, order_book: OrderBook) -> None:
        order_book_id = order_book.id
        instrument_symbol = self.order_book_ids_to_instruments[order_book_id]
        timestamp = int(time.time() * 1000000)
        message = OnPriceDepthBook(instrument_symbol=instrument_symbol, timestamp=timestamp, bids=order_book.bids, asks=order_book.asks)
        logger.info('Info Service multi casting a change in price depth book')
        self.pd_subscribers.broadcast_message(MessageType.ON_PRICE_DEPTH_BOOK, message)

    def send_create_order_book_request(self, instrument_request):
        create_order_book_request = CreateOrderBookRequest(request_id=self.next_create_order_book_request_id, tick_size=instrument_request.tick_size)
        self.next_create_order_book_request_id += 1
        self.orderbook_connection_handler.send_message(OrderBookServiceMessageType.CREATE_ORDER_BOOK_REQUEST, create_order_book_request)
