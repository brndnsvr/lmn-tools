"""
Unified LogicMonitor REST API client.

Provides a session-based client with automatic authentication,
pagination, and error handling.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Generator

import requests
from pydantic import SecretStr

from lmn_tools.auth.hmac import generate_auth_headers
from lmn_tools.constants import LMAPIConfig
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

logger = logging.getLogger(__name__)


class LMClient:
    """
    LogicMonitor REST API v3 client with LMv1 authentication.

    Usage:
        # From credentials
        client = LMClient.from_credentials(creds)

        # Direct instantiation
        client = LMClient("company", "access_id", "access_key")

        # Basic operations
        devices = client.get("/device/devices", params={"filter": "displayName:myhost"})

        # Paginate through all results
        for device in client.paginate("/device/devices"):
            print(device["displayName"])
    """

    BASE_PATH: str = "/santaba/rest"
    DEFAULT_TIMEOUT: int = 30
    DEFAULT_PAGE_SIZE: int = 250

    def __init__(
        self,
        company: str,
        access_id: str,
        access_key: str | SecretStr,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        Initialize the LogicMonitor API client.

        Args:
            company: LogicMonitor company/account name
            access_id: API access ID
            access_key: API access key
            timeout: Request timeout in seconds
        """
        self.company = company
        self.access_id = access_id
        self._access_key = access_key if isinstance(access_key, SecretStr) else SecretStr(access_key)
        self.timeout = timeout
        self.base_url = f"https://{company}.logicmonitor.com{self.BASE_PATH}"
        self._session = requests.Session()

    @classmethod
    def from_credentials(cls, credentials: LMCredentials, timeout: int = DEFAULT_TIMEOUT) -> LMClient:
        """
        Create client from LMCredentials object.

        Args:
            credentials: LMCredentials instance
            timeout: Request timeout in seconds

        Returns:
            Configured LMClient instance
        """
        return cls(
            company=credentials.company,
            access_id=credentials.access_id,
            access_key=credentials.access_key,
            timeout=timeout,
        )

    def _build_headers(self, method: str, resource_path: str, body: str = "") -> dict[str, str]:
        """Build authentication headers for a request."""
        return generate_auth_headers(
            access_id=self.access_id,
            access_key=self._access_key,
            method=method,
            resource_path=resource_path,
            data=body,
        ).to_dict()

    def _handle_response(self, response: requests.Response) -> dict[str, Any]:
        """
        Handle API response and raise appropriate exceptions.

        Args:
            response: requests.Response object

        Returns:
            Parsed JSON response data

        Raises:
            InvalidCredentialsError: For 401 responses
            APINotFoundError: For 404 responses
            APIRateLimitError: For 429 responses
            APIValidationError: For 400 responses
            APIError: For other error responses
        """
        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text}

        if response.status_code == 401:
            error_msg = data.get("errmsg") or data.get("message") or "Invalid credentials"
            raise InvalidCredentialsError(error_msg)

        if response.status_code == 404:
            raise APINotFoundError("Resource", response.url)

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise APIRateLimitError(int(retry_after) if retry_after else None)

        if response.status_code >= 400:
            error_msg = data.get("errmsg") or data.get("errorMessage") or response.text
            if response.status_code == 400:
                raise APIValidationError(error_msg, response.status_code, data)
            raise APIError(error_msg, response.status_code, data)

        # Normalize response structure - v3 API returns items at top level
        if "items" in data and "data" not in data:
            data = {"data": data}

        return data

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make an authenticated request to the LogicMonitor API.

        Args:
            method: HTTP method (GET, POST, PATCH, PUT, DELETE)
            path: API path (e.g., '/device/devices')
            params: Query parameters
            json_data: JSON body for POST/PATCH/PUT requests

        Returns:
            Parsed JSON response data

        Raises:
            APIError: If the API returns an error
            APIConnectionError: If connection fails
            APITimeoutError: If request times out
        """
        if not path.startswith("/"):
            path = "/" + path

        url = self.base_url + path
        body_str = json.dumps(json_data) if json_data else ""
        headers = self._build_headers(method, path, body_str)

        logger.debug(f"API {method} {path}")

        try:
            response = self._session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout as e:
            raise APITimeoutError(f"Request timed out: {e}")
        except requests.exceptions.ConnectionError as e:
            raise APIConnectionError(f"Connection failed: {e}")

        return self._handle_response(response)

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a GET request."""
        return self.request("GET", path, params=params)

    def post(self, path: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a POST request."""
        return self.request("POST", path, json_data=json_data)

    def patch(self, path: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a PATCH request."""
        return self.request("PATCH", path, json_data=json_data)

    def put(self, path: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a PUT request."""
        return self.request("PUT", path, json_data=json_data)

    def delete(self, path: str) -> dict[str, Any]:
        """Make a DELETE request."""
        return self.request("DELETE", path)

    def paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_items: int | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Iterate through all pages of a paginated endpoint.

        Args:
            path: API path
            params: Base query parameters
            page_size: Items per page
            max_items: Maximum items to fetch (None for unlimited)

        Yields:
            Individual items from the response
        """
        params = (params or {}).copy()
        params["size"] = page_size
        offset = 0
        count = 0

        while True:
            params["offset"] = offset
            response = self.get(path, params)

            items = response.get("data", {}).get("items", [])
            if not items:
                break

            for item in items:
                yield item
                count += 1
                if max_items and count >= max_items:
                    return

            total = response.get("data", {}).get("total", 0)
            offset += page_size

            if offset >= total:
                break

    def get_all(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch all items from a paginated endpoint.

        Args:
            path: API path
            params: Query parameters
            page_size: Items per page
            max_items: Maximum items to fetch

        Returns:
            List of all items
        """
        return list(self.paginate(path, params, page_size, max_items))

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def find_device_by_hostname(
        self,
        hostname: str,
        fields: str = "id,displayName,name,systemProperties",
    ) -> dict[str, Any] | None:
        """
        Find a device by hostname.

        Args:
            hostname: Device hostname (displayName)
            fields: Fields to return

        Returns:
            Device data or None if not found
        """
        params = {
            "filter": f'displayName:"{hostname}"',
            "fields": fields,
            "size": 1,
        }
        response = self.get("/device/devices", params)
        items = response.get("data", {}).get("items", [])
        return items[0] if items else None

    def get_device_datasources(
        self,
        device_id: int,
        datasource_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get datasources applied to a device.

        Args:
            device_id: Device ID
            datasource_name: Optional datasource name filter

        Returns:
            List of device datasources
        """
        params: dict[str, Any] = {"size": LMAPIConfig.MAX_PAGE_SIZE}
        if datasource_name:
            params["filter"] = f'dataSourceName:"{datasource_name}"'

        path = f"/device/devices/{device_id}/devicedatasources"
        return self.get_all(path, params)

    def get_datasource_instances(
        self,
        device_id: int,
        device_datasource_id: int,
        instance_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get instances for a device datasource.

        Args:
            device_id: Device ID
            device_datasource_id: Device datasource ID
            instance_name: Optional instance name filter

        Returns:
            List of instances
        """
        params: dict[str, Any] = {"size": LMAPIConfig.MAX_PAGE_SIZE}
        if instance_name:
            params["filter"] = f'displayName:"{instance_name}"'

        path = f"/device/devices/{device_id}/devicedatasources/{device_datasource_id}/instances"
        return self.get_all(path, params)
