import time
from collections import deque
from group_3_app.risk_limits.rolling_window import RollingWindowBase

class RollingOrderLimit(RollingWindowBase):
    """Rolling window rate limit for order quantity or amount."""

    def __init__(self, limit: float, window_in_seconds: int):
        super().__init__(limit, window_in_seconds)
        self.values = deque()

    def allow_action(self, amount: float) -> bool:
        self._clean_expired()
        current_total = sum((value for _, value in self.values))
        if current_total + amount <= self.limit:
            self.values.append((time.time(), amount))
        return True
