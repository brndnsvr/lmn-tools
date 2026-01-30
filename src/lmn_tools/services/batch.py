"""
Service for LogicMonitor Batch Jobs.

Provides operations for managing asynchronous bulk operations.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from lmn_tools.api.client import LMClient
from lmn_tools.services.base import BaseService


class BatchJobStatus(str, Enum):
    """Batch job status values."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchJobService(BaseService):
    """
    Service for managing LogicMonitor Batch Jobs.

    Batch jobs are used for asynchronous bulk operations like
    device imports, property updates, etc.

    Usage:
        svc = BatchJobService(client)
        jobs = svc.list()
        status = svc.get_status(job_id)
    """

    @property
    def base_path(self) -> str:
        return "/setting/batchjobs"

    def list_by_status(
        self,
        status: BatchJobStatus | str,
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        List batch jobs by status.

        Args:
            status: Job status to filter by
            max_items: Maximum items to return

        Returns:
            List of batch jobs
        """
        status_value = status.value if isinstance(status, BatchJobStatus) else status
        return self.list(filter=f"status:{status_value}", max_items=max_items)

    def list_running(self, max_items: int | None = None) -> list[dict[str, Any]]:
        """List running batch jobs."""
        return self.list_by_status(BatchJobStatus.RUNNING, max_items)

    def list_pending(self, max_items: int | None = None) -> list[dict[str, Any]]:
        """List pending batch jobs."""
        return self.list_by_status(BatchJobStatus.PENDING, max_items)

    def list_completed(self, max_items: int | None = None) -> list[dict[str, Any]]:
        """List completed batch jobs."""
        return self.list_by_status(BatchJobStatus.COMPLETED, max_items)

    def list_failed(self, max_items: int | None = None) -> list[dict[str, Any]]:
        """List failed batch jobs."""
        return self.list_by_status(BatchJobStatus.FAILED, max_items)

    def get_status(self, job_id: int) -> dict[str, Any]:
        """
        Get the status of a batch job.

        Args:
            job_id: Batch job ID

        Returns:
            Status information including progress
        """
        job = self.get(job_id)
        data = job.get("data", job) if "data" in job else job
        return {
            "id": job_id,
            "status": data.get("status"),
            "description": data.get("description"),
            "createdOn": data.get("createdOn"),
            "completedOn": data.get("completedOn"),
            "progress": data.get("progress"),
            "successCount": data.get("successCount"),
            "failCount": data.get("failCount"),
            "totalCount": data.get("totalCount"),
        }

    def cancel(self, job_id: int) -> dict[str, Any]:
        """
        Cancel a running or pending batch job.

        Args:
            job_id: Batch job ID

        Returns:
            Updated job status
        """
        return self.update(job_id, {"status": "cancelled"})

    def wait_for_completion(
        self,
        job_id: int,
        poll_interval: float = 5.0,
        timeout: float = 300.0,
    ) -> dict[str, Any]:
        """
        Wait for a batch job to complete.

        Args:
            job_id: Batch job ID
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait

        Returns:
            Final job status

        Raises:
            TimeoutError: If job doesn't complete within timeout
        """
        import time

        start_time = time.time()
        while True:
            status = self.get_status(job_id)
            job_status = status.get("status", "").lower()

            if job_status in ("completed", "failed", "cancelled"):
                return status

            elapsed = time.time() - start_time
            if elapsed >= timeout:
                raise TimeoutError(f"Batch job {job_id} did not complete within {timeout}s")

            time.sleep(poll_interval)


def batchjob_service(client: LMClient) -> BatchJobService:
    """Create a batch job service."""
    return BatchJobService(client)
