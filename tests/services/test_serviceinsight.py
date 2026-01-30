"""
Tests for ServiceService and ServiceGroupService.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lmn_tools.services.serviceinsight import ServiceGroupService, ServiceService


@pytest.fixture
def service(mock_client: MagicMock) -> ServiceService:
    """Create ServiceService with mock client."""
    return ServiceService(mock_client)


@pytest.fixture
def group_service(mock_client: MagicMock) -> ServiceGroupService:
    """Create ServiceGroupService with mock client."""
    return ServiceGroupService(mock_client)


class TestServiceService:
    """Tests for ServiceService."""

    def test_base_path(self, service: ServiceService) -> None:
        """Test base_path property."""
        assert service.base_path == "/service/services"

    def test_search(self, service: ServiceService, mock_client: MagicMock) -> None:
        """Test searching services by name."""
        mock_client.get_all.return_value = [{"id": 1, "name": "WebApp"}]

        result = service.search("Web")

        mock_client.get_all.assert_called_once()
        call_args = mock_client.get_all.call_args
        assert 'name~"Web"' in call_args[0][1]["filter"]
        assert len(result) == 1

    def test_list_by_group(self, service: ServiceService, mock_client: MagicMock) -> None:
        """Test listing services by group."""
        mock_client.get_all.return_value = [
            {"id": 1, "name": "Service1", "groupId": 10},
            {"id": 2, "name": "Service2", "groupId": 10},
        ]

        result = service.list_by_group(10)

        call_args = mock_client.get_all.call_args
        assert "groupId:10" in call_args[0][1]["filter"]
        assert len(result) == 2

    def test_list_by_group_with_max_items(self, service: ServiceService, mock_client: MagicMock) -> None:
        """Test list_by_group with max_items."""
        mock_client.get_all.return_value = []

        service.list_by_group(10, max_items=25)

        call_args = mock_client.get_all.call_args
        assert call_args[1]["max_items"] == 25

    def test_get_status(self, service: ServiceService, mock_client: MagicMock) -> None:
        """Test getting service status."""
        mock_client.get.return_value = {
            "name": "WebApp",
            "status": "normal",
            "alertStatus": 0,
            "sdtStatus": "none",
            "alertDisableStatus": "none",
        }

        result = service.get_status(123)

        mock_client.get.assert_called_once_with("/service/services/123")
        assert result["id"] == 123
        assert result["name"] == "WebApp"
        assert result["alertStatus"] == 0
        assert result["sdtStatus"] == "none"

    def test_get_status_with_data_wrapper(self, service: ServiceService, mock_client: MagicMock) -> None:
        """Test get_status when response has data wrapper."""
        mock_client.get.return_value = {
            "data": {
                "name": "WrappedService",
                "alertStatus": 1,
            }
        }

        result = service.get_status(123)

        assert result["name"] == "WrappedService"
        assert result["alertStatus"] == 1

    def test_get_members(self, service: ServiceService, mock_client: MagicMock) -> None:
        """Test getting service members."""
        mock_client.get.return_value = {
            "id": 123,
            "name": "WebApp",
            "members": [
                {"type": "device", "id": 10},
                {"type": "device", "id": 20},
            ],
        }

        result = service.get_members(123)

        assert len(result) == 2
        assert result[0]["type"] == "device"

    def test_get_members_empty(self, service: ServiceService, mock_client: MagicMock) -> None:
        """Test getting members when service has none."""
        mock_client.get.return_value = {"id": 123, "name": "Empty", "members": []}

        result = service.get_members(123)

        assert result == []

    def test_get_members_with_data_wrapper(self, service: ServiceService, mock_client: MagicMock) -> None:
        """Test get_members when response has data wrapper."""
        mock_client.get.return_value = {
            "data": {
                "members": [{"type": "device", "id": 30}]
            }
        }

        result = service.get_members(123)

        assert len(result) == 1
        assert result[0]["id"] == 30

    def test_create_simple(self, service: ServiceService, mock_client: MagicMock) -> None:
        """Test creating a service with simple parameters."""
        mock_client.post.return_value = {"id": 456, "name": "NewService"}

        service.create_simple(
            name="NewService",
            group_id=10,
            description="Test service",
            device_ids=[1, 2, 3],
        )

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        data = call_args[1]["json_data"]
        assert data["name"] == "NewService"
        assert data["groupId"] == 10
        assert data["description"] == "Test service"
        assert len(data["members"]) == 3
        assert data["members"][0] == {"type": "device", "id": 1}

    def test_create_simple_no_devices(self, service: ServiceService, mock_client: MagicMock) -> None:
        """Test creating a service without devices."""
        mock_client.post.return_value = {"id": 457}

        service.create_simple("MinimalService")

        call_args = mock_client.post.call_args
        data = call_args[1]["json_data"]
        assert "members" not in data
        assert data["groupId"] == 1  # default

    def test_add_device(self, service: ServiceService, mock_client: MagicMock) -> None:
        """Test adding a device to a service."""
        mock_client.get.return_value = {
            "id": 123,
            "name": "WebApp",
            "members": [{"type": "device", "id": 10}],
        }
        mock_client.patch.return_value = {"id": 123}

        service.add_device(123, 20)

        mock_client.patch.assert_called_once()
        call_args = mock_client.patch.call_args
        data = call_args[1]["json_data"]
        assert len(data["members"]) == 2
        assert {"type": "device", "id": 20} in data["members"]

    def test_add_device_to_empty_service(self, service: ServiceService, mock_client: MagicMock) -> None:
        """Test adding a device to a service with no members."""
        mock_client.get.return_value = {"id": 123, "members": []}
        mock_client.patch.return_value = {"id": 123}

        service.add_device(123, 20)

        call_args = mock_client.patch.call_args
        data = call_args[1]["json_data"]
        assert len(data["members"]) == 1
        assert data["members"][0]["id"] == 20


class TestServiceGroupService:
    """Tests for ServiceGroupService."""

    def test_base_path(self, group_service: ServiceGroupService) -> None:
        """Test base_path property."""
        assert group_service.base_path == "/service/groups"

    def test_get_children(self, group_service: ServiceGroupService, mock_client: MagicMock) -> None:
        """Test getting child groups."""
        mock_client.get_all.return_value = [
            {"id": 11, "name": "Child1", "parentId": 10},
            {"id": 12, "name": "Child2", "parentId": 10},
        ]

        result = group_service.get_children(10)

        call_args = mock_client.get_all.call_args
        assert "parentId:10" in call_args[0][1]["filter"]
        assert len(result) == 2

    def test_get_services(self, group_service: ServiceGroupService, mock_client: MagicMock) -> None:
        """Test getting services in a group."""
        mock_client.get_all.return_value = [
            {"id": 1, "name": "Service1", "groupId": 10},
        ]

        result = group_service.get_services(10)

        # This calls list on /service/services with filter
        mock_client.get_all.assert_called_once()
        call_args = mock_client.get_all.call_args
        assert call_args[0][0] == "/service/services"
        assert "groupId:10" in call_args[0][1]["filter"]
        assert len(result) == 1
