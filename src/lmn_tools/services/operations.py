"""
Service for LogicMonitor OpsNotes.

Provides operations for managing operational notes attached to resources.
"""

from __future__ import annotations

from typing import Any

from lmn_tools.api.client import LMClient
from lmn_tools.services.base import BaseService


class OpsNoteService(BaseService):
    """
    Service for managing LogicMonitor OpsNotes.

    OpsNotes are operational annotations that can be attached to various
    resources (devices, groups, websites) to track events, maintenance,
    or other operational information.

    Usage:
        svc = OpsNoteService(client)
        notes = svc.list()
        note = svc.create({"note": "Planned maintenance", "scopes": [...]})
    """

    @property
    def base_path(self) -> str:
        return "/setting/opsnotes"

    def list_by_resource(
        self,
        resource_type: str,
        resource_id: int,
        max_items: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        List OpsNotes for a specific resource.

        Args:
            resource_type: Type of resource (device, deviceGroup, website)
            resource_id: Resource ID

        Returns:
            List of OpsNotes
        """
        filter_str = f'scopes.type:"{resource_type}",scopes.id:{resource_id}'
        return self.list(filter=filter_str, max_items=max_items)

    def list_by_device(self, device_id: int, max_items: int | None = None) -> list[dict[str, Any]]:
        """List OpsNotes for a device."""
        return self.list_by_resource("device", device_id, max_items)

    def list_by_group(self, group_id: int, max_items: int | None = None) -> list[dict[str, Any]]:
        """List OpsNotes for a device group."""
        return self.list_by_resource("deviceGroup", group_id, max_items)

    def list_by_tag(self, tag: str, max_items: int | None = None) -> list[dict[str, Any]]:
        """
        List OpsNotes with a specific tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of matching OpsNotes
        """
        return self.list(filter=f'tags~"{tag}"', max_items=max_items)

    def create_device_note(
        self,
        device_id: int,
        note: str,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create an OpsNote for a device.

        Args:
            device_id: Device ID
            note: Note text
            tags: Optional list of tags

        Returns:
            Created OpsNote
        """
        data: dict[str, Any] = {
            "note": note,
            "scopes": [{"type": "device", "id": device_id}],
        }
        if tags:
            data["tags"] = [{"name": t} for t in tags]
        return self.create(data)

    def create_group_note(
        self,
        group_id: int,
        note: str,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create an OpsNote for a device group.

        Args:
            group_id: Device group ID
            note: Note text
            tags: Optional list of tags

        Returns:
            Created OpsNote
        """
        data: dict[str, Any] = {
            "note": note,
            "scopes": [{"type": "deviceGroup", "id": group_id}],
        }
        if tags:
            data["tags"] = [{"name": t} for t in tags]
        return self.create(data)

    def add_tag(self, note_id: int, tag: str) -> dict[str, Any]:
        """
        Add a tag to an OpsNote.

        Args:
            note_id: OpsNote ID
            tag: Tag to add

        Returns:
            Updated OpsNote
        """
        note = self.get(note_id)
        data = note.get("data", note) if "data" in note else note
        tags = data.get("tags", [])
        tags.append({"name": tag})
        return self.update(note_id, {"tags": tags})


def opsnote_service(client: LMClient) -> OpsNoteService:
    """Create an OpsNote service."""
    return OpsNoteService(client)
