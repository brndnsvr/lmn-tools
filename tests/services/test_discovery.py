"""
Tests for NetscanService.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lmn_tools.services.discovery import NetscanMethod, NetscanService


@pytest.fixture
def service(mock_client: MagicMock) -> NetscanService:
    """Create NetscanService with mock client."""
    return NetscanService(mock_client)


class TestNetscanService:
    """Tests for NetscanService."""

    def test_base_path(self, service: NetscanService) -> None:
        """Test base_path property."""
        assert service.base_path == "/setting/netscans"

    def test_run(self, service: NetscanService, mock_client: MagicMock) -> None:
        """Test triggering a netscan run."""
        mock_client.post.return_value = {"status": "scheduled"}

        result = service.run(123)

        mock_client.post.assert_called_once_with(
            "/setting/netscans/123/executenow",
            json_data={},
        )
        assert result["status"] == "scheduled"

    def test_get_execution_status(self, service: NetscanService, mock_client: MagicMock) -> None:
        """Test getting netscan execution status."""
        mock_client.get.return_value = {
            "name": "TestScan",
            "nextStart": "2024-01-15",
            "lastExecutedOn": 1700000000000,
            "lastExecutedOnLocal": "2024-01-14",
        }

        result = service.get_execution_status(123)

        mock_client.get.assert_called_once_with("/setting/netscans/123")
        assert result["id"] == 123
        assert result["name"] == "TestScan"
        assert result["nextStart"] == "2024-01-15"

    def test_get_execution_status_with_data_wrapper(
        self, service: NetscanService, mock_client: MagicMock
    ) -> None:
        """Test get_execution_status when response has data wrapper."""
        mock_client.get.return_value = {
            "data": {
                "name": "WrappedScan",
                "lastExecutedOn": 1700000000000,
            }
        }

        result = service.get_execution_status(123)

        assert result["name"] == "WrappedScan"

    def test_list_by_collector(self, service: NetscanService, mock_client: MagicMock) -> None:
        """Test listing netscans by collector."""
        mock_client.get_all.return_value = [{"id": 1, "collectorId": 10}]

        result = service.list_by_collector(10)

        mock_client.get_all.assert_called_once()
        call_args = mock_client.get_all.call_args
        assert "collector.id:10" in call_args[0][1]["filter"]
        assert len(result) == 1

    def test_list_by_collector_with_max_items(
        self, service: NetscanService, mock_client: MagicMock
    ) -> None:
        """Test list_by_collector with max_items."""
        mock_client.get_all.return_value = []

        service.list_by_collector(10, max_items=25)

        call_args = mock_client.get_all.call_args
        assert call_args[1]["max_items"] == 25

    def test_list_by_group(self, service: NetscanService, mock_client: MagicMock) -> None:
        """Test listing netscans by group."""
        mock_client.get_all.return_value = [{"id": 2, "groupId": 5}]

        service.list_by_group(5)

        call_args = mock_client.get_all.call_args
        assert "group.id:5" in call_args[0][1]["filter"]

    def test_create_icmp_scan(self, service: NetscanService, mock_client: MagicMock) -> None:
        """Test creating an ICMP scan."""
        mock_client.post.return_value = {"id": 123, "name": "TestScan"}

        result = service.create_icmp_scan(
            name="TestScan",
            collector_id=10,
            group_id=5,
            subnet="192.168.1.0/24",
            description="Test description",
        )

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        data = call_args[1]["json_data"]
        assert data["name"] == "TestScan"
        assert data["collector"] == 10
        assert data["group"]["id"] == 5
        assert data["subnet"] == "192.168.1.0/24"
        assert data["method"] == "nmap"
        assert data["description"] == "Test description"
        assert result["id"] == 123

    def test_create_icmp_scan_no_description(
        self, service: NetscanService, mock_client: MagicMock
    ) -> None:
        """Test creating an ICMP scan without description."""
        mock_client.post.return_value = {"id": 124}

        service.create_icmp_scan(
            name="MinimalScan",
            collector_id=5,
            group_id=1,
            subnet="10.0.0.0/8",
        )

        call_args = mock_client.post.call_args
        data = call_args[1]["json_data"]
        assert data["description"] == ""

    def test_enable(self, service: NetscanService, mock_client: MagicMock) -> None:
        """Test enabling a netscan."""
        mock_client.patch.return_value = {"id": 123, "disabled": False}

        service.enable(123)

        mock_client.patch.assert_called_once_with(
            "/setting/netscans/123",
            json_data={"disabled": False},
        )

    def test_disable(self, service: NetscanService, mock_client: MagicMock) -> None:
        """Test disabling a netscan."""
        mock_client.patch.return_value = {"id": 123, "disabled": True}

        service.disable(123)

        mock_client.patch.assert_called_once_with(
            "/setting/netscans/123",
            json_data={"disabled": True},
        )


class TestNetscanMethod:
    """Tests for NetscanMethod enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert NetscanMethod.ICMP.value == "nmap"
        assert NetscanMethod.SCRIPT.value == "script"
        assert NetscanMethod.AWS.value == "aws"
        assert NetscanMethod.AZURE.value == "azure"
        assert NetscanMethod.GCP.value == "gcp"
        assert NetscanMethod.ENHANCED_SCRIPT.value == "enhancedScript"
