"""Expose Core's validation engine with its current static types."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import probatio as vol
else:
    # Modern Core aliases voluptuous to probatio before loading integrations.
    # Earlier Core versions continue to supply the original validation engine.
    import voluptuous as vol

__all__ = ["vol"]
