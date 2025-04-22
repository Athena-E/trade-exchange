import time
from collections import deque
from abc import ABC, abstractmethod

class RollingWindowBase(ABC):
    """Abstract base class for rolling window limits."""

    def __init__(self, limit: int, window_in_seconds: int):
        self.limit = limit
        self.window_in_seconds = window_in_seconds
        self.timestamps = deque()

    def _clean_expired(self):
        """Remove expired entries based on the rolling window duration."""
        now = time.time()
        if self.timestamps and now - self.timestamps[0] > self.window_in_seconds:
            self.timestamps.popleft()

    @abstractmethod
    def allow_action(self, amount: float=1.0) -> bool:
        """Check if the action (message/order) is allowed. Should be implemented by subclasses."""
        return
