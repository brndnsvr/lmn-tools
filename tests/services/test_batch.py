"""
Tests for BatchJobService.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lmn_tools.services.batch import BatchJobService, BatchJobStatus


@pytest.fixture
def service(mock_client: MagicMock) -> BatchJobService:
    """Create BatchJobService with mock client."""
    return BatchJobService(mock_client)


class TestBatchJobService:
    """Tests for BatchJobService."""

    def test_base_path(self, service: BatchJobService) -> None:
        """Test base_path property."""
        assert service.base_path == "/setting/batchjobs"

    def test_get_status(self, service: BatchJobService, mock_client: MagicMock) -> None:
        """Test getting batch job status."""
        mock_client.get.return_value = {
            "status": "running",
            "progress": 50,
            "description": "Test job",
            "createdOn": 1700000000000,
            "successCount": 5,
            "failCount": 1,
            "totalCount": 10,
        }

        result = service.get_status(123)

        mock_client.get.assert_called_once_with("/setting/batchjobs/123")
        assert result["status"] == "running"
        assert result["progress"] == 50
        assert result["id"] == 123

    def test_get_status_with_data_wrapper(self, service: BatchJobService, mock_client: MagicMock) -> None:
        """Test get_status when response has data wrapper."""
        mock_client.get.return_value = {
            "data": {
                "status": "completed",
                "progress": 100,
            }
        }

        result = service.get_status(123)

        assert result["status"] == "completed"

    def test_list_by_status_with_enum(self, service: BatchJobService, mock_client: MagicMock) -> None:
        """Test listing batch jobs by status using enum."""
        mock_client.get_all.return_value = [{"id": 1, "status": "completed"}]

        result = service.list_by_status(BatchJobStatus.COMPLETED)

        call_args = mock_client.get_all.call_args
        assert "status:completed" in call_args[0][1]["filter"]
        assert len(result) == 1

    def test_list_by_status_with_string(self, service: BatchJobService, mock_client: MagicMock) -> None:
        """Test listing batch jobs by status using string."""
        mock_client.get_all.return_value = []

        service.list_by_status("running", max_items=10)

        call_args = mock_client.get_all.call_args
        assert "status:running" in call_args[0][1]["filter"]
        assert call_args[1]["max_items"] == 10

    def test_list_pending(self, service: BatchJobService, mock_client: MagicMock) -> None:
        """Test listing pending batch jobs."""
        mock_client.get_all.return_value = [{"id": 3, "status": "pending"}]

        service.list_pending()

        call_args = mock_client.get_all.call_args
        assert "status:pending" in call_args[0][1]["filter"]

    def test_list_running(self, service: BatchJobService, mock_client: MagicMock) -> None:
        """Test listing running batch jobs."""
        mock_client.get_all.return_value = [{"id": 4, "status": "running"}]

        service.list_running()

        call_args = mock_client.get_all.call_args
        assert "status:running" in call_args[0][1]["filter"]

    def test_list_completed(self, service: BatchJobService, mock_client: MagicMock) -> None:
        """Test listing completed batch jobs."""
        mock_client.get_all.return_value = []

        service.list_completed(max_items=50)

        call_args = mock_client.get_all.call_args
        assert "status:completed" in call_args[0][1]["filter"]
        assert call_args[1]["max_items"] == 50

    def test_list_failed(self, service: BatchJobService, mock_client: MagicMock) -> None:
        """Test listing failed batch jobs."""
        mock_client.get_all.return_value = [{"id": 5, "status": "failed"}]

        service.list_failed()

        call_args = mock_client.get_all.call_args
        assert "status:failed" in call_args[0][1]["filter"]

    def test_cancel(self, service: BatchJobService, mock_client: MagicMock) -> None:
        """Test cancelling a batch job."""
        mock_client.patch.return_value = {"id": 123, "status": "cancelled"}

        service.cancel(123)

        mock_client.patch.assert_called_once_with(
            "/setting/batchjobs/123",
            json_data={"status": "cancelled"},
        )

    def test_wait_for_completion_already_done(self, service: BatchJobService, mock_client: MagicMock) -> None:
        """Test wait_for_completion when job is already done."""
        mock_client.get.return_value = {"status": "completed"}

        result = service.wait_for_completion(123, poll_interval=0.1, timeout=1)

        assert result["status"] == "completed"
        mock_client.get.assert_called_once()

    def test_wait_for_completion_failed(self, service: BatchJobService, mock_client: MagicMock) -> None:
        """Test wait_for_completion when job fails."""
        mock_client.get.return_value = {"status": "failed"}

        result = service.wait_for_completion(123, poll_interval=0.1, timeout=1)

        assert result["status"] == "failed"

    def test_wait_for_completion_cancelled(self, service: BatchJobService, mock_client: MagicMock) -> None:
        """Test wait_for_completion when job is cancelled."""
        mock_client.get.return_value = {"status": "cancelled"}

        result = service.wait_for_completion(123, poll_interval=0.1, timeout=1)

        assert result["status"] == "cancelled"


class TestBatchJobStatus:
    """Tests for BatchJobStatus enum."""

    def test_values(self) -> None:
        """Test enum values."""
        assert BatchJobStatus.PENDING.value == "pending"
        assert BatchJobStatus.RUNNING.value == "running"
        assert BatchJobStatus.COMPLETED.value == "completed"
        assert BatchJobStatus.FAILED.value == "failed"
        assert BatchJobStatus.CANCELLED.value == "cancelled"
