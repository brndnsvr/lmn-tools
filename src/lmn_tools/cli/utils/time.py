"""Time formatting utilities for CLI output."""

from __future__ import annotations

from datetime import datetime
from typing import Literal


def format_timestamp(
    ts: int | None,
    format: Literal["standard", "seconds"] = "standard",
) -> str:
    """Format epoch timestamp to readable string.

    Handles both millisecond and second precision timestamps automatically.

    Args:
        ts: Unix timestamp in seconds or milliseconds (None returns "N/A")
        format: "standard" (YYYY-MM-DD HH:MM) or "seconds" (YYYY-MM-DD HH:MM:SS)

    Returns:
        Formatted timestamp string or "N/A" if ts is None
    """
    if not ts:
        return "N/A"
    try:
        ts_secs: float = ts / 1000 if ts >= 1e12 else float(ts)
        fmt = "%Y-%m-%d %H:%M:%S" if format == "seconds" else "%Y-%m-%d %H:%M"
        return datetime.fromtimestamp(ts_secs).strftime(fmt)
    except Exception:
        return str(ts)


def format_duration(start: int | None, end: int | None) -> str:
    """Format duration between two timestamps.

    Args:
        start: Start timestamp in seconds or milliseconds (None returns "N/A")
        end: End timestamp in seconds or milliseconds (None returns "N/A")

    Returns:
        Formatted duration string (e.g., "2d 3h", "45m", "1h 30m") or "N/A"
    """
    if not start or not end:
        return "N/A"

    try:
        start_secs = start / 1000 if start >= 1e12 else start
        end_secs = end / 1000 if end >= 1e12 else end
        duration_mins = int((end_secs - start_secs) / 60)

        if duration_mins < 60:
            return f"{duration_mins}m"
        elif duration_mins < 1440:
            hours, mins = duration_mins // 60, duration_mins % 60
            return f"{hours}h {mins}m"
        else:
            days = duration_mins // 1440
            hours = (duration_mins % 1440) // 60
            return f"{days}d {hours}h"
    except Exception:
        return "N/A"


def format_duration_from_now(start: int | None) -> str:
    """Format duration from start timestamp to current time.

    Args:
        start: Start timestamp in seconds or milliseconds (None returns "N/A")

    Returns:
        Formatted duration string (e.g., "2d 3h", "45m", "1h 30m") or "N/A"
    """
    if not start:
        return "N/A"

    try:
        start_secs = start / 1000 if start >= 1e12 else start
        now_secs = datetime.now().timestamp()
        duration_mins = int((now_secs - start_secs) / 60)

        if duration_mins < 60:
            return f"{duration_mins}m"
        elif duration_mins < 1440:
            hours, mins = duration_mins // 60, duration_mins % 60
            return f"{hours}h {mins}m"
        else:
            days = duration_mins // 1440
            hours = (duration_mins % 1440) // 60
            return f"{days}d {hours}h"
    except Exception:
        return "N/A"
