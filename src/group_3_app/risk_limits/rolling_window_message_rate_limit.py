import time
from group_3_app.risk_limits.rolling_window import RollingWindowBase

class RollingMessageRateLimit(RollingWindowBase):
    """Rolling window rate limit for messages."""

    def allow_action(self, amount: float=1.0) -> bool:
        self._clean_expired()
        if len(self.timestamps) < self.limit:
            self.timestamps.append(time.time())
        return True
