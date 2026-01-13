"""
Tests for output formatter module.
"""

import json
from io import StringIO

from lmn_tools.collectors.optical.formatter import (
    OutputFormatter,
    format_collection_output,
    format_discovery_output,
)
from lmn_tools.collectors.optical.parser import DiscoveredInstance, MetricValue


class TestDiscoveryFormatting:
    """Tests for Active Discovery output formatting."""

    def test_basic_discovery_output(self):
        """Test basic discovery line format."""
        instance = DiscoveredInstance(
            instance_id="ots-1-1",
            instance_name="OTS Port 1-1"
        )
        formatter = OutputFormatter()
        line = formatter.format_discovery_instance(instance)

        assert line == "ots-1-1##OTS Port 1-1"

    def test_discovery_with_description(self):
        """Test discovery with description."""
        instance = DiscoveredInstance(
            instance_id="ots-1-1",
            instance_name="OTS Port 1-1",
            description="Line East Interface"
        )
        formatter = OutputFormatter()
        line = formatter.format_discovery_instance(instance)

        assert line == "ots-1-1##OTS Port 1-1##Line East Interface"

    def test_discovery_with_properties(self):
        """Test discovery with auto.* properties."""
        instance = DiscoveredInstance(
            instance_id="ots-1-1",
            instance_name="OTS Port 1-1",
            description="Line East Interface",
            properties={"fiber_type": "SMF-28", "direction": "east"}
        )
        formatter = OutputFormatter()
        line = formatter.format_discovery_instance(instance)

        assert "ots-1-1##OTS Port 1-1##Line East Interface##" in line
        assert "auto.fiber_type=SMF-28" in line
        assert "auto.direction=east" in line

    def test_discovery_properties_without_description(self):
        """Test discovery with properties but no description."""
        instance = DiscoveredInstance(
            instance_id="ots-1-1",
            instance_name="OTS Port 1-1",
            properties={"fiber_type": "SMF-28"}
        )
        formatter = OutputFormatter()
        line = formatter.format_discovery_instance(instance)

        # Should have empty description placeholder
        assert "ots-1-1##OTS Port 1-1##" in line
        assert "auto.fiber_type=SMF-28" in line

    def test_format_multiple_instances(self):
        """Test formatting multiple instances."""
        instances = [
            DiscoveredInstance(
                instance_id="ots-1-1",
                instance_name="OTS Port 1-1"
            ),
            DiscoveredInstance(
                instance_id="ots-1-2",
                instance_name="OTS Port 1-2"
            ),
        ]
        formatter = OutputFormatter()
        output = formatter.format_discovery(instances)

        lines = output.split("\n")
        assert len(lines) == 2
        assert lines[0] == "ots-1-1##OTS Port 1-1"
        assert lines[1] == "ots-1-2##OTS Port 1-2"


class TestCollectionFormatting:
    """Tests for BATCHSCRIPT collection output formatting."""

    def test_basic_collection_line(self):
        """Test basic collection line format."""
        formatter = OutputFormatter()
        line = formatter.format_collection_line("ots-1-1", "rx_optical_power", -12.5)

        assert line == "ots-1-1.rx_optical_power=-12.5"

    def test_format_multiple_metrics(self):
        """Test formatting multiple metrics."""
        metrics = [
            MetricValue(
                name="rx_optical_power",
                value=-12.5,
                instance_id="ots-1-1"
            ),
            MetricValue(
                name="tx_optical_power",
                value=1.2,
                instance_id="ots-1-1"
            ),
            MetricValue(
                name="rx_optical_power",
                value=-14.2,
                instance_id="ots-1-2"
            ),
        ]
        formatter = OutputFormatter()
        output = formatter.format_collection(metrics)

        lines = output.split("\n")
        assert len(lines) == 3
        assert "ots-1-1.rx_optical_power=-12.5" in lines
        assert "ots-1-1.tx_optical_power=1.2" in lines
        assert "ots-1-2.rx_optical_power=-14.2" in lines

    def test_skip_none_values(self):
        """Test that None values are skipped."""
        metrics = [
            MetricValue(
                name="rx_optical_power",
                value=-12.5,
                instance_id="ots-1-1"
            ),
            MetricValue(
                name="tx_optical_power",
                value=None,
                instance_id="ots-1-1"
            ),
        ]
        formatter = OutputFormatter()
        output = formatter.format_collection(metrics)

        lines = [line for line in output.split("\n") if line]
        assert len(lines) == 1
        assert "rx_optical_power" in lines[0]


