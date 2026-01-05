"""
Output formatter for LogicMonitor scripts.

Provides formatters for Active Discovery and Collection output
in various formats (BATCHSCRIPT, JSON, table).
"""

from __future__ import annotations

import json
import sys
from typing import TextIO

from lmn_tools.models.discovery import DiscoveredInstance
from lmn_tools.models.metrics import MetricCollection, MetricValue


class OutputFormatter:
    """
    Formatter for LogicMonitor script output.

    Handles formatting of discovery instances and collected metrics
    for output to stdout in various formats.

    Attributes:
        output: Output stream (defaults to stdout)
        use_json: Output in JSON format
        debug: Enable debug output
    """

    def __init__(
        self,
        output: TextIO | None = None,
        use_json: bool = False,
        debug: bool = False,
    ):
        """
        Initialize output formatter.

        Args:
            output: Output stream (defaults to stdout)
            use_json: Output in JSON format
            debug: Enable debug output
        """
        self.output = output or sys.stdout
        self.use_json = use_json
        self.debug = debug

    def _write(self, text: str) -> None:
        """Write text to output stream."""
        self.output.write(text)
        if text and not text.endswith("\n"):
            self.output.write("\n")
        self.output.flush()

    def _debug_print(self, message: str) -> None:
        """Print debug message to stderr."""
        if self.debug:
            print(f"DEBUG [OutputFormatter]: {message}", file=sys.stderr)

    def _error_print(self, message: str) -> None:
        """Print error message to stderr."""
        print(f"ERROR: {message}", file=sys.stderr)

    # =========================================================================
    # Discovery Output
    # =========================================================================

    def format_discovery(self, instances: list[DiscoveredInstance]) -> str:
        """
        Format instances for LogicMonitor Active Discovery.

        Args:
            instances: List of discovered instances

        Returns:
            Formatted discovery output string
        """
        return "\n".join(inst.to_discovery_line() for inst in instances)

    def format_discovery_json(self, instances: list[DiscoveredInstance]) -> str:
        """
        Format instances as JSON.

        Args:
            instances: List of discovered instances

        Returns:
            JSON string
        """
        data = [
            {
                "instance_id": inst.instance_id,
                "instance_name": inst.instance_name,
                "description": inst.description,
                "properties": inst.properties,
            }
            for inst in instances
        ]
        return json.dumps(data, indent=2)

    def write_discovery(self, instances: list[DiscoveredInstance]) -> None:
        """
        Write discovery output to stream.

        Args:
            instances: List of discovered instances
        """
        self._debug_print(f"Writing {len(instances)} instances")

        if self.use_json:
            output_str = self.format_discovery_json(instances)
        else:
            output_str = self.format_discovery(instances)

        self._write(output_str)

    # =========================================================================
    # Collection Output
    # =========================================================================

    def format_collection_line(self, metrics: list[MetricValue]) -> str:
        """
        Format metrics for LogicMonitor BATCHSCRIPT output.

        Output format: instance_id.datapoint_name=value

        Args:
            metrics: List of metric values

        Returns:
            Formatted collection output string
        """
        lines = []
        for m in metrics:
            if m.value is not None:
                line = m.to_collection_line()
                if line:
                    lines.append(line)
        return "\n".join(lines)

    def format_collection_json(self, metrics: list[MetricValue]) -> str:
        """
        Format metrics as JSON for LogicMonitor.

        Output format:
        {
            "data": {
                "instance_id": {
                    "values": {"metric1": value1, "metric2": value2}
                }
            }
        }

        Args:
            metrics: List of metric values

        Returns:
            JSON string
        """
        collection = MetricCollection(metrics=metrics)
        return json.dumps(collection.to_json_output(), indent=2)

    def write_collection(self, metrics: list[MetricValue]) -> None:
        """
        Write collection output to stream.

        Args:
            metrics: List of metric values
        """
        self._debug_print(f"Writing {len(metrics)} metrics")

        if self.use_json:
            output_str = self.format_collection_json(metrics)
        else:
            output_str = self.format_collection_line(metrics)

        self._write(output_str)

    # =========================================================================
    # Table Output (for CLI)
    # =========================================================================

    def format_discovery_table(
        self,
        instances: list[DiscoveredInstance],
        show_properties: bool = False,
    ) -> str:
        """
        Format instances as ASCII table for CLI display.

        Args:
            instances: List of discovered instances
            show_properties: Include properties column

        Returns:
            ASCII table string
        """
        if not instances:
            return "No instances discovered."

        # Calculate column widths
        id_width = max(len(i.instance_id) for i in instances)
        name_width = max(len(i.instance_name) for i in instances)
        desc_width = max((len(i.description) for i in instances), default=0)

        id_width = max(id_width, 11)  # "Instance ID"
        name_width = max(name_width, 4)  # "Name"
        desc_width = max(desc_width, 11)  # "Description"

        lines = []

        # Header
        if show_properties:
            header = f"{'Instance ID':<{id_width}}  {'Name':<{name_width}}  {'Description':<{desc_width}}  Properties"
        else:
            header = f"{'Instance ID':<{id_width}}  {'Name':<{name_width}}  {'Description':<{desc_width}}"
        lines.append(header)
        lines.append("-" * len(header))

        # Rows
        for inst in instances:
            if show_properties and inst.properties:
                props = ", ".join(f"{k}={v}" for k, v in inst.properties.items())
                line = f"{inst.instance_id:<{id_width}}  {inst.instance_name:<{name_width}}  {inst.description:<{desc_width}}  {props}"
            else:
                line = f"{inst.instance_id:<{id_width}}  {inst.instance_name:<{name_width}}  {inst.description:<{desc_width}}"
            lines.append(line)

        return "\n".join(lines)

    def format_collection_table(self, metrics: list[MetricValue]) -> str:
        """
        Format metrics as ASCII table for CLI display.

        Args:
            metrics: List of metric values

        Returns:
            ASCII table string
        """
        if not metrics:
            return "No metrics collected."

        # Calculate column widths
        inst_width = max((len(m.instance_id or "") for m in metrics), default=0)
        name_width = max(len(m.name) for m in metrics)
        value_width = max(len(str(m.value)) for m in metrics if m.value is not None)

        inst_width = max(inst_width, 8)  # "Instance"
        name_width = max(name_width, 6)  # "Metric"
        value_width = max(value_width, 5)  # "Value"

        lines = []

        # Header
        header = f"{'Instance':<{inst_width}}  {'Metric':<{name_width}}  {'Value':>{value_width}}"
        lines.append(header)
        lines.append("-" * len(header))

        # Rows
        for m in metrics:
            if m.value is not None:
                inst = m.instance_id or "-"
                line = f"{inst:<{inst_width}}  {m.name:<{name_width}}  {m.value:>{value_width}}"
                lines.append(line)

        return "\n".join(lines)


# =============================================================================
# Convenience Functions
# =============================================================================


def print_discovery(
    instances: list[DiscoveredInstance],
    use_json: bool = False,
) -> None:
    """
    Print discovery output to stdout.

    Args:
        instances: List of discovered instances
        use_json: Output in JSON format
    """
    formatter = OutputFormatter(use_json=use_json)
    formatter.write_discovery(instances)


def print_collection(
    metrics: list[MetricValue],
    use_json: bool = False,
) -> None:
    """
    Print collection output to stdout.

    Args:
        metrics: List of metric values
        use_json: Output in JSON format
    """
    formatter = OutputFormatter(use_json=use_json)
    formatter.write_collection(metrics)


def print_discovery_table(
    instances: list[DiscoveredInstance],
    show_properties: bool = False,
) -> None:
    """
    Print discovery instances as ASCII table.

    Args:
        instances: List of discovered instances
        show_properties: Include properties column
    """
    formatter = OutputFormatter()
    print(formatter.format_discovery_table(instances, show_properties))


def print_collection_table(metrics: list[MetricValue]) -> None:
    """
    Print collected metrics as ASCII table.

    Args:
        metrics: List of metric values
    """
    formatter = OutputFormatter()
    print(formatter.format_collection_table(metrics))
