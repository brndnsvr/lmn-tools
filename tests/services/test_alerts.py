"""
Tests for AlertService and SDTService.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from lmn_tools.services.alerts import AlertService, AlertSeverity, SDTService, SDTType


@pytest.fixture
def alert_service(mock_client: MagicMock) -> AlertService:
    """Create AlertService with mock client."""
    return AlertService(mock_client)


@pytest.fixture
def sdt_service(mock_client: MagicMock) -> SDTService:
    """Create SDTService with mock client."""
    return SDTService(mock_client)


class TestAlertService:
    """Tests for AlertService."""

    def test_base_path(self, alert_service: AlertService) -> None:
        """Test base_path property."""
        assert alert_service.base_path == "/alert/alerts"

    def test_list_active(self, alert_service: AlertService, mock_client: MagicMock) -> None:
        """Test listing active alerts."""
        mock_client.get_all.return_value = [{"id": "A1", "cleared": False}]

        result = alert_service.list_active()

        mock_client.get_all.assert_called_once()
        call_args = mock_client.get_all.call_args
        assert 'cleared:"false"' in call_args[0][1]["filter"]
        assert len(result) == 1

    def test_list_active_with_severity(self, alert_service: AlertService, mock_client: MagicMock) -> None:
        """Test listing active alerts filtered by severity."""
        mock_client.get_all.return_value = [{"id": "A2", "severity": 4}]

        alert_service.list_active(severity=AlertSeverity.CRITICAL)

        call_args = mock_client.get_all.call_args
        filter_str = call_args[0][1]["filter"]
        assert 'cleared:"false"' in filter_str
        assert 'severity:"critical"' in filter_str

    def test_list_active_with_device_id(self, alert_service: AlertService, mock_client: MagicMock) -> None:
        """Test listing active alerts for a specific device."""
        mock_client.get_all.return_value = []

        alert_service.list_active(device_id=123)

        call_args = mock_client.get_all.call_args
        filter_str = call_args[0][1]["filter"]
        assert "monitorObjectId:123" in filter_str

    def test_list_acknowledged(self, alert_service: AlertService, mock_client: MagicMock) -> None:
        """Test listing acknowledged alerts."""
        mock_client.get_all.return_value = [{"id": "A3", "acked": True}]

        alert_service.list_acknowledged()

        call_args = mock_client.get_all.call_args
        assert 'acked:"true"' in call_args[0][1]["filter"]
        assert 'cleared:"false"' in call_args[0][1]["filter"]

    def test_list_critical(self, alert_service: AlertService, mock_client: MagicMock) -> None:
        """Test listing critical alerts."""
        mock_client.get_all.return_value = [{"id": "A4", "severity": 4}]

        alert_service.list_critical()

        call_args = mock_client.get_all.call_args
        filter_str = call_args[0][1]["filter"]
        assert 'severity:"critical"' in filter_str

    def test_acknowledge(self, alert_service: AlertService, mock_client: MagicMock) -> None:
        """Test acknowledging an alert."""
        mock_client.patch.return_value = {"id": "A1", "acked": True}

        result = alert_service.acknowledge("A1", "Working on it")

        mock_client.patch.assert_called_once_with(
            "/alert/alerts/A1",
            json_data={"acked": True, "ackedNote": "Working on it"},
        )
        assert result["acked"] is True

    def test_acknowledge_without_comment(self, alert_service: AlertService, mock_client: MagicMock) -> None:
        """Test acknowledging an alert without comment."""
        mock_client.patch.return_value = {"id": "A1", "acked": True}

        alert_service.acknowledge("A1")

        call_args = mock_client.patch.call_args
        data = call_args[1]["json_data"]
        assert data == {"acked": True}
        assert "ackedNote" not in data

    def test_add_note(self, alert_service: AlertService, mock_client: MagicMock) -> None:
        """Test adding a note to an alert."""
        mock_client.post.return_value = {"noteId": 123}

        alert_service.add_note("A1", "Investigation started")

        mock_client.post.assert_called_once_with(
            "/alert/alerts/A1/notes",
            json_data={"note": "Investigation started"},
        )

    def test_list_history(self, alert_service: AlertService, mock_client: MagicMock) -> None:
        """Test listing alert history."""
        mock_client.get_all.return_value = [{"id": "A1"}, {"id": "A2"}]

        alert_service.list_history(
            device_id=123,
            severity=AlertSeverity.ERROR,
            start_time=1700000000000,
            end_time=1700100000000,
        )

        call_args = mock_client.get_all.call_args
        filter_str = call_args[0][1]["filter"]
        assert "monitorObjectId:123" in filter_str
        assert 'severity:"error"' in filter_str
        assert "startEpoch>1700000000000" in filter_str
        assert "startEpoch<1700100000000" in filter_str

    def test_list_history_with_group_id(self, alert_service: AlertService, mock_client: MagicMock) -> None:
        """Test listing alert history filtered by group."""
        mock_client.get_all.return_value = []

        alert_service.list_history(group_id=456)

        call_args = mock_client.get_all.call_args
        filter_str = call_args[0][1]["filter"]
        assert "monitorObjectGroups~456" in filter_str

    @patch("lmn_tools.services.alerts.time.time")
    def test_get_trends(self, mock_time: MagicMock, alert_service: AlertService, mock_client: MagicMock) -> None:
        """Test getting alert trends."""
        mock_time.return_value = 1700000000  # Fixed timestamp
        mock_client.get_all.return_value = [
            {"severity": "warning", "monitorObjectName": "server1", "dataSourceName": "CPU", "startEpoch": 1699950000000},
            {"severity": "critical", "monitorObjectName": "server1", "dataSourceName": "Memory", "startEpoch": 1699960000000},
            {"severity": "warning", "monitorObjectName": "server2", "dataSourceName": "CPU", "startEpoch": 1699970000000},
        ]

        result = alert_service.get_trends(days=7)

        assert result["period_days"] == 7
        assert result["total_alerts"] == 3
        assert result["by_severity"]["warning"] == 2
        assert result["by_severity"]["critical"] == 1
        assert result["by_device"]["server1"] == 2
        assert result["by_datasource"]["CPU"] == 2


class TestSDTService:
    """Tests for SDTService."""

    def test_base_path(self, sdt_service: SDTService) -> None:
        """Test base_path property."""
        assert sdt_service.base_path == "/sdt/sdts"

    @patch("lmn_tools.services.alerts.time.time")
    def test_list_active(self, mock_time: MagicMock, sdt_service: SDTService, mock_client: MagicMock) -> None:
        """Test listing active SDTs."""
        mock_time.return_value = 1700000000
        mock_client.get_all.return_value = [{"id": 1, "isEffective": True}]

        sdt_service.list_active()

        call_args = mock_client.get_all.call_args
        filter_str = call_args[0][1]["filter"]
        assert "isEffective:true" in filter_str
        assert "startDateTime<1700000000000" in filter_str
        assert "endDateTime>1700000000000" in filter_str

    @patch("lmn_tools.services.alerts.time.time")
    def test_list_upcoming(self, mock_time: MagicMock, sdt_service: SDTService, mock_client: MagicMock) -> None:
        """Test listing upcoming SDTs."""
        mock_time.return_value = 1700000000
        mock_client.get_all.return_value = []

        sdt_service.list_upcoming(days=7)

        call_args = mock_client.get_all.call_args
        filter_str = call_args[0][1]["filter"]
        assert "startDateTime>1700000000000" in filter_str
        expected_future = 1700000000000 + (7 * 24 * 60 * 60 * 1000)
        assert f"startDateTime<{expected_future}" in filter_str

    def test_list_for_device(self, sdt_service: SDTService, mock_client: MagicMock) -> None:
        """Test listing SDTs for a device."""
        mock_client.get_all.return_value = [{"id": 1, "deviceId": 123}]

        sdt_service.list_for_device(123)

        call_args = mock_client.get_all.call_args
        assert call_args[0][1]["filter"] == "deviceId:123"

    @patch("lmn_tools.services.alerts.time.time")
    def test_create_device_sdt(self, mock_time: MagicMock, sdt_service: SDTService, mock_client: MagicMock) -> None:
        """Test creating a device SDT."""
        mock_time.return_value = 1700000000
        mock_client.post.return_value = {"id": 1, "type": "DeviceSDT"}

        sdt_service.create_device_sdt(
            device_id=123,
            duration_mins=60,
            comment="Maintenance window",
        )

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        data = call_args[1]["json_data"]
        assert data["type"] == SDTType.DEVICE.value
        assert data["deviceId"] == 123
        assert data["startDateTime"] == 1700000000000
        assert data["endDateTime"] == 1700000000000 + (60 * 60 * 1000)
        assert data["comment"] == "Maintenance window"

    @patch("lmn_tools.services.alerts.time.time")
    def test_create_group_sdt(self, mock_time: MagicMock, sdt_service: SDTService, mock_client: MagicMock) -> None:
        """Test creating a device group SDT."""
        mock_time.return_value = 1700000000
        mock_client.post.return_value = {"id": 2, "type": "DeviceGroupSDT"}

        sdt_service.create_group_sdt(
            group_id=456,
            duration_mins=120,
            comment="Group maintenance",
        )

        call_args = mock_client.post.call_args
        data = call_args[1]["json_data"]
        assert data["type"] == SDTType.DEVICE_GROUP.value
        assert data["deviceGroupId"] == 456
        assert data["endDateTime"] == 1700000000000 + (120 * 60 * 1000)

    @patch("lmn_tools.services.alerts.time.time")
    def test_create_datasource_sdt(self, mock_time: MagicMock, sdt_service: SDTService, mock_client: MagicMock) -> None:
        """Test creating a datasource SDT."""
        mock_time.return_value = 1700000000
        mock_client.post.return_value = {"id": 3, "type": "DeviceDataSourceSDT"}

        sdt_service.create_datasource_sdt(
            device_id=123,
            datasource_id=789,
            duration_mins=30,
        )

        call_args = mock_client.post.call_args
        data = call_args[1]["json_data"]
        assert data["type"] == SDTType.DATASOURCE.value
        assert data["deviceId"] == 123
        assert data["dataSourceId"] == 789


class TestAlertSeverity:
    """Tests for AlertSeverity enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.ERROR.value == "error"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestSDTType:
    """Tests for SDTType enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert SDTType.DEVICE.value == "DeviceSDT"
        assert SDTType.DEVICE_GROUP.value == "DeviceGroupSDT"
        assert SDTType.DATASOURCE.value == "DeviceDataSourceSDT"
        assert SDTType.INSTANCE.value == "DeviceDataSourceInstanceSDT"
        assert SDTType.COLLECTOR.value == "CollectorSDT"
        assert SDTType.WEBSITE.value == "WebsiteSDT"
