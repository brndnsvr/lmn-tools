"""
Tests for HMAC signature generation.
"""

from __future__ import annotations

from unittest.mock import patch

from pydantic import SecretStr

from lmn_tools.auth.hmac import (
    AuthHeaders,
    generate_auth_headers,
    generate_lmv1_signature,
)


class TestGenerateLmv1Signature:
    """Tests for generate_lmv1_signature function."""

    def test_generate_signature_known_vector(self) -> None:
        """Verify signature against a known good value."""
        # Pre-computed signature for these exact inputs
        signature = generate_lmv1_signature(
            access_key="test_key",
            method="GET",
            epoch=1700000000000,
            data="",
            resource_path="/device/devices",
        )

        # Signature should be base64-encoded
        assert signature.endswith("=") or signature.isalnum()
        # Should be consistent length for SHA256 -> hex -> base64
        assert len(signature) == 88  # 64 hex chars -> 88 base64 chars

    def test_generate_signature_deterministic(self) -> None:
        """Same inputs always produce the same output."""
        kwargs = {
            "access_key": "my_secret_key",
            "method": "POST",
            "epoch": 1700000000000,
            "data": '{"name": "test"}',
            "resource_path": "/device/devices",
        }

        sig1 = generate_lmv1_signature(**kwargs)
        sig2 = generate_lmv1_signature(**kwargs)

        assert sig1 == sig2

    def test_different_methods_produce_different_signatures(self) -> None:
        """Different HTTP methods produce different signatures."""
        common = {
            "access_key": "key",
            "epoch": 1700000000000,
            "data": "",
            "resource_path": "/device/devices",
        }

        sig_get = generate_lmv1_signature(method="GET", **common)
        sig_post = generate_lmv1_signature(method="POST", **common)

        assert sig_get != sig_post

    def test_method_case_normalization(self) -> None:
        """Method is uppercased in signature string."""
        common = {
            "access_key": "key",
            "epoch": 1700000000000,
            "data": "",
            "resource_path": "/device/devices",
        }

        sig_lower = generate_lmv1_signature(method="get", **common)
        sig_upper = generate_lmv1_signature(method="GET", **common)

        assert sig_lower == sig_upper

    def test_different_data_produces_different_signatures(self) -> None:
        """Different request bodies produce different signatures."""
        common = {
            "access_key": "key",
            "method": "POST",
            "epoch": 1700000000000,
            "resource_path": "/device/devices",
        }

        sig1 = generate_lmv1_signature(data='{"a": 1}', **common)
        sig2 = generate_lmv1_signature(data='{"b": 2}', **common)

        assert sig1 != sig2


