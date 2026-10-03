"""Count permission-eligible logical updates without decoding websocket packets."""

from collections import deque
from time import monotonic
from typing import Any

from homeassistant.util import dt as dt_util

from .const import LIVE_RATE_PRECISION, RATE_HISTORY_LIMIT, NOISY_ENTITY_LIMIT, NOISY_ENTITY_REPORT_LIMIT


class LiveStatistics:
    """Session totals and rates over the most recently completed interval."""

    def __init__(self) -> None:
        self.ignored: frozenset[str] = frozenset()
        self.page_loads: dict[str, dict[str, Any]] = {}
        self.browser_reports: dict[str, dict[str, Any]] = {}
        self.reset()

    def reset(self) -> None:
        """Start a new measurement without changing HA recorder history."""
        self.forwarded = self.avoided = 0
        self.forwarded_rate = self.avoided_rate = self.reduction = 0.0
        self.sample_seconds = 0.0
        self.rate_history: deque[dict[str, Any]] = deque(maxlen=RATE_HISTORY_LIMIT)
        self._previous_forwarded = self._previous_avoided = 0
        self._sample_time = monotonic()
        self.reset_at = dt_util.utcnow()
        self.page_loads.clear()
        self.browser_reports.clear()
        self.noisy_entities: dict[str, int] = {}
        self.noisy_overflow = 0

    def record(self, forwarded: bool, entity_id: str | None = None) -> None:
        """One entity change for one ordinary, selected-account subscription."""
        if forwarded:
            self.forwarded += 1
            if entity_id is not None:
                if entity_id in self.noisy_entities or len(self.noisy_entities) < NOISY_ENTITY_LIMIT:
                    self.noisy_entities[entity_id] = self.noisy_entities.get(entity_id, 0) + 1
                else:
                    self.noisy_overflow += 1
        else:
            self.avoided += 1

    def noisy_report(self) -> dict[str, Any]:
        """Bounded sent-update counts since reset, including per-feed duplication."""
        rows = sorted(self.noisy_entities.items(), key=lambda item: (-item[1], item[0]))
        return {"entities": [{"entity_id": entity_id, "updates": count}
                             for entity_id, count in rows[:NOISY_ENTITY_REPORT_LIMIT]],
                "untracked_updates": self.noisy_overflow}

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
        self.rate_history.append({"at": dt_util.utcnow().isoformat(), "seconds": self.sample_seconds,
                                  "sent": self.forwarded_rate, "filtered": self.avoided_rate})

    def metrics(self) -> dict[str, int | float]:
        """Return small numeric values suitable for native HA sensors."""
        return {
            "forwarded_updates": self.forwarded,
            "avoided_updates": self.avoided,
            "forwarded_rate": self.forwarded_rate,
            "avoided_rate": self.avoided_rate,
            "update_reduction": self.reduction,
        }
