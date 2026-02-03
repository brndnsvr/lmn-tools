"""Tests for time formatting utilities."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from lmn_tools.cli.utils.time import (
    format_duration,
    format_duration_from_now,
    format_timestamp,
)


class TestFormatTimestamp:
    """Tests for format_timestamp function."""

    def test_none_returns_na(self) -> None:
        """Test that None timestamp returns 'N/A'."""
        assert format_timestamp(None) == "N/A"

    def test_zero_returns_na(self) -> None:
        """Test that zero timestamp returns 'N/A'."""
        assert format_timestamp(0) == "N/A"

    def test_seconds_precision(self) -> None:
        """Test formatting timestamp in seconds."""
        # 2021-01-01 00:00:00 UTC
        ts = 1609459200
        result = format_timestamp(ts)
        # Result will be in local timezone, so just check format
        assert len(result) == 16  # YYYY-MM-DD HH:MM
        assert result[4] == "-"
        assert result[7] == "-"
        assert result[10] == " "
        assert result[13] == ":"

    def test_milliseconds_precision(self) -> None:
        """Test formatting timestamp in milliseconds."""
        # 2021-01-01 00:00:00 UTC in milliseconds
        ts = 1609459200000
        result = format_timestamp(ts)
        assert len(result) == 16  # YYYY-MM-DD HH:MM

    def test_standard_format(self) -> None:
        """Test standard format without seconds."""
        ts = 1609459200
        result = format_timestamp(ts, format="standard")
        assert len(result) == 16  # YYYY-MM-DD HH:MM
        assert result.count(":") == 1  # Only one colon (HH:MM)

    def test_seconds_format(self) -> None:
        """Test seconds format with seconds included."""
        ts = 1609459200
        result = format_timestamp(ts, format="seconds")
        assert len(result) == 19  # YYYY-MM-DD HH:MM:SS
        assert result.count(":") == 2  # Two colons (HH:MM:SS)

    def test_invalid_timestamp_returns_string(self) -> None:
        """Test that invalid timestamp is returned as string."""
        # Use a timestamp that will cause an exception
        result = format_timestamp(99999999999999999999)
        assert result == "99999999999999999999"


class TestFormatDuration:
    """Tests for format_duration function."""

    def test_none_start_returns_na(self) -> None:
        """Test that None start returns 'N/A'."""
        assert format_duration(None, 1000000) == "N/A"

    def test_none_end_returns_na(self) -> None:
        """Test that None end returns 'N/A'."""
        assert format_duration(1000000, None) == "N/A"

    def test_both_none_returns_na(self) -> None:
        """Test that both None returns 'N/A'."""
        assert format_duration(None, None) == "N/A"

    def test_zero_start_returns_na(self) -> None:
        """Test that zero start returns 'N/A'."""
        assert format_duration(0, 1000000) == "N/A"

    def test_zero_end_returns_na(self) -> None:
        """Test that zero end returns 'N/A'."""
        assert format_duration(1000000, 0) == "N/A"

    def test_duration_minutes_only(self) -> None:
        """Test duration less than 1 hour (minutes only)."""
        start = 1000000
        end = start + (30 * 60)  # 30 minutes
        assert format_duration(start, end) == "30m"

    def test_duration_hours_and_minutes(self) -> None:
        """Test duration between 1 hour and 24 hours."""
        start = 1000000
        end = start + (90 * 60)  # 1.5 hours
        assert format_duration(start, end) == "1h 30m"

    def test_duration_exact_hours(self) -> None:
        """Test duration of exact hours with no remaining minutes."""
        start = 1000000
        end = start + (120 * 60)  # 2 hours
        assert format_duration(start, end) == "2h 0m"

    def test_duration_days_and_hours(self) -> None:
        """Test duration greater than 24 hours."""
        start = 1000000
        end = start + (36 * 60 * 60)  # 36 hours (1 day 12 hours)
        assert format_duration(start, end) == "1d 12h"

    def test_duration_multiple_days(self) -> None:
        """Test duration of multiple days."""
        start = 1000000
        end = start + (72 * 60 * 60)  # 72 hours (3 days)
        assert format_duration(start, end) == "3d 0h"

    def test_milliseconds_precision(self) -> None:
        """Test duration with millisecond precision timestamps."""
        start = 1609459200000  # 2021-01-01 00:00:00 UTC in milliseconds
        end = start + (45 * 60 * 1000)  # 45 minutes in milliseconds
        assert format_duration(start, end) == "45m"

    def test_mixed_precision(self) -> None:
        """Test duration with mixed precision (seconds start, milliseconds end)."""
        start = 1000000  # seconds
        end = 1000000000 + (60 * 60 * 1000)  # milliseconds, 1 hour later
        result = format_duration(start, end)
        # Should handle the conversion correctly
        assert "h" in result or "m" in result


class TestFormatDurationFromNow:
    """Tests for format_duration_from_now function."""

    def test_none_returns_na(self) -> None:
        """Test that None start returns 'N/A'."""
        assert format_duration_from_now(None) == "N/A"

    def test_zero_returns_na(self) -> None:
        """Test that zero start returns 'N/A'."""
        assert format_duration_from_now(0) == "N/A"

    @patch("lmn_tools.cli.utils.time.datetime")
    def test_duration_from_now_minutes(self, mock_datetime) -> None:
        """Test duration from now (minutes)."""
        # Mock current time
        now = datetime(2021, 1, 1, 12, 30, 0)
        mock_datetime.now.return_value = now

        # Start time 30 minutes ago
        start = int(datetime(2021, 1, 1, 12, 0, 0).timestamp())
        result = format_duration_from_now(start)
        assert result == "30m"

    @patch("lmn_tools.cli.utils.time.datetime")
    def test_duration_from_now_hours(self, mock_datetime) -> None:
        """Test duration from now (hours)."""
        now = datetime(2021, 1, 1, 14, 30, 0)
        mock_datetime.now.return_value = now

        # Start time 2.5 hours ago
        start = int(datetime(2021, 1, 1, 12, 0, 0).timestamp())
        result = format_duration_from_now(start)
        assert result == "2h 30m"

    @patch("lmn_tools.cli.utils.time.datetime")
    def test_duration_from_now_days(self, mock_datetime) -> None:
        """Test duration from now (days)."""
        now = datetime(2021, 1, 3, 14, 0, 0)
        mock_datetime.now.return_value = now

        # Start time 2 days and 2 hours ago
        start = int(datetime(2021, 1, 1, 12, 0, 0).timestamp())
        result = format_duration_from_now(start)
        assert result == "2d 2h"

    @patch("lmn_tools.cli.utils.time.datetime")
    def test_duration_from_now_milliseconds(self, mock_datetime) -> None:
        """Test duration from now with millisecond precision."""
        now = datetime(2021, 1, 1, 12, 45, 0)
        mock_datetime.now.return_value = now

        # Start time 45 minutes ago in milliseconds
        start = int(datetime(2021, 1, 1, 12, 0, 0).timestamp() * 1000)
        result = format_duration_from_now(start)
        assert result == "45m"
