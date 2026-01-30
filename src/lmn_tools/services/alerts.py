"""
Service for LogicMonitor Alerts and SDT (Scheduled Downtime).

Provides operations for managing alerts and maintenance windows.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any

from lmn_tools.api.client import LMClient
from lmn_tools.services.base import BaseService


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SDTType(str, Enum):
    """SDT (Scheduled Downtime) types."""
    DEVICE = "DeviceSDT"
    DEVICE_GROUP = "DeviceGroupSDT"
    DATASOURCE = "DeviceDataSourceSDT"
    INSTANCE = "DeviceDataSourceInstanceSDT"
    DATASOURCE_GROUP = "DeviceDataSourceGroupSDT"
    COLLECTOR = "CollectorSDT"
    WEBSITE = "WebsiteSDT"


class AlertService(BaseService):
    """
    Service for managing LogicMonitor alerts.

    Usage:
        svc = AlertService(client)
        alerts = svc.list_active()
        svc.acknowledge(alert_id, "Working on it")
    """

    @property
    def base_path(self) -> str:
        return "/alert/alerts"

    def list_active(
        self,
        severity: AlertSeverity | str | None = None,
        device_id: int | None = None,
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        List active (uncleared) alerts.

        Args:
            severity: Optional severity filter
            device_id: Optional device ID filter
            max_items: Maximum alerts to return

        Returns:
            List of active alerts
        """
        filters = ['cleared:"false"']
        if severity:
            sev_value = severity.value if isinstance(severity, AlertSeverity) else severity
            filters.append(f'severity:"{sev_value}"')
        if device_id:
            filters.append(f"monitorObjectId:{device_id}")

        return self.list(filter=",".join(filters), max_items=max_items)

    def list_acknowledged(self, max_items: int | None = None) -> list[dict[str, Any]]:
        """List acknowledged alerts."""
        return self.list(filter='acked:"true",cleared:"false"', max_items=max_items)

    def list_critical(self, max_items: int | None = None) -> list[dict[str, Any]]:
        """List critical severity alerts."""
        return self.list_active(severity=AlertSeverity.CRITICAL, max_items=max_items)

    def acknowledge(self, alert_id: str, comment: str = "") -> dict[str, Any]:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID
            comment: Acknowledgement comment

        Returns:
            Updated alert
        """
        data: dict[str, Any] = {"acked": True}
        if comment:
            data["ackedNote"] = comment
        return self.client.patch(f"{self.base_path}/{alert_id}", json_data=data)

    def add_note(self, alert_id: str, note: str) -> dict[str, Any]:
        """
        Add a note to an alert.

        Args:
            alert_id: Alert ID
            note: Note text

        Returns:
            Updated alert
        """
        return self.client.post(
            f"{self.base_path}/{alert_id}/notes",
            json_data={"note": note},
        )

    def list_history(
        self,
        device_id: int | None = None,
        group_id: int | None = None,
        severity: AlertSeverity | str | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        List historical alerts (including cleared).

        Args:
            device_id: Optional device ID filter
            group_id: Optional device group ID filter
            severity: Optional severity filter
            start_time: Optional start timestamp (epoch ms)
            end_time: Optional end timestamp (epoch ms)
            max_items: Maximum alerts to return

        Returns:
            List of historical alerts
        """
        filters = []
        if device_id:
            filters.append(f"monitorObjectId:{device_id}")
        if group_id:
            filters.append(f"monitorObjectGroups~{group_id}")
        if severity:
            sev_value = severity.value if isinstance(severity, AlertSeverity) else severity
            filters.append(f'severity:"{sev_value}"')
        if start_time:
            filters.append(f"startEpoch>{start_time}")
        if end_time:
            filters.append(f"startEpoch<{end_time}")

        filter_str = ",".join(filters) if filters else None
        return self.list(filter=filter_str, max_items=max_items)

    def get_trends(
        self,
        days: int = 7,
        group_by: str = "severity",
    ) -> dict[str, Any]:
        """
        Get alert trends over a time period.

        Args:
            days: Number of days to analyze
            group_by: Group results by (severity, device, datasource)

        Returns:
            Trend data with counts
        """
        now = int(time.time() * 1000)
        start_time = now - (days * 24 * 60 * 60 * 1000)

        alerts = self.list_history(start_time=start_time, max_items=10000)

        # Count by severity
        severity_counts: dict[str, int] = {}
        device_counts: dict[str, int] = {}
        datasource_counts: dict[str, int] = {}
        daily_counts: dict[str, int] = {}

        for alert in alerts:
            # Severity
            sev = str(alert.get("severity", "unknown"))
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

            # Device
            device = alert.get("monitorObjectName", "unknown")
            device_counts[device] = device_counts.get(device, 0) + 1

            # DataSource
            ds = alert.get("dataSourceName", "unknown")
            datasource_counts[ds] = datasource_counts.get(ds, 0) + 1

            # Daily
            start_epoch = alert.get("startEpoch", 0)
            if start_epoch:
                start_secs = start_epoch / 1000 if start_epoch >= 1e12 else start_epoch
                from datetime import datetime
                day = datetime.fromtimestamp(start_secs).strftime("%Y-%m-%d")
                daily_counts[day] = daily_counts.get(day, 0) + 1

        return {
            "period_days": days,
            "total_alerts": len(alerts),
            "by_severity": severity_counts,
            "by_device": dict(sorted(device_counts.items(), key=lambda x: x[1], reverse=True)[:20]),
            "by_datasource": dict(sorted(datasource_counts.items(), key=lambda x: x[1], reverse=True)[:20]),
            "by_day": dict(sorted(daily_counts.items())),
        }


