"""
Discovery models for LogicMonitor resource resolution.

These models represent resolved LogicMonitor resource identifiers
needed for dashboards and other operations.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ResolvedInterface(BaseModel):
    """
    Resolved interface with all LogicMonitor identifiers.

    Used when building dashboards or other operations that require
    the full path of LM resource IDs (device -> datasource -> instance).

    Attributes:
        device_id: LogicMonitor device ID
        hostname: Device hostname/displayName
        instance_id: LogicMonitor instance ID (numeric)
        instance_name: Instance display name
        interface_name: Physical interface name
        alias: Interface alias/description
        role: Interface role (e.g., "uplink", "access")
        include_in_traffic_graphs: Whether to show in traffic graphs
        include_in_table: Whether to show in interface tables
        dom: Whether interface has DOM (optical) data
        datasource_id: LogicMonitor datasource ID
        device_datasource_id: Device-specific datasource ID
        datasource_name: Datasource internal name
        datasource_display_name: Datasource display name
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    device_id: int = Field(description="LogicMonitor device ID")
    hostname: str = Field(description="Device hostname")
    instance_id: int = Field(description="LogicMonitor instance ID")
    instance_name: str = Field(description="Instance display name")
    interface_name: str = Field(description="Physical interface name")

    # Optional metadata
    alias: str = Field(default="", description="Interface alias/description")
    role: str = Field(default="", description="Interface role")
    include_in_traffic_graphs: bool = Field(default=True)
    include_in_table: bool = Field(default=True)
    dom: bool = Field(default=False, description="Has DOM/optical data")

    # LogicMonitor datasource identifiers
    datasource_id: int | None = Field(default=None, description="Datasource ID")
    device_datasource_id: int | None = Field(default=None, description="Device datasource ID")
    datasource_name: str | None = Field(default=None, description="Datasource internal name")
    datasource_display_name: str | None = Field(default=None, description="Datasource display name")

    @property
    def full_name(self) -> str:
        """Return hostname:interface_name."""
        return f"{self.hostname}:{self.interface_name}"


class ResolvedBGPPeer(BaseModel):
    """
    Resolved BGP peer with LogicMonitor identifiers.

    Used for BGP-specific dashboard widgets and operations.

    Attributes:
        device_id: LogicMonitor device ID
        hostname: Device hostname
        instance_id: LogicMonitor instance ID
        neighbor_ip: BGP neighbor IP address
        description: Peer description
        datasource_id: LogicMonitor datasource ID
        device_datasource_id: Device-specific datasource ID
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    device_id: int = Field(description="LogicMonitor device ID")
    hostname: str = Field(description="Device hostname")
    instance_id: int = Field(description="LogicMonitor instance ID")
    neighbor_ip: str = Field(description="BGP neighbor IP address")
    description: str = Field(default="", description="Peer description")

    # LogicMonitor datasource identifiers
    datasource_id: int | None = Field(default=None, description="Datasource ID")
    device_datasource_id: int | None = Field(default=None, description="Device datasource ID")

    @property
    def full_name(self) -> str:
        """Return hostname:neighbor_ip."""
        return f"{self.hostname}:{self.neighbor_ip}"


class ResolutionSummary(BaseModel):
    """
    Summary of resource resolution results.

    Tracks what was requested vs what was successfully resolved
    in LogicMonitor. Used to report on resolution success/failure
    when building dashboards.

    Attributes:
        devices_defined: Number of devices in config
        devices_resolved: Number of devices found in LM
        interfaces_defined: Number of interfaces in config
        interfaces_resolved: Number of interfaces resolved
        bgp_peers_defined: Number of BGP peers in config
        bgp_peers_resolved: Number of BGP peers resolved
        unresolved_devices: List of devices not found
        unresolved_interfaces: List of interfaces not found
        unresolved_bgp_peers: List of BGP peers not found
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    # Counts
    devices_defined: int = Field(default=0, ge=0)
    devices_resolved: int = Field(default=0, ge=0)
    interfaces_defined: int = Field(default=0, ge=0)
    interfaces_resolved: int = Field(default=0, ge=0)
    bgp_peers_defined: int = Field(default=0, ge=0)
    bgp_peers_resolved: int = Field(default=0, ge=0)

    # Unresolved items
    unresolved_devices: list[str] = Field(default_factory=list)
    unresolved_interfaces: list[str] = Field(default_factory=list)
    unresolved_bgp_peers: list[str] = Field(default_factory=list)

    @property
    def all_resolved(self) -> bool:
        """Check if all resources were successfully resolved."""
        return not (
            self.unresolved_devices
            or self.unresolved_interfaces
            or self.unresolved_bgp_peers
        )

    @property
    def device_success_rate(self) -> float:
        """Return device resolution success rate (0.0-1.0)."""
        if self.devices_defined == 0:
            return 1.0
        return self.devices_resolved / self.devices_defined

    @property
    def interface_success_rate(self) -> float:
        """Return interface resolution success rate (0.0-1.0)."""
        if self.interfaces_defined == 0:
            return 1.0
        return self.interfaces_resolved / self.interfaces_defined

    @property
    def bgp_success_rate(self) -> float:
        """Return BGP peer resolution success rate (0.0-1.0)."""
        if self.bgp_peers_defined == 0:
            return 1.0
        return self.bgp_peers_resolved / self.bgp_peers_defined

    def add_unresolved_device(self, hostname: str) -> None:
        """Add a device to the unresolved list."""
        if hostname not in self.unresolved_devices:
            self.unresolved_devices.append(hostname)

    def add_unresolved_interface(self, interface: str) -> None:
        """Add an interface to the unresolved list."""
        if interface not in self.unresolved_interfaces:
            self.unresolved_interfaces.append(interface)

    def add_unresolved_bgp_peer(self, peer: str) -> None:
        """Add a BGP peer to the unresolved list."""
        if peer not in self.unresolved_bgp_peers:
            self.unresolved_bgp_peers.append(peer)

    def summary_text(self) -> str:
        """Return human-readable summary."""
        lines = [
            f"Devices: {self.devices_resolved}/{self.devices_defined}",
            f"Interfaces: {self.interfaces_resolved}/{self.interfaces_defined}",
            f"BGP Peers: {self.bgp_peers_resolved}/{self.bgp_peers_defined}",
        ]
        if self.unresolved_devices:
            lines.append(f"Unresolved devices: {', '.join(self.unresolved_devices)}")
        if self.unresolved_interfaces:
            lines.append(f"Unresolved interfaces: {', '.join(self.unresolved_interfaces)}")
        if self.unresolved_bgp_peers:
            lines.append(f"Unresolved BGP peers: {', '.join(self.unresolved_bgp_peers)}")
        return "\n".join(lines)
