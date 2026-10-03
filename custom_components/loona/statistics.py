"""Count permission-eligible logical updates without decoding websocket packets."""

from time import monotonic
from typing import Any

from homeassistant.util import dt as dt_util

from .const import LIVE_RATE_PRECISION


class LiveStatistics:
    """Session totals and rates over the most recently completed interval."""

    def __init__(self) -> None:
        self.ignored: frozenset[str] = frozenset()
        self.page_loads: dict[str, dict[str, Any]] = {}
        self.reset()

    def reset(self) -> None:
        """Start a new measurement without changing HA recorder history."""
        self.forwarded = self.avoided = 0
        self.forwarded_rate = self.avoided_rate = self.reduction = 0.0
        self.sample_seconds = 0.0
        self._previous_forwarded = self._previous_avoided = 0
        self._sample_time = monotonic()
        self.reset_at = dt_util.utcnow()
        self.page_loads.clear()

    def record(self, forwarded: bool) -> None:
        """One entity change for one ordinary, selected-account subscription."""
        if forwarded:
            self.forwarded += 1
        else:
            self.avoided += 1

    def sample(self) -> None:
        """Publish a bounded rate interval; an idle interval produces zero."""
        now = monotonic()
        elapsed = now - self._sample_time
        if elapsed <= 0:
            return
        forwarded = self.forwarded - self._previous_forwarded
        avoided = self.avoided - self._previous_avoided
        self.forwarded_rate = round(forwarded / elapsed, LIVE_RATE_PRECISION)
        self.avoided_rate = round(avoided / elapsed, LIVE_RATE_PRECISION)
        self.reduction = round(100 * avoided / (forwarded + avoided), 1) if forwarded + avoided else 0.0
        self.sample_seconds = round(elapsed, 1)
        self._previous_forwarded, self._previous_avoided = self.forwarded, self.avoided
        self._sample_time = now

    def metrics(self) -> dict[str, int | float]:
        """Return small numeric values suitable for native HA sensors."""
        return {
            "forwarded_updates": self.forwarded,
            "avoided_updates": self.avoided,
            "forwarded_rate": self.forwarded_rate,
            "avoided_rate": self.avoided_rate,
            "update_reduction": self.reduction,
        }
