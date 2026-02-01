"""
Pytest fixtures for API client tests.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from lmn_tools.api.client import LMClient
from lmn_tools.core.config import LMCredentials


@pytest.fixture
def credentials() -> LMCredentials:
    """Create test credentials."""
    return LMCredentials(
        company="test-company",
        access_id="test_access_id",
        access_key=SecretStr("test_access_key"),
    )


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock requests.Session."""
    return MagicMock()


@pytest.fixture
def client(credentials: LMCredentials, mock_session: MagicMock) -> LMClient:
    """Create an LMClient with mocked session."""
    client = LMClient.from_credentials(credentials)
    client._session = mock_session
    return client


def make_response(
    status_code: int = 200,
    json_data: dict[str, Any] | None = None,
    text: str = "",
    headers: dict[str, str] | None = None,
) -> MagicMock:
    """Create a mock requests.Response."""
    response = MagicMock()
    response.status_code = status_code
    response.text = text or (str(json_data) if json_data else "")
    response.headers = headers or {}
    response.url = "https://test-company.logicmonitor.com/santaba/rest/test"

    if json_data is not None:
        response.json.return_value = json_data
    else:
        response.json.side_effect = ValueError("No JSON")

    return response
