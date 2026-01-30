"""
Tests for AuditLogService.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from lmn_tools.services.audit import AuditLogService


@pytest.fixture
def service(mock_client: MagicMock) -> AuditLogService:
    """Create AuditLogService with mock client."""
    return AuditLogService(mock_client)


class TestAuditLogService:
    """Tests for AuditLogService."""

    def test_base_path(self, service: AuditLogService) -> None:
        """Test base_path property."""
        assert service.base_path == "/setting/accesslogs"

    def test_list_by_user(self, service: AuditLogService, mock_client: MagicMock) -> None:
        """Test listing audit logs by user."""
        mock_client.get_all.return_value = [
            {"id": 1, "username": "admin", "description": "Login"},
        ]

        result = service.list_by_user("admin")

        mock_client.get_all.assert_called_once()
        call_args = mock_client.get_all.call_args
        assert 'username:"admin"' in call_args[0][1]["filter"]
        assert len(result) == 1

    def test_list_by_user_with_max_items(self, service: AuditLogService, mock_client: MagicMock) -> None:
        """Test list_by_user with max_items limit."""
        mock_client.get_all.return_value = []

        service.list_by_user("admin", max_items=100)

        call_args = mock_client.get_all.call_args
        assert call_args[1]["max_items"] == 100

    def test_list_by_action(self, service: AuditLogService, mock_client: MagicMock) -> None:
        """Test listing audit logs by action."""
        mock_client.get_all.return_value = [
            {"id": 2, "description": "delete"},
        ]

        service.list_by_action("delete")

        call_args = mock_client.get_all.call_args
        assert 'description~"delete"' in call_args[0][1]["filter"]

    def test_list_by_resource(self, service: AuditLogService, mock_client: MagicMock) -> None:
        """Test listing audit logs by resource type."""
        mock_client.get_all.return_value = []

        service.list_by_resource("device")

        call_args = mock_client.get_all.call_args
        assert 'description~"device"' in call_args[0][1]["filter"]

    @patch("lmn_tools.services.audit.time.time")
    def test_list_by_time_range(self, mock_time: MagicMock, service: AuditLogService, mock_client: MagicMock) -> None:
        """Test listing audit logs by time range."""
        mock_time.return_value = 1700100000
        mock_client.get_all.return_value = [{"id": 3}]

        service.list_by_time_range(
            start_time=1700000000,
            end_time=1700100000000,
        )

        call_args = mock_client.get_all.call_args
        filter_str = call_args[0][1]["filter"]
        assert "happenedOn>1700000000" in filter_str
        assert "happenedOn<1700100000000" in filter_str

    @patch("lmn_tools.services.audit.time.time")
    def test_list_by_time_range_end_time_default(
        self, mock_time: MagicMock, service: AuditLogService, mock_client: MagicMock
    ) -> None:
        """Test list_by_time_range defaults end_time to now."""
        mock_time.return_value = 1700100000
        mock_client.get_all.return_value = []

        service.list_by_time_range(start_time=1700000000)

        call_args = mock_client.get_all.call_args
        filter_str = call_args[0][1]["filter"]
        assert "happenedOn>1700000000" in filter_str
        assert "happenedOn<1700100000000" in filter_str  # time.time() * 1000

    @patch("lmn_tools.services.audit.time.time")
    def test_list_recent(self, mock_time: MagicMock, service: AuditLogService, mock_client: MagicMock) -> None:
        """Test listing recent audit logs."""
        mock_time.return_value = 1700000000
        mock_client.get_all.return_value = [{"id": 1}, {"id": 2}]

        service.list_recent(hours=24, max_items=50)

        # 24 hours ago: 1700000000000 - (24 * 60 * 60 * 1000) = 1699913600000
        call_args = mock_client.get_all.call_args
        filter_str = call_args[0][1]["filter"]
        assert "happenedOn>1699913600000" in filter_str
        assert call_args[1]["max_items"] == 50

    def test_list_logins(self, service: AuditLogService, mock_client: MagicMock) -> None:
        """Test listing login events."""
        mock_client.get_all.return_value = [{"id": 1, "description": "login"}]

        service.list_logins()

        call_args = mock_client.get_all.call_args
        assert 'description~"login"' in call_args[0][1]["filter"]

    def test_list_failed_logins(self, service: AuditLogService, mock_client: MagicMock) -> None:
        """Test listing failed login attempts."""
        mock_client.get_all.return_value = []

        service.list_failed_logins(max_items=50)

        call_args = mock_client.get_all.call_args
        assert 'description~"failed login"' in call_args[0][1]["filter"]
        assert call_args[1]["max_items"] == 50
