"""APIGW.0301 rate-limit emulation (see docs)1.3)."""

import os
import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
    """Per-AK sliding window throttle. 0 = disabled."""
    max_per_window: int = field(default_factory=lambda: int(os.environ.get("SIM_RATE_LIMIT", "100")))
    window_seconds: float = 10.0
    cooldown_seconds: float = field(default_factory=lambda: float(os.environ.get("SIM_RATE_COOLDOWN_MS", "30000")) / 1000)
    mode: str = field(default_factory=lambda: os.environ.get("SIM_RATE_MODE", "0301"))

    def __post_init__(self):
        self._windows: dict[str, deque] = {}
        self._blocked_until: dict[str, float] = {}

    def record(self, ak: str) -> bool:
        """Record a request. Returns False when the AK is throttled."""
        if self.max_per_window == 0:
            return True

        now = time.monotonic()
        if ak in self._blocked_until:
            if now < self._blocked_until[ak]:
                return False
            del self._blocked_until[ak]

        window = self._windows.setdefault(ak, deque())
        cutoff = now - self.window_seconds
        while window and window[0] < cutoff:
            window.popleft()
        window.append(now)

        if len(window) > self.max_per_window:
            self._blocked_until[ak] = now + self.cooldown_seconds
            self._windows.pop(ak, None)
            return False
        return True

    def error_response(self) -> tuple[int, dict]:
        """The error response for the active mode: (status_code, body)."""
        request_id = f"{time.time_ns():x}"
        if self.mode == "0308":
            return 429, {
                "error_msg": "The throttling threshold has been reached.",
                "error_code": "APIGW.0308",
                "request_id": request_id,
            }
        return 401, {
            "error_msg": "Incorrect IAM authentication information: AK access failed to reach the limit,forbidden.",
            "error_code": "APIGW.0301",
            "request_id": request_id,
        }
