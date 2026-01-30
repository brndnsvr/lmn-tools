"""
Tests for TopologyService.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lmn_tools.services.topology import TopologyService


@pytest.fixture
def service(mock_client: MagicMock) -> TopologyService:
    """Create TopologyService with mock client."""
    return TopologyService(mock_client)


class TestTopologyService:
    """Tests for TopologyService."""

    def test_base_path(self, service: TopologyService) -> None:
        """Test base_path property."""
        assert service.base_path == "/topology/topologies"

    def test_search(self, service: TopologyService, mock_client: MagicMock) -> None:
        """Test searching topology maps by name."""
        mock_client.get_all.return_value = [{"id": 1, "name": "TestMap"}]

        result = service.search("Test")

        mock_client.get_all.assert_called_once()
        call_args = mock_client.get_all.call_args
        assert 'name~"Test"' in call_args[0][1]["filter"]
        assert len(result) == 1

    def test_get_map_data(self, service: TopologyService, mock_client: MagicMock) -> None:
        """Test getting topology map data."""
        mock_client.get.return_value = {
            "vertices": [{"id": 1, "type": "device"}],
            "edges": [{"from": 1, "to": 2}],
        }

        result = service.get_map_data(123)

        mock_client.get.assert_called_once_with("/topology/topologies/123/data")
        assert len(result["vertices"]) == 1
        assert len(result["edges"]) == 1

    def test_export_map(self, service: TopologyService, mock_client: MagicMock) -> None:
        """Test exporting a complete topology map."""
        mock_client.get.side_effect = [
            # First call: get map config
            {"id": 123, "name": "TestMap", "type": "manual", "description": "Test"},
            # Second call: get map data
            {
                "vertices": [{"id": 10, "type": "device"}],
                "edges": [{"from": 10, "to": 20}],
            },
        ]

        result = service.export_map(123)

        assert result["config"]["id"] == 123
        assert result["config"]["name"] == "TestMap"
        assert "data" in result
        assert len(result["data"]["vertices"]) == 1
        assert len(result["data"]["edges"]) == 1

    def test_export_map_with_data_wrapper(self, service: TopologyService, mock_client: MagicMock) -> None:
        """Test export_map when responses have data wrappers."""
        mock_client.get.side_effect = [
            {"data": {"id": 123, "name": "WrappedMap"}},
            {"data": {"vertices": [], "edges": []}},
        ]

        result = service.export_map(123)

        assert result["config"]["name"] == "WrappedMap"

    def test_create_from_devices(self, service: TopologyService, mock_client: MagicMock) -> None:
        """Test creating a topology map from devices."""
        mock_client.post.return_value = {"id": 456, "name": "NewMap"}

        service.create_from_devices(
            name="NewMap",
            device_ids=[10, 20, 30],
            description="Test description",
        )

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        data = call_args[1]["json_data"]
        assert data["name"] == "NewMap"
        assert data["type"] == "manual"
        assert data["description"] == "Test description"
        assert len(data["vertices"]) == 3
        assert data["vertices"][0] == {"type": "device", "id": 10}

    def test_create_from_devices_no_description(self, service: TopologyService, mock_client: MagicMock) -> None:
        """Test creating a map without description."""
        mock_client.post.return_value = {"id": 457}

        service.create_from_devices("MinimalMap", [10])

        call_args = mock_client.post.call_args
        data = call_args[1]["json_data"]
        assert data["description"] == ""

    def test_add_device(self, service: TopologyService, mock_client: MagicMock) -> None:
        """Test adding a device to a topology map."""
        mock_client.get.return_value = {
            "vertices": [{"type": "device", "id": 10}],
        }
        mock_client.patch.return_value = {"vertices": [{"id": 10}, {"id": 20}]}

        service.add_device(123, 20)

        mock_client.patch.assert_called_once()
        call_args = mock_client.patch.call_args
        assert call_args[0][0] == "/topology/topologies/123"
        data = call_args[1]["json_data"]
        assert len(data["vertices"]) == 2
        assert {"type": "device", "id": 20} in data["vertices"]

    def test_add_device_to_empty_map(self, service: TopologyService, mock_client: MagicMock) -> None:
        """Test adding a device to an empty topology map."""
        mock_client.get.return_value = {"vertices": []}
        mock_client.patch.return_value = {"vertices": [{"id": 20}]}

        service.add_device(123, 20)

        call_args = mock_client.patch.call_args
        data = call_args[1]["json_data"]
        assert len(data["vertices"]) == 1

    def test_add_device_with_data_wrapper(self, service: TopologyService, mock_client: MagicMock) -> None:
        """Test add_device when response has data wrapper."""
        mock_client.get.return_value = {
            "data": {
                "vertices": [{"type": "device", "id": 10}]
            }
        }
        mock_client.patch.return_value = {}

        service.add_device(123, 20)

        call_args = mock_client.patch.call_args
        data = call_args[1]["json_data"]
        assert len(data["vertices"]) == 2
