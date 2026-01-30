"""
Tests for AccessGroupService.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lmn_tools.services.access import AccessGroupService


@pytest.fixture
def service(mock_client: MagicMock) -> AccessGroupService:
    """Create AccessGroupService with mock client."""
    return AccessGroupService(mock_client)


class TestAccessGroupService:
    """Tests for AccessGroupService."""

    def test_base_path(self, service: AccessGroupService) -> None:
        """Test base_path property."""
        assert service.base_path == "/setting/accessgroup"

    def test_search(self, service: AccessGroupService, mock_client: MagicMock) -> None:
        """Test searching access groups by name."""
        mock_client.get_all.return_value = [{"id": 1, "name": "TestGroup"}]

        result = service.search("Test")

        mock_client.get_all.assert_called_once()
        call_args = mock_client.get_all.call_args
        assert 'name~"Test"' in call_args[0][1]["filter"]
        assert len(result) == 1

    def test_get_device_groups(self, service: AccessGroupService, mock_client: MagicMock) -> None:
        """Test getting device groups for an access group."""
        mock_client.get.return_value = {
            "deviceGroups": [
                {"id": 1, "permission": "read"},
                {"id": 2, "permission": "write"},
            ]
        }

        result = service.get_device_groups(123)

        mock_client.get.assert_called_once_with("/setting/accessgroup/123")
        assert len(result) == 2
        assert result[0]["permission"] == "read"

    def test_get_device_groups_with_data_wrapper(self, service: AccessGroupService, mock_client: MagicMock) -> None:
        """Test getting device groups when response has data wrapper."""
        mock_client.get.return_value = {
            "data": {
                "deviceGroups": [{"id": 1, "permission": "manage"}]
            }
        }

        result = service.get_device_groups(123)

        assert len(result) == 1
        assert result[0]["permission"] == "manage"

    def test_get_device_groups_empty(self, service: AccessGroupService, mock_client: MagicMock) -> None:
        """Test getting device groups when none exist."""
        mock_client.get.return_value = {"deviceGroups": []}

        result = service.get_device_groups(123)

        assert result == []

    def test_add_device_group(self, service: AccessGroupService, mock_client: MagicMock) -> None:
        """Test adding a device group to an access group."""
        mock_client.get.return_value = {
            "id": 123,
            "name": "TestGroup",
            "deviceGroups": [{"id": 1, "permission": "read"}],
        }
        mock_client.patch.return_value = {"id": 123}

        service.add_device_group(123, 2, "write")

        mock_client.patch.assert_called_once()
        call_args = mock_client.patch.call_args
        data = call_args[1]["json_data"]
        assert len(data["deviceGroups"]) == 2
        assert {"id": 2, "permission": "write"} in data["deviceGroups"]

    def test_add_device_group_default_permission(self, service: AccessGroupService, mock_client: MagicMock) -> None:
        """Test adding a device group with default read permission."""
        mock_client.get.return_value = {"id": 123, "deviceGroups": []}
        mock_client.patch.return_value = {"id": 123}

        service.add_device_group(123, 2)

        call_args = mock_client.patch.call_args
        data = call_args[1]["json_data"]
        assert data["deviceGroups"][0]["permission"] == "read"

    def test_create_simple(self, service: AccessGroupService, mock_client: MagicMock) -> None:
        """Test creating an access group with simple parameters."""
        mock_client.post.return_value = {"id": 456, "name": "NewGroup"}

        service.create_simple("NewGroup", "Description", [1, 2, 3])

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        data = call_args[1]["json_data"]
        assert data["name"] == "NewGroup"
        assert data["description"] == "Description"
        assert len(data["deviceGroups"]) == 3
        assert all(dg["permission"] == "read" for dg in data["deviceGroups"])

    def test_create_simple_no_device_groups(self, service: AccessGroupService, mock_client: MagicMock) -> None:
        """Test creating an access group without device groups."""
        mock_client.post.return_value = {"id": 457}

        service.create_simple("MinimalGroup")

        call_args = mock_client.post.call_args
        data = call_args[1]["json_data"]
        assert "deviceGroups" not in data
