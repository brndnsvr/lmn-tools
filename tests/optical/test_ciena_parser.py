"""
Tests for Ciena WaveServer XML parsing and metric extraction.
"""

import pytest
from pathlib import Path
from lxml import etree

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.xml_parser import XmlParser, DiscoveredInstance, MetricValue
import yaml


# Load fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def ciena_ptp_response():
    """Load Ciena PTP response fixture."""
    with open(FIXTURES_DIR / "ciena_ptp_response.xml", "rb") as f:
        return etree.parse(f).getroot()


@pytest.fixture
def ciena_chassis_response():
    """Load Ciena chassis response fixture."""
    with open(FIXTURES_DIR / "ciena_chassis_response.xml", "rb") as f:
        return etree.parse(f).getroot()


@pytest.fixture
def ciena_config():
    """Load Ciena configuration."""
    config_path = Path(__file__).parent.parent / "configs" / "ciena.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def ciena_chassis_config():
    """Load Ciena chassis configuration."""
    config_path = Path(__file__).parent.parent / "configs" / "ciena_chassis.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


class TestCienaPtpDiscovery:
    """Test Ciena PTP interface discovery."""

    def test_discover_ptp_instances(self, ciena_ptp_response, ciena_config):
        """Test discovering PTP instances."""
        parser = XmlParser(debug=False)
        instances = parser.discover_instances(ciena_ptp_response, ciena_config)

        # Should discover 2 PTPs + 2 Ports = 4 instances
        assert len(instances) >= 2

        # Find PTP instances
        ptp_instances = [i for i in instances if i.properties.get("interface_type") == "ptp"]
        assert len(ptp_instances) == 2

        # Check first PTP
        ptp1 = next(i for i in ptp_instances if "1" in i.instance_id)
        assert ptp1.instance_id is not None
        assert "ptp" in ptp1.properties.get("interface_type", "").lower()

    def test_discover_port_instances(self, ciena_ptp_response, ciena_config):
        """Test discovering Port instances."""
        parser = XmlParser(debug=False)
        instances = parser.discover_instances(ciena_ptp_response, ciena_config)

        # Find Port instances
        port_instances = [i for i in instances if i.properties.get("interface_type") == "port"]
        assert len(port_instances) == 2

        # Check first port has properties
        port1 = port_instances[0]
        assert port1.instance_id is not None


class TestCienaPtpMetrics:
    """Test Ciena PTP metric extraction."""

    def test_collect_ptp_metrics(self, ciena_ptp_response, ciena_config):
        """Test collecting PTP metrics."""
        parser = XmlParser(debug=False)
        metrics = parser.collect_metrics(ciena_ptp_response, ciena_config)

        # Should have metrics from PTPs and Ports
        assert len(metrics) > 0

        # Check for admin_status metrics
        admin_metrics = [m for m in metrics if m.name == "admin_status"]
        assert len(admin_metrics) > 0

    def test_ptp_admin_status_string_map(self, ciena_ptp_response, ciena_config):
        """Test admin_status string map conversion."""
        parser = XmlParser(debug=False)
        metrics = parser.collect_metrics(ciena_ptp_response, ciena_config)

        # Find admin_status for first PTP (should be enabled -> 1)
        admin_metrics = [m for m in metrics if m.name == "admin_status"]
        enabled_metrics = [m for m in admin_metrics if m.value == 1.0]
        disabled_metrics = [m for m in admin_metrics if m.value == 0.0]

        assert len(enabled_metrics) > 0  # At least one enabled interface
        assert len(disabled_metrics) > 0  # At least one disabled interface

    def test_transmitter_power_extraction(self, ciena_ptp_response, ciena_config):
        """Test transmitter power metric extraction."""
        parser = XmlParser(debug=False)
        metrics = parser.collect_metrics(ciena_ptp_response, ciena_config)

        # Find transmitter_power metrics
        tx_power_metrics = [m for m in metrics if m.name == "transmitter_power"]
        assert len(tx_power_metrics) > 0

        # Check the active PTP has power value
        active_power = [m for m in tx_power_metrics if m.value == 1.5]
        assert len(active_power) >= 1

    def test_span_loss_metrics(self, ciena_ptp_response, ciena_config):
        """Test span loss metric extraction."""
        parser = XmlParser(debug=False)
        metrics = parser.collect_metrics(ciena_ptp_response, ciena_config)

        # Find tx_span_loss metrics
        tx_span_loss = [m for m in metrics if m.name == "tx_span_loss"]
        assert len(tx_span_loss) > 0

        # Check for expected value
        expected_loss = [m for m in tx_span_loss if m.value == 12.5]
        assert len(expected_loss) >= 1