class SDTService(BaseService):
    """
    Service for managing LogicMonitor SDT (Scheduled Downtime).

    Usage:
        svc = SDTService(client)
        sdts = svc.list_active()
        svc.create_device_sdt(device_id=123, duration_mins=60, comment="Maintenance")
    """

    @property
    def base_path(self) -> str:
        return "/sdt/sdts"

    def list_active(self) -> list[dict[str, Any]]:
        """List currently active SDTs."""
        now = int(time.time() * 1000)
        return self.list(filter=f"isEffective:true,startDateTime<{now},endDateTime>{now}")

    def list_upcoming(self, days: int = 7) -> list[dict[str, Any]]:
        """
        List upcoming SDTs within a time window.

        Args:
            days: Number of days ahead to look

        Returns:
            List of upcoming SDTs
        """
        now = int(time.time() * 1000)
        future = now + (days * 24 * 60 * 60 * 1000)
        return self.list(filter=f"startDateTime>{now},startDateTime<{future}")

    def list_for_device(self, device_id: int) -> list[dict[str, Any]]:
        """List SDTs for a specific device."""
        return self.list(filter=f"deviceId:{device_id}")

    def create_device_sdt(
        self,
        device_id: int,
        duration_mins: int,
        comment: str = "",
        start_time: int | None = None,
    ) -> dict[str, Any]:
        """
        Create an SDT for a device.

        Args:
            device_id: Device ID
            duration_mins: Duration in minutes
            comment: SDT comment
            start_time: Start timestamp (ms), defaults to now

        Returns:
            Created SDT
        """
        if start_time is None:
            start_time = int(time.time() * 1000)

        end_time = start_time + (duration_mins * 60 * 1000)

        data = {
            "type": SDTType.DEVICE.value,
            "deviceId": device_id,
            "startDateTime": start_time,
            "endDateTime": end_time,
            "comment": comment,
        }
        return self.create(data)

    def create_group_sdt(
        self,
        group_id: int,
        duration_mins: int,
        comment: str = "",
        start_time: int | None = None,
    ) -> dict[str, Any]:
        """
        Create an SDT for a device group.

        Args:
            group_id: Device group ID
            duration_mins: Duration in minutes
            comment: SDT comment
            start_time: Start timestamp (ms), defaults to now

        Returns:
            Created SDT
        """
        if start_time is None:
            start_time = int(time.time() * 1000)

        end_time = start_time + (duration_mins * 60 * 1000)

        data = {
            "type": SDTType.DEVICE_GROUP.value,
            "deviceGroupId": group_id,
            "startDateTime": start_time,
            "endDateTime": end_time,
            "comment": comment,
        }
        return self.create(data)

    def create_datasource_sdt(
        self,
        device_id: int,
        datasource_id: int,
        duration_mins: int,
        comment: str = "",
        start_time: int | None = None,
    ) -> dict[str, Any]:
        """
        Create an SDT for a device datasource.

        Args:
            device_id: Device ID
            datasource_id: DataSource ID
            duration_mins: Duration in minutes
            comment: SDT comment
            start_time: Start timestamp (ms), defaults to now

        Returns:
            Created SDT
        """
        if start_time is None:
            start_time = int(time.time() * 1000)

        end_time = start_time + (duration_mins * 60 * 1000)

        data = {
            "type": SDTType.DATASOURCE.value,
            "deviceId": device_id,
            "dataSourceId": datasource_id,
            "startDateTime": start_time,
            "endDateTime": end_time,
            "comment": comment,
        }
        return self.create(data)


class EscalationChainService(BaseService):
    """Service for managing escalation chains."""

    @property
    def base_path(self) -> str:
        return "/setting/alert/chains"


class IntegrationService(BaseService):
    """Service for managing integrations."""

    @property
    def base_path(self) -> str:
        return "/setting/integrations"


class WebsiteService(BaseService):
    """Service for managing websites (synthetic monitoring)."""

    @property
    def base_path(self) -> str:
        return "/website/websites"

    def list_checks(self, website_id: int) -> list[dict[str, Any]]:
        """List checks for a website."""
        response = self.client.get(f"{self.base_path}/{website_id}/checkpoints")
        items: list[dict[str, Any]] = response.get("items", response.get("data", {}).get("items", []))
        return items

    def list_by_group(self, group_id: int) -> list[dict[str, Any]]:
        """List websites in a group."""
        return self.list(filter=f"groupId:{group_id}")


class AlertRuleService(BaseService):
    """Service for managing alert rules (threshold rules)."""

    @property
    def base_path(self) -> str:
        return "/setting/alert/rules"

    def list_by_datasource(self, datasource_id: int) -> list[dict[str, Any]]:
        """List alert rules for a specific DataSource."""
        return self.list(filter=f"dataSourceId:{datasource_id}")

    def list_by_severity(self, severity: str) -> list[dict[str, Any]]:
        """List alert rules by severity level."""
        return self.list(filter=f"levelStr:{severity}")

    def enable(self, rule_id: int) -> dict[str, Any]:
        """Enable an alert rule."""
        return self.update(rule_id, {"disableAlerting": False})

    def disable(self, rule_id: int) -> dict[str, Any]:
        """Disable an alert rule."""
        return self.update(rule_id, {"disableAlerting": True})


def alert_service(client: LMClient) -> AlertService:
    """Create an alert service."""
    return AlertService(client)


def sdt_service(client: LMClient) -> SDTService:
    """Create an SDT service."""
    return SDTService(client)


def alert_rule_service(client: LMClient) -> AlertRuleService:
    """Create an alert rule service."""
    return AlertRuleService(client)
