"""
Exception hierarchy for lmn-tools.

All exceptions inherit from LMToolsError for unified error handling.
Specific exceptions provide detailed context for debugging.
"""

from __future__ import annotations

from typing import Any


class LMToolsError(Exception):
    """
    Base exception for all lmn-tools errors.

    All custom exceptions inherit from this class, allowing callers
    to catch all lmn-tools errors with a single except clause.

    Attributes:
        message: Human-readable error description
        context: Optional dictionary with additional error context
    """

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        self.message = message
        self.context = context or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.context:
            ctx_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            return f"{self.message} ({ctx_str})"
        return self.message


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(LMToolsError):
    """
    Error in configuration parsing or validation.

    Raised when:
    - YAML/config file is malformed
    - Required fields are missing
    - Field values fail validation
    """

    pass


class ConfigFileNotFoundError(ConfigurationError):
    """Configuration file does not exist."""

    def __init__(self, path: str):
        super().__init__(f"Configuration file not found: {path}", context={"path": path})


class ConfigValidationError(ConfigurationError):
    """
    Configuration validation failed.

    Attributes:
        field: The field that failed validation
        value: The invalid value
        reason: Why validation failed
    """

    def __init__(self, field: str, value: Any, reason: str):
        super().__init__(
            f"Validation failed for '{field}': {reason}",
            context={"field": field, "value": value, "reason": reason},
        )


# =============================================================================
# Authentication Errors
# =============================================================================


class AuthenticationError(LMToolsError):
    """Base class for authentication errors."""

    pass


class InvalidCredentialsError(AuthenticationError):
    """API credentials are invalid or expired."""

    def __init__(self, message: str = "Invalid API credentials"):
        super().__init__(message)


class MissingCredentialsError(AuthenticationError):
    """Required credentials not configured."""

    def __init__(self, missing_fields: list[str] | None = None):
        fields = missing_fields or ["credentials"]
        super().__init__(
            f"Missing required credentials: {', '.join(fields)}",
            context={"missing_fields": fields},
        )


class SignatureError(AuthenticationError):
    """Error generating HMAC signature."""

    pass


# =============================================================================
# API Client Errors
# =============================================================================