class TestJsonFormatting:
    """Tests for JSON output formatting."""

    def test_json_collection_format(self):
        """Test JSON collection output format."""
        metrics = [
            MetricValue(
                name="rx_optical_power",
                value=-12.5,
                instance_id="ots-1-1"
            ),
            MetricValue(
                name="tx_optical_power",
                value=1.2,
                instance_id="ots-1-1"
            ),
            MetricValue(
                name="rx_optical_power",
                value=-14.2,
                instance_id="ots-1-2"
            ),
        ]
        formatter = OutputFormatter(use_json=True)
        output = formatter.format_collection_json(metrics)

        data = json.loads(output)

        assert "data" in data
        assert "ots-1-1" in data["data"]
        assert "ots-1-2" in data["data"]
        assert data["data"]["ots-1-1"]["values"]["rx_optical_power"] == -12.5
        assert data["data"]["ots-1-1"]["values"]["tx_optical_power"] == 1.2
        assert data["data"]["ots-1-2"]["values"]["rx_optical_power"] == -14.2

    def test_json_structure(self):
        """Test JSON has correct nested structure."""
        metrics = [
            MetricValue(
                name="admin_status",
                value=1,
                instance_id="test-instance"
            ),
        ]
        formatter = OutputFormatter(use_json=True)
        output = formatter.format_collection_json(metrics)

        data = json.loads(output)

        # Verify nested structure
        assert isinstance(data, dict)
        assert isinstance(data["data"], dict)
        assert isinstance(data["data"]["test-instance"], dict)
        assert isinstance(data["data"]["test-instance"]["values"], dict)


class TestOutputWriting:
    """Tests for output writing to streams."""

    def test_write_discovery_to_stream(self):
        """Test writing discovery output to a stream."""
        instances = [
            DiscoveredInstance(
                instance_id="ots-1-1",
                instance_name="OTS Port 1-1"
            ),
        ]
        output = StringIO()
        formatter = OutputFormatter(output=output)
        formatter.write_discovery(instances)

        result = output.getvalue()
        assert "ots-1-1##OTS Port 1-1" in result

    def test_write_collection_to_stream(self):
        """Test writing collection output to a stream."""
        metrics = [
            MetricValue(
                name="rx_optical_power",
                value=-12.5,
                instance_id="ots-1-1"
            ),
        ]
        output = StringIO()
        formatter = OutputFormatter(output=output)
        formatter.write_collection(metrics)

        result = output.getvalue()
        assert "ots-1-1.rx_optical_power=-12.5" in result


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_format_discovery_output_function(self):
        """Test format_discovery_output convenience function."""
        instances = [
            DiscoveredInstance(
                instance_id="test",
                instance_name="Test Instance"
            ),
        ]
        output = format_discovery_output(instances)
        assert "test##Test Instance" in output

    def test_format_collection_output_function(self):
        """Test format_collection_output convenience function."""
        metrics = [
            MetricValue(
                name="test_metric",
                value=42.0,
                instance_id="test"
            ),
        ]
        output = format_collection_output(metrics)
        assert "test.test_metric=42.0" in output

    def test_format_collection_output_json(self):
        """Test format_collection_output with JSON."""
        metrics = [
            MetricValue(
                name="test_metric",
                value=42.0,
                instance_id="test"
            ),
        ]
        output = format_collection_output(metrics, use_json=True)

        data = json.loads(output)
        assert data["data"]["test"]["values"]["test_metric"] == 42.0
