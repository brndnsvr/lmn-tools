"""
HMAC-SHA256 signature generation for LogicMonitor API authentication.

The LogicMonitor API uses LMv1 authentication which requires:
1. A signature string: METHOD + EPOCH + DATA + RESOURCE_PATH
2. HMAC-SHA256 hash of the signature string
3. Base64 encoding of the hex digest

The Authorization header format is:
    LMv1 access_id:base64(hex(hmac-sha256(key, signature_string))):epoch
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from dataclasses import dataclass

from pydantic import SecretStr


@dataclass(frozen=True)
class AuthHeaders:
    """
    Container for LMv1 authentication headers.

    Attributes:
        authorization: The Authorization header value
        content_type: Content-Type header (always application/json)
        x_version: X-Version header for API version
        epoch: The epoch timestamp used in signature
    """

    authorization: str
    content_type: str = "application/json"
    x_version: str = "3"
    epoch: int = 0

    def to_dict(self) -> dict[str, str]:
        """Convert to header dictionary for requests."""
        return {
            "Authorization": self.authorization,
            "Content-Type": self.content_type,
            "X-Version": self.x_version,
        }


def generate_lmv1_signature(
    access_key: str,
    method: str,
    epoch: int,
    data: str,
    resource_path: str,
) -> str:
    """
    Generate HMAC-SHA256 signature for LMv1 authentication.

    The signature is computed as:
        base64(hex(HMAC-SHA256(access_key, method + epoch + data + resource_path)))

    Args:
        access_key: LogicMonitor API access key
        method: HTTP method (GET, POST, etc.)
        epoch: Unix timestamp in milliseconds
        data: Request body (empty string for GET)
        resource_path: API resource path (e.g., /device/devices)

    Returns:
        Base64-encoded signature string
    """
    # Build signature string: METHOD + EPOCH + DATA + RESOURCE_PATH
    signature_string = f"{method.upper()}{epoch}{data}{resource_path}"

    # Generate HMAC-SHA256 hash
    hmac_hash = hmac.new(
        access_key.encode("utf-8"),
        msg=signature_string.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    # Base64 encode the hex digest
    signature = base64.b64encode(hmac_hash.encode("utf-8")).decode("utf-8")

    return signature


def generate_auth_headers(
    access_id: str,
    access_key: str | SecretStr,
    method: str,
    resource_path: str,
    data: str = "",
    epoch: int | None = None,
) -> AuthHeaders:
    """
    Generate complete LMv1 authentication headers.

    Args:
        access_id: LogicMonitor API access ID
        access_key: LogicMonitor API access key
        method: HTTP method
        resource_path: API resource path (without /santaba/rest prefix)
        data: Request body (empty string for GET)
        epoch: Optional epoch timestamp (uses current time if not provided)

    Returns:
        AuthHeaders containing all required headers

    Example:
        >>> headers = generate_auth_headers(
        ...     access_id="abc123",
        ...     access_key="secret",
        ...     method="GET",
        ...     resource_path="/device/devices"
        ... )
        >>> requests.get(url, headers=headers.to_dict())
    """
    # Extract secret value if SecretStr
    if isinstance(access_key, SecretStr):
        access_key = access_key.get_secret_value()

    # Generate epoch if not provided
    if epoch is None:
        epoch = int(time.time() * 1000)

    signature = generate_lmv1_signature(
        access_key=access_key,
        method=method,
        epoch=epoch,
        data=data,
        resource_path=resource_path,
    )

    # Build authorization header: LMv1 accessId:signature:epoch
    authorization = f"LMv1 {access_id}:{signature}:{epoch}"

    return AuthHeaders(authorization=authorization, epoch=epoch)
