"""
Pytest fixtures for auth tests.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_credentials() -> dict[str, str]:
    """Sample credentials for testing."""
    return {
        "access_id": "test_access_id",
        "access_key": "test_access_key",
    }


@pytest.fixture
def fixed_epoch() -> int:
    """Fixed epoch timestamp for reproducible tests."""
    return 1700000000000  # 2023-11-14 in milliseconds
