"""
Service modules for lmn-tools.

Contains higher-level services built on top of the API client
and collectors, such as device resolution and dashboard building.
"""

from __future__ import annotations

from lmn_tools.services.access import AccessGroupService, access_group_service
from lmn_tools.services.audit import AuditLogService, audit_log_service
from lmn_tools.services.base import BaseService
from lmn_tools.services.batch import BatchJobService, batchjob_service
from lmn_tools.services.dashboards import (
    DashboardGroupService,
    DashboardService,
    WidgetService,
    dashboard_group_service,
    dashboard_service,
    widget_service,
)
from lmn_tools.services.discovery import NetscanService, netscan_service
from lmn_tools.services.modules import (
    LogicModuleService,
    ModuleType,
    configsource_service,
    datasource_service,
    eventsource_service,
    propertysource_service,
    topologysource_service,
)
from lmn_tools.services.notifications import RecipientGroupService, recipient_group_service
from lmn_tools.services.operations import OpsNoteService, opsnote_service
from lmn_tools.services.serviceinsight import (
    ServiceGroupService,
    ServiceService,
    service_group_service,
    service_service,
)
from lmn_tools.services.tokens import APITokenService, api_token_service
from lmn_tools.services.topology import TopologyService, topology_service

__all__ = [  # noqa: RUF022
    # Base
    "BaseService",
    # LogicModules
    "LogicModuleService",
    "ModuleType",
    "configsource_service",
    "datasource_service",
    "eventsource_service",
    "propertysource_service",
    "topologysource_service",
    # Dashboards
    "DashboardService",
    "DashboardGroupService",
    "WidgetService",
    "dashboard_service",
    "dashboard_group_service",
    "widget_service",
    # Operations
    "OpsNoteService",
    "opsnote_service",
    # Discovery
    "NetscanService",
    "netscan_service",
    # Batch
    "BatchJobService",
    "batchjob_service",
    # Notifications
    "RecipientGroupService",
    "recipient_group_service",
    # Tokens
    "APITokenService",
    "api_token_service",
    # Access
    "AccessGroupService",
    "access_group_service",
    # Audit
    "AuditLogService",
    "audit_log_service",
    # Topology
    "TopologyService",
    "topology_service",
    # Services (Service Insight)
    "ServiceService",
    "ServiceGroupService",
    "service_service",
    "service_group_service",
]
