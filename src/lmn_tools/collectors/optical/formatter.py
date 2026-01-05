"""
Output formatter for LogicMonitor-compatible data formats.

Handles formatting of:
- Active Discovery output (instance discovery)
- BATCHSCRIPT collection output (metric collection)
- Both line-based and JSON output formats
"""

import json
import sys
from typing import Dict, List, Optional, Any, TextIO
from dataclasses import dataclass

from .parser import DiscoveredInstance, MetricValue


class OutputFormatter:
    """
    Formatter for LogicMonitor script output.

    Supports two output modes:
    - Line-based: Simple text format for discovery and collection
    - JSON: Structured JSON format for BATCHSCRIPT collection

    Line-based Discovery format:
        instance_id##instance_name
        instance_id##instance_name##description
        instance_id##instance_name##description####auto.prop1=val1&auto.prop2=val2

    Line-based Collection format:
        instance_id.datapoint_name=numeric_value

    JSON Collection format:
        {
            "data": {
                "instance_id": {
                    "values": {
                        "datapoint_name": numeric_value
                    }
                }
            }
        }
    """

    def __init__(
        self,
        output: TextIO = None,
        use_json: bool = False,
        debug: bool = False
    ):
        """
        Initialize the output formatter.

        Args:
            output: Output stream (default: sys.stdout)
            use_json: Use JSON format for collection output
            debug: Enable debug output to stderr
        """
        self.output = output or sys.stdout
        self.use_json = use_json
        self.debug = debug

    # =========================================================================
    # Active Discovery Output
    # =========================================================================

    def format_discovery(
        self,
        instances: List[DiscoveredInstance]
    ) -> str:
        """
        Format instances for LogicMonitor Active Discovery output.

        Args:
            instances: List of discovered instances

        Returns:
            Formatted discovery output string
        """
        lines = []
        for instance in instances:
            line = self.format_discovery_instance(instance)
            lines.append(line)
        return "\n".join(lines)

    def format_discovery_instance(self, instance: DiscoveredInstance) -> str:
        """
        Format a single instance for discovery output.

        Format: instance_id##instance_name##description####auto.prop=val&auto.prop2=val2

        Args:
            instance: The discovered instance

        Returns:
            Formatted line string
        """
        parts = [instance.instance_id, instance.instance_name]

        # Add description if present
        if instance.description:
            parts.append(instance.description)
        elif instance.properties:
            # Need description placeholder if we have properties
            parts.append("")

        # Add properties if present
        if instance.properties:
            props_str = "&".join(
                f"auto.{k}={v}" for k, v in instance.properties.items()
            )
            parts.append("")  # Empty field before properties
            parts.append(props_str)

        return "##".join(parts)

    def write_discovery(self, instances: List[DiscoveredInstance]) -> None:
        """
        Write discovery output to the output stream.

        Args:
            instances: List of discovered instances
        """
        output_str = self.format_discovery(instances)
        self.output.write(output_str)
        if output_str and not output_str.endswith("\n"):
            self.output.write("\n")
        self.output.flush()

    # =========================================================================
    # Collection Output (Line-based)
    # =========================================================================

    def format_collection_line(
        self,
        instance_id: str,
        datapoint: str,
        value: float
    ) -> str:
        """
        Format a single metric for line-based collection output.

        Format: instance_id.datapoint_name=numeric_value

        Args:
            instance_id: Instance identifier
            datapoint: Datapoint/metric name
            value: Numeric value

        Returns:
            Formatted line string
        """
        return f"{instance_id}.{datapoint}={value}"

    def format_collection(self, metrics: List[MetricValue]) -> str:
        """
        Format metrics for line-based BATCHSCRIPT collection output.

        Args:
            metrics: List of metric values

        Returns:
            Formatted collection output string
        """
        lines = []
        for metric in metrics:
            if metric.instance_id and metric.name and metric.value is not None:
                line = self.format_collection_line(
                    metric.instance_id,
                    metric.name,
                    metric.value
                )
                lines.append(line)
        return "\n".join(lines)

    def write_collection(self, metrics: List[MetricValue]) -> None:
        """
        Write collection output to the output stream.

        Automatically uses JSON or line format based on use_json setting.

        Args:
            metrics: List of metric values
        """
        if self.use_json:
            self.write_collection_json(metrics)
        else:
            output_str = self.format_collection(metrics)
            self.output.write(output_str)
            if output_str and not output_str.endswith("\n"):
                self.output.write("\n")
            self.output.flush()

    # =========================================================================
    # Collection Output (JSON)
    # =========================================================================

    def format_collection_json(self, metrics: List[MetricValue]) -> str:
        """
        Format metrics for JSON BATCHSCRIPT collection output.

        Format:
        {
            "data": {
                "instance_id": {
                    "values": {
                        "datapoint": value,
                        ...
                    }
                },
                ...
            }
        }

        Args:
            metrics: List of metric values

        Returns:
            JSON-formatted string
        """
        data: Dict[str, Dict[str, Dict[str, float]]] = {}

        for metric in metrics:
            if not metric.instance_id or not metric.name:
                continue
            if metric.value is None:
                continue

            if metric.instance_id not in data:
                data[metric.instance_id] = {"values": {}}

            data[metric.instance_id]["values"][metric.name] = metric.value

        output = {"data": data}
        return json.dumps(output, indent=2)

    def write_collection_json(self, metrics: List[MetricValue]) -> None:
        """
        Write JSON collection output to the output stream.

        Args:
            metrics: List of metric values
        """
        output_str = self.format_collection_json(metrics)
        self.output.write(output_str)
        self.output.write("\n")
        self.output.flush()

    # =========================================================================
    # Grouped Output (by instance)
    # =========================================================================

    def format_collection_grouped(
        self,
        metrics_by_instance: Dict[str, List[MetricValue]]
    ) -> str:
        """
        Format metrics grouped by instance.

        Useful when you want to output metrics instance-by-instance.

        Args:
            metrics_by_instance: Dict mapping instance_id -> list of metrics

        Returns:
            Formatted collection output
        """
        lines = []
        for instance_id, metrics in metrics_by_instance.items():
            for metric in metrics:
                if metric.name and metric.value is not None:
                    line = self.format_collection_line(
                        instance_id,
                        metric.name,
                        metric.value
                    )
                    lines.append(line)
        return "\n".join(lines)

    # =========================================================================
    # Debug Output
    # =========================================================================

    def debug_print(self, message: str) -> None:
        """
        Print debug message to stderr if debug mode is enabled.

        Args:
            message: Debug message to print
        """
        if self.debug:
            print(f"DEBUG: {message}", file=sys.stderr)

    def error_print(self, message: str) -> None:
        """
        Print error message to stderr.

        Args:
            message: Error message to print
        """
        print(f"ERROR: {message}", file=sys.stderr)


def format_discovery_output(instances: List[DiscoveredInstance]) -> str:
    """
    Convenience function to format discovery output.

    Args:
        instances: List of discovered instances

    Returns:
        Formatted discovery output string
    """
    formatter = OutputFormatter()
    return formatter.format_discovery(instances)


def format_collection_output(
    metrics: List[MetricValue],
    use_json: bool = False
) -> str:
    """
    Convenience function to format collection output.

    Args:
        metrics: List of metric values
        use_json: Use JSON format

    Returns:
        Formatted collection output string
    """
    formatter = OutputFormatter(use_json=use_json)
    if use_json:
        return formatter.format_collection_json(metrics)
    return formatter.format_collection(metrics)


def print_discovery(instances: List[DiscoveredInstance]) -> None:
    """
    Convenience function to print discovery output to stdout.

    Args:
        instances: List of discovered instances
    """
    formatter = OutputFormatter()
    formatter.write_discovery(instances)


def print_collection(
    metrics: List[MetricValue],
    use_json: bool = False
) -> None:
    """
    Convenience function to print collection output to stdout.

    Args:
        metrics: List of metric values
        use_json: Use JSON format
    """
    formatter = OutputFormatter(use_json=use_json)
    formatter.write_collection(metrics)
