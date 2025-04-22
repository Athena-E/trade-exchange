import logging
import socket
from typing import Literal

logger = logging.getLogger(__name__)

BYTE_ORDER: Literal['little', 'big'] = 'big'
MESSAGE_SIZE_BYTES = 4
MESSAGE_TYPE_BYTES = 4


def encode_message(message_type: int, message: bytes) -> bytes:
    message_size: int = len(message) + MESSAGE_TYPE_BYTES
    output_stream: bytes = message_size.to_bytes(MESSAGE_SIZE_BYTES, byteorder=BYTE_ORDER)
    output_stream += message_type.to_bytes(MESSAGE_TYPE_BYTES, byteorder=BYTE_ORDER)
    output_stream += message
    return output_stream


def read_message(socket_fd: socket.socket) -> tuple[int, bytes]:
    raw_msg_len = socket_fd.recv(MESSAGE_SIZE_BYTES)
    if not raw_msg_len:
        raise BrokenPipeError("No data on socket")

    msg_len = int.from_bytes(raw_msg_len, byteorder=BYTE_ORDER)
    logger.debug(f"Received expected message length: {msg_len}")

    raw_msg = socket_fd.recv(msg_len)
    logger.debug(f"Actual message length: {len(raw_msg)}")

    message_type = int.from_bytes(raw_msg[:MESSAGE_TYPE_BYTES], byteorder=BYTE_ORDER)
    message = raw_msg[MESSAGE_TYPE_BYTES:]
    return message_type, message
