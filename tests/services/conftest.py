"""
Pytest fixtures for service tests.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock LMClient."""
    client = MagicMock()
    client.company = "test-company"
    return client


def make_list_response(items: list[dict[str, Any]], total: int | None = None) -> list[dict[str, Any]]:
    """Helper to format list responses as the client returns them."""
    return items


def make_get_response(item: dict[str, Any]) -> dict[str, Any]:
    """Helper to format get responses."""
    return item