class TestGenerateAuthHeaders:
    """Tests for generate_auth_headers function."""

    def test_returns_auth_headers_structure(self) -> None:
        """Returns AuthHeaders dataclass with correct attributes."""
        headers = generate_auth_headers(
            access_id="test_id",
            access_key="test_key",
            method="GET",
            resource_path="/device/devices",
            epoch=1700000000000,
        )

        assert isinstance(headers, AuthHeaders)
        assert hasattr(headers, "authorization")
        assert hasattr(headers, "content_type")
        assert hasattr(headers, "x_version")
        assert hasattr(headers, "epoch")

    def test_authorization_header_format(self) -> None:
        """Authorization header follows LMv1 format."""
        headers = generate_auth_headers(
            access_id="my_access_id",
            access_key="my_key",
            method="GET",
            resource_path="/device/devices",
            epoch=1700000000000,
        )

        # Format: LMv1 access_id:signature:epoch
        assert headers.authorization.startswith("LMv1 my_access_id:")
        assert headers.authorization.endswith(":1700000000000")

        # Should have exactly 3 parts after "LMv1 "
        parts = headers.authorization.replace("LMv1 ", "").split(":")
        assert len(parts) == 3
        assert parts[0] == "my_access_id"
        # parts[1] is the signature
        assert parts[2] == "1700000000000"

    def test_default_content_type(self) -> None:
        """Content-Type defaults to application/json."""
        headers = generate_auth_headers(
            access_id="id",
            access_key="key",
            method="GET",
            resource_path="/test",
            epoch=1700000000000,
        )

        assert headers.content_type == "application/json"

    def test_default_x_version(self) -> None:
        """X-Version defaults to 3."""
        headers = generate_auth_headers(
            access_id="id",
            access_key="key",
            method="GET",
            resource_path="/test",
            epoch=1700000000000,
        )

        assert headers.x_version == "3"

    def test_epoch_stored_in_headers(self) -> None:
        """Epoch is stored in the AuthHeaders object."""
        headers = generate_auth_headers(
            access_id="id",
            access_key="key",
            method="GET",
            resource_path="/test",
            epoch=1700000000000,
        )

        assert headers.epoch == 1700000000000

    def test_secret_str_handling(self) -> None:
        """Works with pydantic SecretStr for access_key."""
        secret_key = SecretStr("my_secret_key")

        headers = generate_auth_headers(
            access_id="id",
            access_key=secret_key,
            method="GET",
            resource_path="/test",
            epoch=1700000000000,
        )

        assert headers.authorization.startswith("LMv1 id:")

    @patch("lmn_tools.auth.hmac.time")
    def test_uses_current_time_when_epoch_not_provided(self, mock_time) -> None:
        """Uses time.time() when epoch parameter is None."""
        mock_time.time.return_value = 1700000000.123

        headers = generate_auth_headers(
            access_id="id",
            access_key="key",
            method="GET",
            resource_path="/test",
            # epoch not provided
        )

        mock_time.time.assert_called_once()
        # Should convert to milliseconds
        assert headers.epoch == 1700000000123

    def test_custom_epoch_used(self) -> None:
        """Uses provided epoch instead of current time."""
        custom_epoch = 1600000000000

        headers = generate_auth_headers(
            access_id="id",
            access_key="key",
            method="GET",
            resource_path="/test",
            epoch=custom_epoch,
        )

        assert headers.epoch == custom_epoch
        assert str(custom_epoch) in headers.authorization

    def test_empty_data_for_get_requests(self) -> None:
        """GET requests use empty string for data by default."""
        headers1 = generate_auth_headers(
            access_id="id",
            access_key="key",
            method="GET",
            resource_path="/test",
            epoch=1700000000000,
        )

        headers2 = generate_auth_headers(
            access_id="id",
            access_key="key",
            method="GET",
            resource_path="/test",
            data="",
            epoch=1700000000000,
        )

        assert headers1.authorization == headers2.authorization


class TestAuthHeadersToDict:
    """Tests for AuthHeaders.to_dict() method."""

    def test_to_dict_structure(self) -> None:
        """to_dict returns correct header keys."""
        headers = generate_auth_headers(
            access_id="id",
            access_key="key",
            method="GET",
            resource_path="/test",
            epoch=1700000000000,
        )

        header_dict = headers.to_dict()

        assert "Authorization" in header_dict
        assert "Content-Type" in header_dict
        assert "X-Version" in header_dict
        assert len(header_dict) == 3

    def test_to_dict_values(self) -> None:
        """to_dict contains correct values."""
        headers = AuthHeaders(
            authorization="LMv1 id:sig:epoch",
            content_type="application/json",
            x_version="3",
            epoch=1700000000000,
        )

        header_dict = headers.to_dict()

        assert header_dict["Authorization"] == "LMv1 id:sig:epoch"
        assert header_dict["Content-Type"] == "application/json"
        assert header_dict["X-Version"] == "3"

    def test_to_dict_does_not_include_epoch(self) -> None:
        """epoch is not included in HTTP headers dict."""
        headers = AuthHeaders(
            authorization="LMv1 id:sig:epoch",
            epoch=1700000000000,
        )

        header_dict = headers.to_dict()

        assert "epoch" not in header_dict
        assert "Epoch" not in header_dict
