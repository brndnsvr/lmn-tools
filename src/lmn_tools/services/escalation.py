"""
Service for LogicMonitor Escalation Chains.

Provides operations for managing alert escalation workflows.
"""

from __future__ import annotations

from lmn_tools.api.client import LMClient
from lmn_tools.services.base import BaseService


class EscalationChainService(BaseService):
    """Service for managing LogicMonitor escalation chains."""

    @property
    def base_path(self) -> str:
        return "/setting/alert/chains"


def escalation_chain_service(client: LMClient) -> EscalationChainService:
    """Create an EscalationChainService instance."""
    return EscalationChainService(client)