class APIError(LMToolsError):
    """
    Base class for API-related errors.

    Attributes:
        status_code: HTTP status code (if applicable)
        response_data: Raw response data from API
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
    ):
        super().__init__(
            message, context={"status_code": status_code, "response_data": response_data}
        )
        self.status_code = status_code
        self.response_data = response_data or {}


class APIConnectionError(APIError):
    """Failed to connect to API endpoint."""

    pass


class APITimeoutError(APIError):
    """API request timed out."""

    pass


class APIRateLimitError(APIError):
    """API rate limit exceeded."""

    def __init__(self, retry_after: int | None = None, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class APINotFoundError(APIError):
    """Requested resource does not exist."""

    def __init__(self, resource_type: str, identifier: str):
        super().__init__(
            f"{resource_type} not found: {identifier}",
            status_code=404,
            response_data={"resource_type": resource_type, "identifier": identifier},
        )
        self.resource_type = resource_type
        self.identifier = identifier


class APIValidationError(APIError):
    """API request validation failed."""

    pass


# =============================================================================
# NETCONF Errors
# =============================================================================


class NetconfError(LMToolsError):
    """Base class for NETCONF-related errors."""

    pass


class NetconfConnectionError(NetconfError):
    """Failed to establish NETCONF connection."""

    def __init__(self, hostname: str, port: int, reason: str):
        super().__init__(
            f"Failed to connect to {hostname}:{port}: {reason}",
            context={"hostname": hostname, "port": port, "reason": reason},
        )
        self.hostname = hostname
        self.port = port
        self.reason = reason


class NetconfAuthenticationError(NetconfError):
    """NETCONF authentication failed."""

    def __init__(self, hostname: str, username: str):
        super().__init__(
            f"Authentication failed for {username}@{hostname}",
            context={"hostname": hostname, "username": username},
        )
        self.hostname = hostname
        self.username = username


class NetconfRPCError(NetconfError):
    """NETCONF RPC operation failed."""

    def __init__(self, operation: str, error_message: str):
        super().__init__(
            f"RPC '{operation}' failed: {error_message}", context={"operation": operation}
        )
        self.operation = operation


class NetconfTimeoutError(NetconfError):
    """NETCONF operation timed out."""

    pass


# =============================================================================
# SNMP Errors
# =============================================================================


class SNMPError(LMToolsError):
    """Base class for SNMP-related errors."""

    pass


class SNMPConnectionError(SNMPError):
    """Failed to connect to device via SNMP."""

    def __init__(self, hostname: str, port: int, reason: str):
        super().__init__(
            f"SNMP connection to {hostname}:{port} failed: {reason}",
            context={"hostname": hostname, "port": port, "reason": reason},
        )
        self.hostname = hostname
        self.port = port
        self.reason = reason


class SNMPTimeoutError(SNMPError):
    """SNMP operation timed out."""

    def __init__(self, hostname: str, oid: str | None = None):
        msg = f"SNMP timeout querying {hostname}"
        if oid:
            msg += f" for OID {oid}"
        super().__init__(msg, context={"hostname": hostname, "oid": oid})
        self.hostname = hostname
        self.oid = oid


class SNMPAuthenticationError(SNMPError):
    """SNMP authentication failed."""

    def __init__(self, hostname: str, message: str = "SNMP authentication failed"):
        super().__init__(f"{message}: {hostname}", context={"hostname": hostname})
        self.hostname = hostname


# =============================================================================
# Data Parsing Errors
# =============================================================================


class ParsingError(LMToolsError):
    """Base class for data parsing errors."""

    pass


class XMLParsingError(ParsingError):
    """Failed to parse XML data."""

    def __init__(self, message: str, xpath: str | None = None):
        super().__init__(message, context={"xpath": xpath})
        self.xpath = xpath


class MetricExtractionError(ParsingError):
    """Failed to extract metric value."""

    def __init__(self, metric_name: str, instance_id: str, reason: str):
        super().__init__(
            f"Failed to extract metric '{metric_name}' for instance '{instance_id}': {reason}",
            context={"metric_name": metric_name, "instance_id": instance_id, "reason": reason},
        )
        self.metric_name = metric_name
        self.instance_id = instance_id
        self.reason = reason


class StringMapError(ParsingError):
    """Error applying string map conversion."""

    def __init__(self, value: str, string_map_name: str):
        super().__init__(
            f"Value '{value}' not found in string map '{string_map_name}'",
            context={"value": value, "string_map": string_map_name},
        )
        self.value = value
        self.string_map_name = string_map_name


# =============================================================================
# Resolution Errors (LogicMonitor resource resolution)
# =============================================================================


class ResolutionError(LMToolsError):
    """Base class for resource resolution errors."""

    pass


class DeviceNotFoundError(ResolutionError):
    """Device not found in LogicMonitor."""

    def __init__(self, hostname: str):
        super().__init__(f"Device not found: {hostname}", context={"hostname": hostname})
        self.hostname = hostname


class DatasourceNotFoundError(ResolutionError):
    """Datasource not found or not applied to device."""

    def __init__(self, datasource_name: str, device_id: int | None = None):
        msg = f"Datasource not found: {datasource_name}"
        if device_id is not None:
            msg += f" (device_id={device_id})"
        super().__init__(msg, context={"datasource_name": datasource_name, "device_id": device_id})
        self.datasource_name = datasource_name
        self.device_id = device_id


class InstanceNotFoundError(ResolutionError):
    """Datasource instance not found."""

    def __init__(self, instance_name: str, device_id: int, datasource_name: str):
        super().__init__(
            f"Instance '{instance_name}' not found for device {device_id} "
            f"datasource '{datasource_name}'",
            context={
                "instance_name": instance_name,
                "device_id": device_id,
                "datasource_name": datasource_name,
            },
        )
        self.instance_name = instance_name
        self.device_id = device_id
        self.datasource_name = datasource_name


# =============================================================================
# Dashboard Errors
# =============================================================================


class DashboardError(LMToolsError):
    """Base class for dashboard-related errors."""

    pass


class DashboardNotFoundError(DashboardError):
    """Dashboard not found."""

    def __init__(self, identifier: str | int):
        super().__init__(f"Dashboard not found: {identifier}", context={"identifier": identifier})
        self.identifier = identifier


class WidgetCreationError(DashboardError):
    """Failed to create dashboard widget."""

    def __init__(self, widget_type: str, reason: str):
        super().__init__(
            f"Failed to create {widget_type} widget: {reason}",
            context={"widget_type": widget_type, "reason": reason},
        )
        self.widget_type = widget_type
        self.reason = reason
