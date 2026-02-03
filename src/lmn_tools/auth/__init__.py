"""
Authentication module for LogicMonitor API.
"""

from __future__ import annotations

from lmn_tools.auth.hmac import (
    AuthHeaders,
    generate_auth_headers,
    generate_lmv1_signature,
)

__all__ = [
    "AuthHeaders",
    "generate_auth_headers",
    "generate_lmv1_signature",
]
