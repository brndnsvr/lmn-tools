"""
Tests for OpsNoteService.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lmn_tools.services.operations import OpsNoteService


@pytest.fixture
def service(mock_client: MagicMock) -> OpsNoteService:
    """Create OpsNoteService with mock client."""
    return OpsNoteService(mock_client)


class TestOpsNoteService:
    """Tests for OpsNoteService."""

    def test_base_path(self, service: OpsNoteService) -> None:
        """Test base_path property."""
        assert service.base_path == "/setting/opsnotes"

    def test_list_by_resource(self, service: OpsNoteService, mock_client: MagicMock) -> None:
        """Test listing notes by resource."""
        mock_client.get_all.return_value = [{"id": 1, "note": "test"}]

        result = service.list_by_resource("device", 123)

        mock_client.get_all.assert_called_once()
        call_args = mock_client.get_all.call_args
        filter_str = call_args[0][1]["filter"]
        assert 'scopes.type:"device"' in filter_str
        assert "scopes.id:123" in filter_str
        assert len(result) == 1

    def test_list_by_resource_with_max_items(
        self, service: OpsNoteService, mock_client: MagicMock
    ) -> None:
        """Test list_by_resource with max_items limit."""
        mock_client.get_all.return_value = [{"id": 1}]

        service.list_by_resource("device", 123, max_items=10)

        call_args = mock_client.get_all.call_args
        assert call_args[1]["max_items"] == 10

    def test_list_by_device(self, service: OpsNoteService, mock_client: MagicMock) -> None:
        """Test listing notes for a device."""
        mock_client.get_all.return_value = [{"id": 1}]

        service.list_by_device(123)

        call_args = mock_client.get_all.call_args
        filter_str = call_args[0][1]["filter"]
        assert 'scopes.type:"device"' in filter_str
        assert "scopes.id:123" in filter_str

    def test_list_by_group(self, service: OpsNoteService, mock_client: MagicMock) -> None:
        """Test listing notes for a device group."""
        mock_client.get_all.return_value = []

        service.list_by_group(456)

        call_args = mock_client.get_all.call_args
        filter_str = call_args[0][1]["filter"]
        assert 'scopes.type:"deviceGroup"' in filter_str
        assert "scopes.id:456" in filter_str

    def test_list_by_tag(self, service: OpsNoteService, mock_client: MagicMock) -> None:
        """Test listing notes by tag."""
        mock_client.get_all.return_value = [{"id": 1, "tags": [{"name": "incident"}]}]

        result = service.list_by_tag("incident")

        call_args = mock_client.get_all.call_args
        assert 'tags~"incident"' in call_args[0][1]["filter"]
        assert len(result) == 1

    def test_create_device_note(self, service: OpsNoteService, mock_client: MagicMock) -> None:
        """Test creating a note for a device."""
        mock_client.post.return_value = {"id": 1, "note": "test note"}

        result = service.create_device_note(123, "test note", ["tag1", "tag2"])

        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        data = call_args[1]["json_data"]
        assert data["note"] == "test note"
        assert data["tags"] == [{"name": "tag1"}, {"name": "tag2"}]
        assert data["scopes"] == [{"type": "device", "id": 123}]
        assert result["id"] == 1

    def test_create_device_note_no_tags(
        self, service: OpsNoteService, mock_client: MagicMock
    ) -> None:
        """Test creating a device note without tags."""
        mock_client.post.return_value = {"id": 1, "note": "test"}

        service.create_device_note(123, "test")

        call_args = mock_client.post.call_args
        data = call_args[1]["json_data"]
        assert "tags" not in data

    def test_create_group_note(self, service: OpsNoteService, mock_client: MagicMock) -> None:
        """Test creating a note for a device group."""
        mock_client.post.return_value = {"id": 2, "note": "group note"}

        result = service.create_group_note(456, "group note", ["maintenance"])

        call_args = mock_client.post.call_args
        data = call_args[1]["json_data"]
        assert data["scopes"] == [{"type": "deviceGroup", "id": 456}]
        assert data["tags"] == [{"name": "maintenance"}]
        assert result["id"] == 2

    def test_add_tag(self, service: OpsNoteService, mock_client: MagicMock) -> None:
        """Test adding a tag to a note."""
        mock_client.get.return_value = {
            "id": 1,
            "note": "test",
            "tags": [{"name": "existing"}],
        }
        mock_client.patch.return_value = {"id": 1}

        service.add_tag(1, "new_tag")

        mock_client.patch.assert_called_once()
        call_args = mock_client.patch.call_args
        data = call_args[1]["json_data"]
        assert len(data["tags"]) == 2
        assert {"name": "new_tag"} in data["tags"]

    def test_add_tag_with_data_wrapper(
        self, service: OpsNoteService, mock_client: MagicMock
    ) -> None:
        """Test add_tag when response has data wrapper."""
        mock_client.get.return_value = {"data": {"tags": []}}
        mock_client.patch.return_value = {"id": 1}

        service.add_tag(1, "first_tag")

        call_args = mock_client.patch.call_args
        data = call_args[1]["json_data"]
        assert data["tags"] == [{"name": "first_tag"}]