class TestCienaPortMetrics:
    """Test Ciena Port metric extraction."""

    def test_port_speed_extraction(self, ciena_ptp_response, ciena_config):
        """Test port speed metric extraction."""
        parser = XmlParser(debug=False)
        metrics = parser.collect_metrics(ciena_ptp_response, ciena_config)

        # Find speed metrics
        speed_metrics = [m for m in metrics if m.name == "speed"]
        assert len(speed_metrics) > 0

        # Check for 100GE speed
        expected_speed = [m for m in speed_metrics if m.value == 100000000000]
        assert len(expected_speed) >= 1

    def test_oper_state_duration(self, ciena_ptp_response, ciena_config):
        """Test operational state duration metric."""
        parser = XmlParser(debug=False)
        metrics = parser.collect_metrics(ciena_ptp_response, ciena_config)

        # Find oper_state_duration metrics
        duration_metrics = [m for m in metrics if m.name == "oper_state_duration"]
        assert len(duration_metrics) > 0


class TestCienaChassis:
    """Test Ciena chassis metric extraction."""

    def test_software_oper_state(self, ciena_chassis_response, ciena_chassis_config):
        """Test software operational state extraction."""
        # For chassis metrics, we need to test the xpath extraction directly
        # since the chassis config uses a different structure
        from src.utils import get_local_name, extract_element_text

        # Find software-operational-state
        for elem in ciena_chassis_response.iter():
            local_name = get_local_name(elem.tag)
            if local_name == "software-operational-state":
                text = extract_element_text(elem)
                assert text == "normal"
                return

        # If we get here, the element wasn't found
        pytest.fail("software-operational-state not found in response")

    def test_active_version_label(self, ciena_chassis_response, ciena_chassis_config):
        """Test active version label extraction."""
        from src.utils import get_local_name, extract_element_text

        # Find active-version
        for elem in ciena_chassis_response.iter():
            local_name = get_local_name(elem.tag)
            if local_name == "active-version":
                text = extract_element_text(elem)
                assert text == "waveserver-1.9.0"
                return

        pytest.fail("active-version not found in response")


class TestCienaInstanceIds:
    """Test Ciena instance ID handling."""

    def test_ptp_instance_id_sanitization(self, ciena_ptp_response, ciena_config):
        """Test that PTP instance IDs are properly sanitized."""
        parser = XmlParser(debug=False)
        instances = parser.discover_instances(ciena_ptp_response, ciena_config)

        for instance in instances:
            # Instance IDs should not contain invalid characters
            assert ":" not in instance.instance_id
            assert "#" not in instance.instance_id
            assert "\\" not in instance.instance_id
            assert " " not in instance.instance_id

    def test_port_fallback_id(self, ciena_ptp_response, ciena_config):
        """Test port fallback ID when primary ID is not available."""
        parser = XmlParser(debug=False)
        instances = parser.discover_instances(ciena_ptp_response, ciena_config)

        # All instances should have non-empty IDs
        for instance in instances:
            assert instance.instance_id
            assert len(instance.instance_id) > 0


class TestCienaDebugOutput:
    """Test debug output functionality for Ciena parsing."""

    def test_debug_mode_no_errors(self, ciena_ptp_response, ciena_config):
        """Test that debug mode doesn't cause errors."""
        parser = XmlParser(debug=True)

        # Should not raise any exceptions
        instances = parser.discover_instances(ciena_ptp_response, ciena_config)
        metrics = parser.collect_metrics(ciena_ptp_response, ciena_config)

        assert len(instances) > 0
        assert len(metrics) > 0
