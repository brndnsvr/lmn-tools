"""
Tests for CollectorService and CollectorGroupService.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lmn_tools.services.collectors import (
    CollectorGroupService,
    CollectorService,
    CollectorStatus,
)


@pytest.fixture
def collector_service(mock_client: MagicMock) -> CollectorService:
    """Create CollectorService with mock client."""
    return CollectorService(mock_client)


@pytest.fixture
def collector_group_service(mock_client: MagicMock) -> CollectorGroupService:
    """Create CollectorGroupService with mock client."""
    return CollectorGroupService(mock_client)


class TestCollectorService:
    """Tests for CollectorService."""

    def test_base_path(self, collector_service: CollectorService) -> None:
        """Test base_path uses constant."""
        assert collector_service.base_path == "/setting/collector/collectors"

    def test_list_by_group(
        self, collector_service: CollectorService, mock_client: MagicMock
    ) -> None:
        """Test filtering by group."""
        mock_client.get_all.return_value = [
            {"id": 1, "collectorGroupId": 5},
            {"id": 2, "collectorGroupId": 5},
        ]

        result = collector_service.list_by_group(5)

        mock_client.get_all.assert_called_once()
        call_args = mock_client.get_all.call_args
        assert "collectorGroupId:5" in call_args[0][1]["filter"]
        assert len(result) == 2

    def test_list_by_status(
        self, collector_service: CollectorService, mock_client: MagicMock
    ) -> None:
        """Test filtering by status enum."""
        mock_client.get_all.return_value = [{"id": 1, "status": 0}]

        collector_service.list_by_status(CollectorStatus.DOWN)

        call_args = mock_client.get_all.call_args
        assert "status:0" in call_args[0][1]["filter"]

    def test_list_down(self, collector_service: CollectorService, mock_client: MagicMock) -> None:
        """Test convenience method for down collectors."""
        mock_client.get_all.return_value = [{"id": 1, "status": 0}]

        result = collector_service.list_down()

        call_args = mock_client.get_all.call_args
        assert "status:0" in call_args[0][1]["filter"]
        assert len(result) == 1

    def test_get_status(self, collector_service: CollectorService, mock_client: MagicMock) -> None:
        """Test health metrics extraction."""
        mock_client.get.return_value = {
            "id": 1,
            "status": 1,
            "upTime": 86400000,
            "numberOfHosts": 50,
            "build": "31.004",
        }

        result = collector_service.get_status(1)

        assert result["status"] == 1
        assert result["upTime"] == 86400000
        assert result["numberOfHosts"] == 50
        assert result["build"] == "31.004"

    def test_get_installer_url_default(
        self, collector_service: CollectorService, mock_client: MagicMock
    ) -> None:
        """Test getting installer URL without version."""
        mock_client.get.return_value = {
            "version": "31.004",
            "link": "https://example.com/installer",
        }

        result = collector_service.get_installer_url("linux64")

        mock_client.get.assert_called_once_with("/setting/collector/installers/linux64")
        assert result["version"] == "31.004"

    def test_get_installer_url_with_version(
        self, collector_service: CollectorService, mock_client: MagicMock
    ) -> None:
        """Test getting installer URL with specific version."""
        mock_client.get.return_value = {
            "version": "30.003",
            "link": "https://example.com/installer",
        }

        collector_service.get_installer_url("linux64", version="30.003")

        mock_client.get.assert_called_once_with("/setting/collector/installers/linux64/30.003")

    def test_escalate_to_version(
        self, collector_service: CollectorService, mock_client: MagicMock
    ) -> None:
        """Test collector version upgrade."""
        mock_client.patch.return_value = {"id": 1, "build": "31.004"}

        collector_service.escalate_to_version(1, "31.004")

        mock_client.patch.assert_called_once()
        call_args = mock_client.patch.call_args
        data = call_args[1]["json_data"]
        assert data["onetimeUpgradeInfo"]["version"] == "31.004"
        assert data["escalatingChainId"] == 0


class TestCollectorGroupService:
    """Tests for CollectorGroupService."""

    def test_base_path(self, collector_group_service: CollectorGroupService) -> None:
        """Test base_path uses constant."""
        assert collector_group_service.base_path == "/setting/collector/groups"

    def test_get_collectors(
        self, collector_group_service: CollectorGroupService, mock_client: MagicMock
    ) -> None:
        """Test getting collectors in a group."""
        mock_client.get_all.return_value = [{"id": 1}, {"id": 2}]

        result = collector_group_service.get_collectors(5)

        mock_client.get_all.assert_called_once_with("/setting/collector/groups/5/collectors")
        assert len(result) == 2


class TestCollectorStatus:
    """Tests for CollectorStatus enum."""

    def test_values(self) -> None:
        """Test enum values match API."""
        assert CollectorStatus.DOWN.value == 0
        assert CollectorStatus.OK.value == 1
        assert CollectorStatus.WARNING.value == 2

    def test_by_value(self) -> None:
        """Test getting enum by value."""
        assert CollectorStatus(0) == CollectorStatus.DOWN
        assert CollectorStatus(1) == CollectorStatus.OK
        assert CollectorStatus(2) == CollectorStatus.WARNING

    def test_invalid_value(self) -> None:
        """Test invalid status value raises ValueError."""
        with pytest.raises(ValueError):
            CollectorStatus(99)
