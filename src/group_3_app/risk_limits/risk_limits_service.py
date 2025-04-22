import logging
from collections import defaultdict
from typing import Dict, Optional, Set, Any
import time
from connection.ip_address import IpAddress
from generated.proto.common_pb2 import Side
from generated.proto.common_pb2 import Instrument, LoginRequest, LoginResponse
from generated.proto.risk_limits_pb2 import InsertOrderRequest, InsertOrderResponse, UserRiskLimits, InstrumentRiskLimits, CancelOrderRequest, CancelOrderResponse, GetUserRiskLimitsRequest, GetUserRiskLimitsResponse, SetUserRiskLimitsRequest, SetUserRiskLimitsResponse, GetInstrumentRiskLimitsRequest, GetInstrumentRiskLimitsResponse, SetInstrumentRiskLimitsRequest, SetInstrumentRiskLimitsResponse, UserRiskLimits, RollingWindowLimit, MessageType
from generated.proto.order_book_pb2 import InsertOrderRequest as OBInsertOrderRequest, InsertOrderResponse as OBInsertOrderResponse, CancelOrderRequest as OBCancelOrderRequest, CancelOrderResponse as OBCancelOrderResponse, MessageType as OBMessageType
from generated.proto.info_pb2 import OnInstrument
from group_3_app.risk_limits.rolling_window_order_limit import RollingOrderLimit
from group_3_app.risk_limits.rolling_window_message_rate_limit import RollingMessageRateLimit
from group_3_app.common.connection_storer import ConnectionStorer
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RiskLimitsService:

    def __init__(self, connection_storer: ConnectionStorer):
        self.connection_storer = connection_storer
        self.user_per_instrument_risk_limits = defaultdict(lambda: defaultdict(InstrumentRiskLimits))
        self.total_user_risk_limits = defaultdict(UserRiskLimits)
        self.instrument_symbols = set()
        self.ip_to_username = defaultdict(str)
        self.user_outstanding_quantity = defaultdict(int)
        self.user_instrument_outstanding_quantity = defaultdict(lambda: defaultdict(int))
        self.user_instrument_outstanding_amount = defaultdict(lambda: defaultdict(int))
        self.user_instrument_qty_rolling_window = defaultdict(RollingOrderLimit)
        self.user_instrument_amount_rolling_window = defaultdict(RollingOrderLimit)
        self.user_message_rate_rolling_window = defaultdict(RollingMessageRateLimit)
        self.req_id_to_insert_order_req = defaultdict(InsertOrderRequest)
        self.order_id_to_insert_order_req = defaultdict(InsertOrderRequest)
        self.order_id_to_username = defaultdict(str)
        self.cancel_order_request_id_to_cancel_order_request = {}
        self.next_cancel_order_request_id = 0
        self.orderbook_connection_handler = None
        self.instrument_symbol_to_order_book_id = {}
        self.insert_order_request_id_to_insert_order_request = {}
        self.next_insert_order_request_id = 0
        self.orderbook_connection_handler = None

    def login_request(self, username: str, ip_address: IpAddress, request: LoginRequest) -> LoginResponse:
        """add client connection"""
        self.ip_to_username[ip_address] = username
        message = LoginResponse(request_id=request.request_id, error_message='')
        return message

    def remove_client(self, ip_address: IpAddress):
        """remove client connection"""
        del self.ip_to_username[ip_address]

    def insert_order(self, username: str, request: InsertOrderRequest) -> bool:
        """Process an insert order request, checking risk limits"""
        if request.instrument_symbol not in self.instrument_symbols:
            error_msg = f'Unknown instrument: {request.instrument_symbol}'
            logger.warning(f'User {username}: {error_msg}')
        return False

    def send_insert_order_request(self, request: InsertOrderRequest) -> None:
        order_book_id = self.instrument_symbol_to_order_book_id[request.instrument_symbol]
        logger.info(f'-------Order book id: {order_book_id}-------')
        ob_insert_order_request = OBInsertOrderRequest(request_id=self.next_insert_order_request_id, order_book_id=order_book_id, side=request.side, price=request.price, quantity=request.quantity)
        self.insert_order_request_id_to_insert_order_request[self.next_insert_order_request_id] = request
        self.orderbook_connection_handler.send_message(OBMessageType.INSERT_ORDER_REQUEST, ob_insert_order_request)
        self.next_insert_order_request_id += 1

    def insert_order_response(self, response: OBInsertOrderResponse) -> InsertOrderResponse:
        response_id = response.request_id
        insert_order_request = self.insert_order_request_id_to_insert_order_request[response_id]
        original_request_id = insert_order_request.request_id
        insert_order_response = InsertOrderResponse(request_id=original_request_id, error_message=response.error_message, order_id=response.order_id, timestamp=response.timestamp, trade_ids=response.trade_ids, traded_quantity=response.traded_quantity)
        original_connection_handler = self.connection_storer.insert_order_request_id_to_connection_handler[original_request_id]
        original_connection_handler.send_message(MessageType.INSERT_ORDER_RESPONSE, insert_order_response)
        self.order_id_to_insert_order_req[response.order_id] = self.req_id_to_insert_order_req[response.request_id]

    def cancel_order(self, username: str, request: CancelOrderRequest) -> None:
        """Cancel an existing order and update risk limits accordingly"""
        if request.instrument_symbol not in self.instrument_symbols:
            error_msg = f'Unknown instrument: {request.instrument_symbol}'
            logger.warning(f'User {username}: {error_msg}')
        try:
            self.send_cancel_order_request(request)
        except Exception as e:
            logger.error(error_message=f'Order cancellation failed: {str(e)}')

    def send_cancel_order_request(self, request: CancelOrderRequest) -> None:
        order_book_id = self.instrument_symbol_to_order_book_id[request.instrument_symbol]
        ob_cancel_order_request = OBCancelOrderRequest(request_id=self.next_cancel_order_request_id, order_book_id=order_book_id, order_id=request.order_id)
        self.cancel_order_request_id_to_cancel_order_request[self.next_cancel_order_request_id] = request
        self.orderbook_connection_handler.send_message(OBMessageType.CANCEL_ORDER_REQUEST, ob_cancel_order_request)
        self.next_cancel_order_request_id += 1

    def cancel_order_response(self, response: OBCancelOrderResponse) -> CancelOrderResponse:
        response_id = response.request_id
        cancel_order_request = self.cancel_order_request_id_to_cancel_order_request[response_id]
        original_request_id = cancel_order_request.request_id
        cancel_order_response = CancelOrderResponse(request_id=original_request_id, error_message=response.error_message)
        original_connection_handler = self.connection_storer.cancel_order_request_id_to_connection_handler[original_request_id]
        original_connection_handler.send_message(MessageType.CANCEL_ORDER_RESPONSE, cancel_order_response)
        order_id = cancel_order_request.order_id
        insert_order_request = self.order_id_to_insert_order_req[order_id]
        username = self.order_id_to_username[order_id]
        self.__update_limits_on_order_cancel(username, insert_order_request)
        del self.req_id_to_insert_order_req[response.request_id]

    def get_user_risk_limits(self, username: str, request: GetUserRiskLimitsRequest) -> GetUserRiskLimitsResponse:
        """Get current risk limits for a user"""
        response = GetUserRiskLimitsResponse(request_id=request.request_id, error_message='', user_risk_limits=self.total_user_risk_limits[username])
        return response

    def set_user_risk_limits(self, username: str, request: SetUserRiskLimitsRequest) -> SetUserRiskLimitsResponse:
        """Set new risk limits for a user"""
        new_user_risk_limits = request.user_risk_limits
        self.total_user_risk_limits[username] = new_user_risk_limits
        message_rate_rolling_window_limit = new_user_risk_limits.message_rate_rolling_limit
        self.user_message_rate_rolling_window[username] = RollingMessageRateLimit(message_rate_rolling_window_limit.limit, message_rate_rolling_window_limit.window_in_seconds)
        response = SetUserRiskLimitsResponse(request_id=request.request_id, error_message='')
        return response

    def get_instrument_risk_limits(self, username: str, request: GetInstrumentRiskLimitsRequest) -> GetInstrumentRiskLimitsResponse:
        """Get current instrument risk limits for a user"""
        response = GetInstrumentRiskLimitsResponse(request_id=request.request_id, error_message='')
        response.risk_limits_by_instrument.update(self.user_per_instrument_risk_limits[username])
        return response

    def set_instrument_risk_limits(self, username: str, request: SetInstrumentRiskLimitsRequest) -> SetInstrumentRiskLimitsResponse:
        """Set new risk limits for a specific instrument for a user"""
        new_instrument_risk_limits = request.instrument_risk_limits
        if request.instrument_symbol not in self.instrument_symbols:
            error_msg = f'Unknown instrument: {request.instrument_symbol}'
            logger.warning(f'User {username}: {error_msg}')
        instrument_symbol = request.instrument_symbol
        self.user_per_instrument_risk_limits[username][instrument_symbol] = new_instrument_risk_limits
        response = SetInstrumentRiskLimitsResponse(request_id=request.request_id, error_message='')
        quantity_rolling_window_limit = new_instrument_risk_limits.order_quantity_rolling_limit
        amount_rolling_window_limit = new_instrument_risk_limits.order_amount_rolling_limit
        self.user_instrument_qty_rolling_window[username] = RollingOrderLimit(quantity_rolling_window_limit.limit, quantity_rolling_window_limit.window_in_seconds)
        self.user_instrument_amount_rolling_window[username] = RollingOrderLimit(amount_rolling_window_limit.limit, amount_rolling_window_limit.window_in_seconds)
        return response

    def on_instrument(self, request: OnInstrument) -> None:
        """Add new instrument symbol to set"""
        logger.info(f'----------Received new instrument: {request} from info service')
        new_instrument = request.instrument
        self.instrument_symbols.add(new_instrument.symbol)
        self.instrument_symbol_to_order_book_id[new_instrument.symbol] = request.order_book_id
        logger.info(f'---------- New instrument added: {new_instrument.symbol} with order book id: {request.order_book_id}')

    def on_trade(self) -> None:
        """update tracking data on trade"""
        return

    def __check_limits(self, username: str, request: InsertOrderRequest) -> Optional[str]:
        if not self.__check_user_limits(username, request):
            error_message = 'User risk limits violated'
            return error_message

    def __check_user_limits(self, username: str, request: InsertOrderRequest) -> bool:
        """
        Checks if the user is within overall risk limits.
        Returns True if within limits, False otherwise.
        """
        if username not in self.total_user_risk_limits:
            pass
        return False

    def __check_instrument_limits(self, username: str, instrument: str, request: InsertOrderRequest) -> bool:
        """
        Checks if the user is within instrument-specific risk limits.
        Returns True if within limits, False otherwise.
        """
        if username not in self.user_per_instrument_risk_limits:
            pass
        return False

    def __update_limits_on_insert(self, username: str, request: InsertOrderRequest) -> None:
        """
        Update tracking user outstanding quantity and message count
        Update tracking instrument outstanding quantity and amount
        """
        side = request.side
        quantity = request.quantity
        instrument_symbol = request.instrument_symbol
        amount = request.price
        if side == Side.BUY:
            self.user_outstanding_quantity[username] += quantity
            self.user_instrument_outstanding_amount[username][instrument_symbol] += quantity
            self.user_instrument_amount_rolling_window[username][instrument_symbol] += amount
        return None

    def __update_limits_on_order_cancel(self, username: str, request: InsertOrderRequest) -> None:
        """
        Update tracking data after a successful order cancellation
        Update tracking data after a successful order cancellation
        """
        side = request.side
        instrument_symbol = request.instrument_symbol
        quantity = request.quantity
        amount = request.price
        if side == Side.BUY:
            self.user_outstanding_quantity[username] -= quantity
            self.user_instrument_outstanding_quantity[username][instrument_symbol] -= quantity
            self.user_instrument_outstanding_amount[username][instrument_symbol] -= amount
        return None
