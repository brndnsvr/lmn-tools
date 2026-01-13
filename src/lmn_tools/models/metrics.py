"""
Metric models for LogicMonitor collection output.

These models represent metric values collected from devices
and format them for LogicMonitor's collection script output.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from lmn_tools.constants import LMOutputFormat


class MetricValue(BaseModel):
    """
    Single metric value for LogicMonitor collection.

    Represents a single datapoint value that will be output
    in LogicMonitor's BATCHSCRIPT or JSON format.

    Attributes:
        name: Datapoint name (e.g., "rxPower", "temperature")
        value: Numeric metric value
        instance_id: Instance identifier (for multi-instance datasources)
        instance_name: Human-readable instance name
        labels: Additional labels/tags for the metric
        help_text: Documentation for the metric
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, description="Datapoint name")
    value: float | None = Field(description="Metric value")
    instance_id: str | None = Field(default=None, description="Instance identifier")
    instance_name: str | None = Field(default=None, description="Instance display name")
    labels: dict[str, str] = Field(default_factory=dict, description="Additional labels")
    help_text: str | None = Field(default=None, description="Metric documentation")

    def to_collection_line(self) -> str:
        """
        Format metric for LogicMonitor BATCHSCRIPT output.

        Output format:
            instance_id.datapoint_name=value

        For single-instance datasources (no instance_id):
            datapoint_name=value

        Returns:
            Formatted collection line string
        """
        if self.value is None:
            return ""

        sep = LMOutputFormat.METRIC_SEPARATOR
        eq = LMOutputFormat.METRIC_VALUE_SEPARATOR

        if not self.instance_id:
            return f"{self.name}{eq}{self.value}"
        return f"{self.instance_id}{sep}{self.name}{eq}{self.value}"

    @classmethod
    def create(
        cls,
        name: str,
        value: float | None,
        instance_id: str | None = None,
        **kwargs: Any,
    ) -> MetricValue:
        """
        Factory method for creating metric values.

        Args:
            name: Datapoint name
            value: Metric value
            instance_id: Optional instance identifier
            **kwargs: Additional fields (instance_name, labels, help_text)

        Returns:
            MetricValue instance
        """
        return cls(name=name, value=value, instance_id=instance_id, **kwargs)


class MetricCollection(BaseModel):
    """
    Collection of metrics from a single collection run.

    Aggregates multiple MetricValue objects and provides
    methods to output them in various formats.

    Attributes:
        metrics: List of MetricValue objects
        timestamp: Collection timestamp (epoch seconds)
        hostname: Source device hostname
        datasource: Datasource name
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    metrics: list[MetricValue] = Field(default_factory=list)
    timestamp: float | None = Field(default=None, description="Collection timestamp")
    hostname: str | None = Field(default=None, description="Source device")
    datasource: str | None = Field(default=None, description="Datasource name")

    def add(self, metric: MetricValue) -> None:
        """Add a metric to the collection."""
        self.metrics.append(metric)

    def add_metric(
        self,
        name: str,
        value: float | None,
        instance_id: str | None = None,
        **kwargs: Any,
    ) -> MetricValue:
        """
        Create and add a metric in one step.

        Args:
            name: Datapoint name
            value: Metric value
            instance_id: Optional instance identifier
            **kwargs: Additional fields

        Returns:
            The created MetricValue
        """
        metric = MetricValue.create(name, value, instance_id, **kwargs)
        self.add(metric)
        return metric

    def to_line_output(self) -> str:
        """
        Format all metrics for BATCHSCRIPT output.

        Returns:
            Newline-separated metric lines
        """
        lines = []
        for m in self.metrics:
            if m.value is not None:
                line = m.to_collection_line()
                if line:
                    lines.append(line)
        return "\n".join(lines)

    def to_json_output(self) -> dict[str, Any]:
        """
        Format metrics for JSON output.

        Output format:
            {
                "data": {
                    "instance_id": {
                        "values": {
                            "datapoint1": value1,
                            "datapoint2": value2
                        }
                    }
                }
            }

        Returns:
            Dictionary suitable for JSON serialization
        """
        data: dict[str, dict[str, Any]] = {}

        for m in self.metrics:
            if m.value is None:
                continue

            # For single-instance datasources, use empty string as key
            instance_key = m.instance_id or ""

            if instance_key not in data:
                data[instance_key] = {"values": {}}
                if m.instance_name:
                    data[instance_key]["name"] = m.instance_name
                if m.labels:
                    data[instance_key]["labels"] = m.labels

            data[instance_key]["values"][m.name] = m.value

        return {"data": data}

    def get_instance_ids(self) -> set[str]:
        """Return set of unique instance IDs in the collection."""
        return {m.instance_id for m in self.metrics if m.instance_id}

    def get_metrics_for_instance(self, instance_id: str) -> list[MetricValue]:
        """Return all metrics for a specific instance."""
        return [m for m in self.metrics if m.instance_id == instance_id]

    def filter_by_name(self, *names: str) -> list[MetricValue]:
        """Return metrics matching any of the given names."""
        name_set = set(names)
        return [m for m in self.metrics if m.name in name_set]

    def __len__(self) -> int:
        """Return number of metrics in collection."""
        return len(self.metrics)

    def __iter__(self) -> Any:
        """Iterate over metrics."""
        return iter(self.metrics)

    def __bool__(self) -> bool:
        """Return True if collection has metrics."""
        return bool(self.metrics)
