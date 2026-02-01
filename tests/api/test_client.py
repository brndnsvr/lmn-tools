"""
Tests for the LogicMonitor API client.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import requests
from pydantic import SecretStr

from lmn_tools.api.client import LMClient
from lmn_tools.core.config import LMCredentials
from lmn_tools.core.exceptions import (
    APIConnectionError,
    APIError,
    APINotFoundError,
    APIRateLimitError,
    APITimeoutError,
    APIValidationError,
    InvalidCredentialsError,
)

from .conftest import make_response


class TestLMClientInitialization:
    """Tests for LMClient initialization."""

    def test_init_sets_company(self) -> None:
        """Company is extracted and stored from constructor."""
        client = LMClient(
            company="my-company",
            access_id="id",
            access_key="key",
        )

        assert client.company == "my-company"

    def test_init_sets_base_url(self) -> None:
        """Base URL is constructed from company."""
        client = LMClient(
            company="acme",
            access_id="id",
            access_key="key",
        )

        assert client.base_url == "https://acme.logicmonitor.com/santaba/rest"

    def test_init_stores_access_id(self) -> None:
        """Access ID is stored."""
        client = LMClient(
            company="co",
            access_id="my_access_id",
            access_key="key",
        )

        assert client.access_id == "my_access_id"

    def test_init_wraps_string_key_in_secret_str(self) -> None:
        """String access_key is wrapped in SecretStr."""
        client = LMClient(
            company="co",
            access_id="id",
            access_key="plain_key",
        )

        assert isinstance(client._access_key, SecretStr)
        assert client._access_key.get_secret_value() == "plain_key"

    def test_init_preserves_secret_str_key(self) -> None:
        """SecretStr access_key is preserved."""
        secret = SecretStr("my_secret")
        client = LMClient(
            company="co",
            access_id="id",
            access_key=secret,
        )

        assert client._access_key is secret

    def test_init_default_timeout(self) -> None:
        """Default timeout is 30 seconds."""
        client = LMClient(
            company="co",
            access_id="id",
            access_key="key",
        )

        assert client.timeout == 30

    def test_init_custom_timeout(self) -> None:
        """Custom timeout is respected."""
        client = LMClient(
            company="co",
            access_id="id",
            access_key="key",
            timeout=60,
        )

        assert client.timeout == 60

    def test_from_credentials_factory(self) -> None:
        """Factory method creates client from LMCredentials."""
        creds = LMCredentials(
            company="factory-test",
            access_id="factory_id",
            access_key=SecretStr("factory_key"),
        )

        client = LMClient.from_credentials(creds)

        assert client.company == "factory-test"
        assert client.access_id == "factory_id"
        assert client._access_key.get_secret_value() == "factory_key"

    def test_from_credentials_with_custom_timeout(self) -> None:
        """Factory method accepts custom timeout."""
        creds = LMCredentials(
            company="co",
            access_id="id",
            access_key=SecretStr("key"),
        )

        client = LMClient.from_credentials(creds, timeout=120)

        assert client.timeout == 120


class TestRequestHandling:
    """Tests for request method and header building."""

    def test_request_get_success(self, client: LMClient, mock_session: MagicMock) -> None:
        """Successful GET request returns parsed data."""
        mock_session.request.return_value = make_response(
            status_code=200,
            json_data={"id": 1, "name": "test"},
        )

        result = client.request("GET", "/device/devices")

        assert result == {"id": 1, "name": "test"}

    def test_request_adds_auth_headers(self, client: LMClient, mock_session: MagicMock) -> None:
        """Request includes authentication headers."""
        mock_session.request.return_value = make_response(status_code=200, json_data={})

        client.request("GET", "/test")

        call_kwargs = mock_session.request.call_args.kwargs
        headers = call_kwargs["headers"]

        assert "Authorization" in headers
        assert headers["Authorization"].startswith("LMv1 test_access_id:")
        assert "Content-Type" in headers
        assert "X-Version" in headers

    def test_request_path_normalization_adds_leading_slash(
        self, client: LMClient, mock_session: MagicMock
    ) -> None:
        """Path without leading slash gets one added."""
        mock_session.request.return_value = make_response(status_code=200, json_data={})

        client.request("GET", "device/devices")

        call_kwargs = mock_session.request.call_args.kwargs
        assert call_kwargs["url"].endswith("/device/devices")

    def test_request_path_with_leading_slash(
        self, client: LMClient, mock_session: MagicMock
    ) -> None:
        """Path with leading slash is preserved."""
        mock_session.request.return_value = make_response(status_code=200, json_data={})

        client.request("GET", "/device/devices")

        call_kwargs = mock_session.request.call_args.kwargs
        assert "/device/devices" in call_kwargs["url"]
        assert "//device" not in call_kwargs["url"]

    def test_request_passes_params(self, client: LMClient, mock_session: MagicMock) -> None:
        """Query parameters are passed to session."""
        mock_session.request.return_value = make_response(status_code=200, json_data={})

        client.request("GET", "/test", params={"filter": "name:test", "size": 10})

        call_kwargs = mock_session.request.call_args.kwargs
        assert call_kwargs["params"] == {"filter": "name:test", "size": 10}

    def test_request_passes_json_data(self, client: LMClient, mock_session: MagicMock) -> None:
        """JSON data is passed to session."""
        mock_session.request.return_value = make_response(status_code=200, json_data={})

        client.request("POST", "/test", json_data={"name": "new_device"})

        call_kwargs = mock_session.request.call_args.kwargs
        assert call_kwargs["json"] == {"name": "new_device"}

    def test_request_uses_timeout(self, client: LMClient, mock_session: MagicMock) -> None:
        """Request uses configured timeout."""
        client.timeout = 45
        mock_session.request.return_value = make_response(status_code=200, json_data={})

        client.request("GET", "/test")

        call_kwargs = mock_session.request.call_args.kwargs
        assert call_kwargs["timeout"] == 45


class TestResponseHandling:
    """Tests for _handle_response method."""

    def test_handle_401_raises_invalid_credentials(
        self, client: LMClient, mock_session: MagicMock
    ) -> None:
        """401 response raises InvalidCredentialsError."""
        mock_session.request.return_value = make_response(
            status_code=401,
            json_data={"errmsg": "Authentication failed"},
        )

        with pytest.raises(InvalidCredentialsError) as exc_info:
            client.request("GET", "/test")

        assert "Authentication failed" in str(exc_info.value)

    def test_handle_401_with_message_key(self, client: LMClient, mock_session: MagicMock) -> None:
        """401 response extracts message from 'message' key."""
        mock_session.request.return_value = make_response(
            status_code=401,
            json_data={"message": "Token expired"},
        )

        with pytest.raises(InvalidCredentialsError) as exc_info:
            client.request("GET", "/test")

        assert "Token expired" in str(exc_info.value)

    def test_handle_401_default_message(self, client: LMClient, mock_session: MagicMock) -> None:
        """401 response uses default message when none provided."""
        mock_session.request.return_value = make_response(
            status_code=401,
            json_data={},
        )

        with pytest.raises(InvalidCredentialsError) as exc_info:
            client.request("GET", "/test")

        assert "Invalid credentials" in str(exc_info.value)

    def test_handle_404_raises_not_found(self, client: LMClient, mock_session: MagicMock) -> None:
        """404 response raises APINotFoundError."""
        mock_session.request.return_value = make_response(
            status_code=404,
            json_data={"errmsg": "Not found"},
        )

        with pytest.raises(APINotFoundError) as exc_info:
            client.request("GET", "/device/devices/999")

        assert exc_info.value.status_code == 404

    def test_handle_429_raises_rate_limit(self, client: LMClient, mock_session: MagicMock) -> None:
        """429 response raises APIRateLimitError."""
        mock_session.request.return_value = make_response(
            status_code=429,
            json_data={"errmsg": "Rate limit exceeded"},
        )

        with pytest.raises(APIRateLimitError) as exc_info:
            client.request("GET", "/test")

        assert exc_info.value.status_code == 429

    def test_handle_429_with_retry_after(self, client: LMClient, mock_session: MagicMock) -> None:
        """429 response extracts Retry-After header."""
        mock_session.request.return_value = make_response(
            status_code=429,
            json_data={},
            headers={"Retry-After": "60"},
        )

        with pytest.raises(APIRateLimitError) as exc_info:
            client.request("GET", "/test")

        assert exc_info.value.retry_after == 60

    def test_handle_429_without_retry_after(
        self, client: LMClient, mock_session: MagicMock
    ) -> None:
        """429 response handles missing Retry-After header."""
        mock_session.request.return_value = make_response(
            status_code=429,
            json_data={},
            headers={},
        )

        with pytest.raises(APIRateLimitError) as exc_info:
            client.request("GET", "/test")

        assert exc_info.value.retry_after is None

    def test_handle_400_raises_validation_error(
        self, client: LMClient, mock_session: MagicMock
    ) -> None:
        """400 response raises APIValidationError."""
        mock_session.request.return_value = make_response(
            status_code=400,
            json_data={"errmsg": "Invalid filter syntax"},
        )

        with pytest.raises(APIValidationError) as exc_info:
            client.request("GET", "/test")

        assert "Invalid filter syntax" in str(exc_info.value)
        assert exc_info.value.status_code == 400

    def test_handle_500_raises_api_error(self, client: LMClient, mock_session: MagicMock) -> None:
        """5xx response raises APIError."""
        mock_session.request.return_value = make_response(
            status_code=500,
            json_data={"errmsg": "Internal server error"},
        )

        with pytest.raises(APIError) as exc_info:
            client.request("GET", "/test")

        assert exc_info.value.status_code == 500

    def test_handle_503_raises_api_error(self, client: LMClient, mock_session: MagicMock) -> None:
        """503 response raises APIError."""
        mock_session.request.return_value = make_response(
            status_code=503,
            json_data={"errorMessage": "Service unavailable"},
        )

        with pytest.raises(APIError) as exc_info:
            client.request("GET", "/test")

        assert "Service unavailable" in str(exc_info.value)

    def test_handle_non_json_response(self, client: LMClient, mock_session: MagicMock) -> None:
        """Non-JSON response is handled gracefully."""
        response = MagicMock()
        response.status_code = 502
        response.text = "Bad Gateway"
        response.headers = {}
        response.url = "https://test.logicmonitor.com/test"
        response.json.side_effect = ValueError("No JSON")

        mock_session.request.return_value = response

        with pytest.raises(APIError) as exc_info:
            client.request("GET", "/test")

        assert "Bad Gateway" in str(exc_info.value)

    def test_handle_normalizes_items_response(
        self, client: LMClient, mock_session: MagicMock
    ) -> None:
        """Response with 'items' but no 'data' is normalized."""
        mock_session.request.return_value = make_response(
            status_code=200,
            json_data={"items": [{"id": 1}, {"id": 2}], "total": 2},
        )

        result = client.request("GET", "/device/devices")

        assert "data" in result
        assert result["data"]["items"] == [{"id": 1}, {"id": 2}]
        assert result["data"]["total"] == 2

    def test_handle_preserves_data_structure(
        self, client: LMClient, mock_session: MagicMock
    ) -> None:
        """Response with 'data' key is preserved as-is."""
        mock_session.request.return_value = make_response(
            status_code=200,
            json_data={"data": {"id": 1, "name": "device"}},
        )

        result = client.request("GET", "/device/devices/1")

        assert result == {"data": {"id": 1, "name": "device"}}


class TestHTTPVerbs:
    """Tests for HTTP verb convenience methods."""

    def test_get_calls_request(self, client: LMClient, mock_session: MagicMock) -> None:
        """get() delegates to request() with GET method."""
        mock_session.request.return_value = make_response(
            status_code=200, json_data={"result": "ok"}
        )

        result = client.get("/test", params={"size": 10})

        call_kwargs = mock_session.request.call_args.kwargs
        assert call_kwargs["method"] == "GET"
        assert call_kwargs["params"] == {"size": 10}
        assert result == {"result": "ok"}

    def test_post_with_json_data(self, client: LMClient, mock_session: MagicMock) -> None:
        """post() passes json_data correctly."""
        mock_session.request.return_value = make_response(status_code=200, json_data={"id": 123})

        result = client.post("/device/devices", json_data={"name": "new-device"})

        call_kwargs = mock_session.request.call_args.kwargs
        assert call_kwargs["method"] == "POST"
        assert call_kwargs["json"] == {"name": "new-device"}
        assert result == {"id": 123}

    def test_patch_with_json_data(self, client: LMClient, mock_session: MagicMock) -> None:
        """patch() uses PATCH method with json_data."""
        mock_session.request.return_value = make_response(
            status_code=200, json_data={"updated": True}
        )

        client.patch("/device/devices/1", json_data={"name": "updated-name"})

        call_kwargs = mock_session.request.call_args.kwargs
        assert call_kwargs["method"] == "PATCH"
        assert call_kwargs["json"] == {"name": "updated-name"}

    def test_put_with_json_data(self, client: LMClient, mock_session: MagicMock) -> None:
        """put() uses PUT method with json_data."""
        mock_session.request.return_value = make_response(
            status_code=200, json_data={"replaced": True}
        )

        client.put("/device/devices/1", json_data={"name": "replaced-device"})

        call_kwargs = mock_session.request.call_args.kwargs
        assert call_kwargs["method"] == "PUT"

    def test_delete_calls_request(self, client: LMClient, mock_session: MagicMock) -> None:
        """delete() uses DELETE method."""
        mock_session.request.return_value = make_response(status_code=200, json_data={})

        client.delete("/device/devices/1")

        call_kwargs = mock_session.request.call_args.kwargs
        assert call_kwargs["method"] == "DELETE"


class TestPagination:
    """Tests for paginate() and get_all() methods."""

    def test_paginate_single_page(self, client: LMClient, mock_session: MagicMock) -> None:
        """Paginate yields items and stops when empty."""
        mock_session.request.side_effect = [
            make_response(
                status_code=200,
                json_data={
                    "data": {
                        "items": [{"id": 1}, {"id": 2}],
                        "total": 2,
                    }
                },
            ),
            make_response(
                status_code=200,
                json_data={"data": {"items": [], "total": 2}},
            ),
        ]

        items = list(client.paginate("/device/devices"))

        assert len(items) == 2
        assert items[0]["id"] == 1
        assert items[1]["id"] == 2

    def test_paginate_multiple_pages(self, client: LMClient, mock_session: MagicMock) -> None:
        """Paginate iterates through multiple pages."""
        # Track offsets as they're called (since MagicMock stores refs to mutable dicts)
        captured_offsets: list[int] = []

        def capture_request(**kwargs):
            captured_offsets.append(kwargs["params"]["offset"])
            page_num = len(captured_offsets)
            if page_num == 1:
                return make_response(
                    status_code=200,
                    json_data={
                        "data": {
                            "items": [{"id": 1}, {"id": 2}],
                            "total": 4,
                        }
                    },
                )
            else:
                return make_response(
                    status_code=200,
                    json_data={
                        "data": {
                            "items": [{"id": 3}, {"id": 4}],
                            "total": 4,
                        }
                    },
                )

        mock_session.request.side_effect = capture_request

        items = list(client.paginate("/device/devices", page_size=2))

        assert len(items) == 4
        assert [i["id"] for i in items] == [1, 2, 3, 4]

        # Verify offset was incremented
        assert mock_session.request.call_count == 2
        assert captured_offsets == [0, 2]

    def test_paginate_respects_max_items(self, client: LMClient, mock_session: MagicMock) -> None:
        """Paginate stops at max_items limit."""
        mock_session.request.return_value = make_response(
            status_code=200,
            json_data={
                "data": {
                    "items": [{"id": i} for i in range(10)],
                    "total": 100,
                }
            },
        )

        items = list(client.paginate("/device/devices", max_items=5))

        assert len(items) == 5

    def test_paginate_empty_first_page(self, client: LMClient, mock_session: MagicMock) -> None:
        """Paginate handles no results."""
        mock_session.request.return_value = make_response(
            status_code=200,
            json_data={"data": {"items": [], "total": 0}},
        )

        items = list(client.paginate("/device/devices"))

        assert items == []

    def test_paginate_uses_custom_page_size(
        self, client: LMClient, mock_session: MagicMock
    ) -> None:
        """Paginate respects custom page_size."""
        mock_session.request.return_value = make_response(
            status_code=200,
            json_data={"data": {"items": [], "total": 0}},
        )

        list(client.paginate("/device/devices", page_size=100))

        call_kwargs = mock_session.request.call_args.kwargs
        assert call_kwargs["params"]["size"] == 100

    def test_paginate_merges_params(self, client: LMClient, mock_session: MagicMock) -> None:
        """Paginate merges user params with pagination params."""
        mock_session.request.return_value = make_response(
            status_code=200,
            json_data={"data": {"items": [], "total": 0}},
        )

        list(client.paginate("/device/devices", params={"filter": "name:test"}))

        call_kwargs = mock_session.request.call_args.kwargs
        assert call_kwargs["params"]["filter"] == "name:test"
        assert "size" in call_kwargs["params"]
        assert "offset" in call_kwargs["params"]

    def test_get_all_returns_list(self, client: LMClient, mock_session: MagicMock) -> None:
        """get_all() collects paginated results into a list."""
        mock_session.request.side_effect = [
            make_response(
                status_code=200,
                json_data={
                    "data": {
                        "items": [{"id": 1}],
                        "total": 2,
                    }
                },
            ),
            make_response(
                status_code=200,
                json_data={
                    "data": {
                        "items": [{"id": 2}],
                        "total": 2,
                    }
                },
            ),
        ]

        result = client.get_all("/device/devices", page_size=1)

        assert isinstance(result, list)
        assert len(result) == 2

    def test_get_all_respects_max_items(self, client: LMClient, mock_session: MagicMock) -> None:
        """get_all() respects max_items parameter."""
        mock_session.request.return_value = make_response(
            status_code=200,
            json_data={
                "data": {
                    "items": [{"id": i} for i in range(50)],
                    "total": 1000,
                }
            },
        )

        result = client.get_all("/device/devices", max_items=25)

        assert len(result) == 25


class TestExceptionPropagation:
    """Tests for exception handling during requests."""

    def test_timeout_raises_api_timeout(self, client: LMClient, mock_session: MagicMock) -> None:
        """Timeout exception is wrapped in APITimeoutError."""
        mock_session.request.side_effect = requests.exceptions.Timeout("timed out")

        with pytest.raises(APITimeoutError) as exc_info:
            client.request("GET", "/test")

        assert "timed out" in str(exc_info.value)

    def test_connection_error_raises_connection_error(
        self, client: LMClient, mock_session: MagicMock
    ) -> None:
        """Connection error is wrapped in APIConnectionError."""
        mock_session.request.side_effect = requests.exceptions.ConnectionError("connection refused")

        with pytest.raises(APIConnectionError) as exc_info:
            client.request("GET", "/test")

        assert "connection" in str(exc_info.value).lower()
