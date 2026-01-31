"""
Pydantic models for lmn-tools.

Contains data models for:
- Resolution: Resolved LogicMonitor resource identifiers
"""

from __future__ import annotations

from lmn_tools.models.discovery import (
    ResolutionSummary,
    ResolvedBGPPeer,
    ResolvedInterface,
)

__all__ = [
    "ResolutionSummary",
    "ResolvedBGPPeer",
    "ResolvedInterface",
]
