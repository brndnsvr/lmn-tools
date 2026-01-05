"""
Tests for XML parser module.
"""

import pytest
from pathlib import Path
from lxml import etree

from src.xml_parser import XmlParser, DiscoveredInstance, MetricValue


# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "namespaces": {
            "ne": "http://coriant.com/yang/os/ne",
            "nc": "urn:ietf:params:xml:ns:netconf:base:1.0",
        },
        "chassis": {
            "xpath": "ne",
            "metrics": [
                {"name": "ne_temperature", "xpath": "ne-temperature"},
                {"name": "ne_altitude", "xpath": "ne-altitude"},
            ]
        },
        "interfaces": {
            "ots": {
                "xpath": ".//ots",
                "instance_key": "alias-name",
                "fallback_id_key": "ots-name",  # Fallback if alias-name is empty
                "instance_name_key": "alias-name",
                "description_key": "ots-name",
                "properties": ["fiber-type"],
                "metrics": [
                    {
                        "name": "admin_status",
                        "xpath": "admin-status",
                        "string_map": {"down": 0, "up": 1}
                    },
                    {
                        "name": "oper_status",
                        "xpath": "oper-status",
                        "string_map": {"down": 0, "up": 1}
                    },
                    {"name": "measured_span_loss", "xpath": "measured-span-loss"},
                    {"name": "fiber_length_tx_derived", "xpath": "fiber-length-tx-derived"},
                ]
            },
            "oms": {
                "xpath": ".//oms",
                "instance_key": "alias-name",
                "instance_name_key": "alias-name",
                "description_key": "oms-name",
                "properties": ["grid-mode"],
                "metrics": [
                    {
                        "name": "admin_status",
                        "xpath": "admin-status",
                        "string_map": {"down": 0, "up": 1}
                    },
                    {
                        "name": "oper_status",
                        "xpath": "oper-status",
                        "string_map": {"down": 0, "up": 1}
                    },
                    {"name": "rx_optical_power", "xpath": "rx-optical-power"},
                    {"name": "tx_optical_power", "xpath": "tx-optical-power"},
                    {"name": "in_optical_power_instant", "xpath": "statistics/in-optical-power/instant"},
                ]
            },
            "osc": {
                "xpath": ".//osc",
                "instance_key": "alias-name",
                "instance_name_key": "alias-name",
                "description_key": "osc-name",
                "properties": ["osc-mode"],
                "metrics": [
                    {
                        "name": "admin_status",
                        "xpath": "admin-status",
                        "string_map": {"down": 0, "up": 1}
                    },
                    {"name": "rx_optical_power", "xpath": "rx-optical-power"},
                    {"name": "tx_optical_power", "xpath": "tx-optical-power"},
                    {"name": "osc_wavelength", "xpath": "osc-wavelength"},
                ]
            },
        }
    }


@pytest.fixture
def sample_xml():
    """Load sample XML fixture."""
    fixture_path = FIXTURES_DIR / "coriant_response.xml"
    if fixture_path.exists():
        with open(fixture_path, 'rb') as f:
            return etree.parse(f).getroot()
    else:
        # Inline minimal XML for testing if fixture doesn't exist
        xml_str = """
        <data xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
          <ne xmlns="http://coriant.com/yang/os/ne">
            <ne-temperature>28.5</ne-temperature>
            <ne-altitude>152</ne-altitude>
            <services>
              <optical-interfaces>
                <ots>
                  <ots-name>OTS-1-1-1</ots-name>
                  <admin-status>up</admin-status>
                  <oper-status>up</oper-status>
                  <alias-name>Line-East-OTS</alias-name>
                  <measured-span-loss>18.5</measured-span-loss>
                  <fiber-type>SMF-28</fiber-type>
                  <fiber-length-tx-derived>85.2</fiber-length-tx-derived>
                </ots>
                <oms>
                  <oms-name>OMS-1-1-1</oms-name>
                  <admin-status>up</admin-status>
                  <oper-status>up</oper-status>
                  <alias-name>C-Band-East-OMS</alias-name>
                  <rx-optical-power>-12.5</rx-optical-power>
                  <tx-optical-power>1.2</tx-optical-power>
                  <grid-mode>flexible</grid-mode>
                  <statistics>
                    <in-optical-power>
                      <instant>-12.3</instant>
                    </in-optical-power>
                  </statistics>
                </oms>
                <osc>
                  <osc-name>OSC-1-1-1</osc-name>
                  <admin-status>up</admin-status>
                  <oper-status>up</oper-status>
                  <alias-name>OSC-East</alias-name>
                  <osc-mode>bidirectional</osc-mode>
                  <rx-optical-power>-18.2</rx-optical-power>
                  <tx-optical-power>2.1</tx-optical-power>
                  <osc-wavelength>1510.0</osc-wavelength>
                </osc>
              </optical-interfaces>
            </services>
          </ne>
        </data>
        """
        return etree.fromstring(xml_str.encode())


class TestXmlParser:
    """Tests for XmlParser class."""

    def test_parser_initialization(self):
        """Test parser can be initialized."""
        parser = XmlParser()
        assert parser is not None

    def test_parser_with_namespaces(self, sample_config):
        """Test parser with namespace configuration."""
        parser = XmlParser(namespaces=sample_config["namespaces"])
        assert "ne" in parser.namespaces

    def test_discover_instances(self, sample_xml, sample_config):
        """Test instance discovery from XML."""
        parser = XmlParser(namespaces=sample_config["namespaces"])
        instances = parser.discover_instances(sample_xml, sample_config)

        assert len(instances) > 0

        # Check that we found the expected interface types
        instance_ids = [i.instance_id for i in instances]
        assert any("Line-East-OTS" in id for id in instance_ids)

    def test_collect_metrics(self, sample_xml, sample_config):
        """Test metric collection from XML."""
        parser = XmlParser(namespaces=sample_config["namespaces"])
        metrics = parser.collect_metrics(sample_xml, sample_config)

        assert len(metrics) > 0

        # Check that we collected expected metrics
        metric_names = [m.name for m in metrics]
        assert "admin_status" in metric_names or any("admin" in n for n in metric_names)

    def test_string_map_conversion(self, sample_xml, sample_config):
        """Test that string maps are applied correctly."""
        parser = XmlParser(namespaces=sample_config["namespaces"])
        metrics = parser.collect_metrics(sample_xml, sample_config)

        # Find admin_status metrics
        admin_metrics = [m for m in metrics if m.name == "admin_status"]

        # All should be numeric (0 or 1)
        for m in admin_metrics:
            assert m.value in [0.0, 1.0]


class TestDiscoveredInstance:
    """Tests for DiscoveredInstance dataclass."""

    def test_creation(self):
        """Test basic instance creation."""
        instance = DiscoveredInstance(
            instance_id="ots-1-1",
            instance_name="OTS Port 1-1",
            description="Line East Interface",
            properties={"fiber_type": "SMF-28"}
        )
        assert instance.instance_id == "ots-1-1"
        assert instance.instance_name == "OTS Port 1-1"
        assert instance.description == "Line East Interface"
        assert instance.properties["fiber_type"] == "SMF-28"

    def test_default_values(self):
        """Test default values."""
        instance = DiscoveredInstance(
            instance_id="test",
            instance_name="Test"
        )
        assert instance.description == ""
        assert instance.properties == {}


class TestMetricValue:
    """Tests for MetricValue dataclass."""

    def test_creation(self):
        """Test basic metric value creation."""
        metric = MetricValue(
            name="rx_optical_power",
            value=-12.5,
            instance_id="ots-1-1"
        )
        assert metric.name == "rx_optical_power"
        assert metric.value == -12.5
        assert metric.instance_id == "ots-1-1"

    def test_with_labels(self):
        """Test metric with labels."""
        metric = MetricValue(
            name="temperature",
            value=28.5,
            labels={"shelf_id": "1", "slot_id": "2"}
        )
        assert metric.labels["shelf_id"] == "1"


class TestTransformValue:
    """Tests for value transformation."""

    def test_string_to_number(self):
        """Test string to number conversion."""
        parser = XmlParser()
        result = parser._transform_value("12.5")
        assert result == 12.5

    def test_string_map_transform(self):
        """Test string map transformation."""
        parser = XmlParser()
        string_map = {"up": 1, "down": 0}
        result = parser._transform_value("up", string_map=string_map)
        assert result == 1.0

    def test_unknown_string_defaults_to_zero(self):
        """Test unknown string defaults to 0."""
        parser = XmlParser()
        string_map = {"up": 1, "down": 0}
        result = parser._transform_value("unknown", string_map=string_map)
        assert result == 0.0

    def test_invalid_value_returns_none(self):
        """Test invalid value returns None."""
        parser = XmlParser()
        result = parser._transform_value("not a number")
        assert result is None


class TestFallbackInstanceId:
    """Tests for fallback instance ID logic."""

    def test_fallback_to_interface_name(self):
        """Test fallback to interface name when alias-name is missing."""
        xml_str = """
        <data xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
          <ne xmlns="http://coriant.com/yang/os/ne">
            <services>
              <optical-interfaces>
                <ots>
                  <ots-name>OTS-1-1-1</ots-name>
                  <admin-status>up</admin-status>
                  <oper-status>up</oper-status>
                </ots>
              </optical-interfaces>
            </services>
          </ne>
        </data>
        """
        data = etree.fromstring(xml_str.encode())

        config = {
            "namespaces": {
                "ne": "http://coriant.com/yang/os/ne",
            },
            "interfaces": {
                "ots": {
                    "xpath": ".//ots",
                    "instance_key": "alias-name",
                    "fallback_id_key": "ots-name",
                    "instance_name_key": "alias-name",
                    "description_key": "ots-name",
                    "metrics": [
                        {
                            "name": "admin_status",
                            "xpath": "admin-status",
                            "string_map": {"down": 0, "up": 1}
                        }
                    ]
                }
            }
        }

        parser = XmlParser(namespaces=config["namespaces"])
        instances = parser.discover_instances(data, config)

        # Should find instance using fallback ots-name
        assert len(instances) == 1
        assert instances[0].instance_id == "OTS-1-1-1"

    def test_prefer_alias_name_over_fallback(self):
        """Test that alias-name is preferred over fallback when both exist."""
        xml_str = """
        <data xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
          <ne xmlns="http://coriant.com/yang/os/ne">
            <services>
              <optical-interfaces>
                <ots>
                  <ots-name>OTS-1-1-1</ots-name>
                  <alias-name>Line-East-OTS</alias-name>
                  <admin-status>up</admin-status>
                </ots>
              </optical-interfaces>
            </services>
          </ne>
        </data>
        """
        data = etree.fromstring(xml_str.encode())

        config = {
            "namespaces": {
                "ne": "http://coriant.com/yang/os/ne",
            },
            "interfaces": {
                "ots": {
                    "xpath": ".//ots",
                    "instance_key": "alias-name",
                    "fallback_id_key": "ots-name",
                    "instance_name_key": "alias-name",
                    "description_key": "ots-name",
                    "metrics": []
                }
            }
        }

        parser = XmlParser(namespaces=config["namespaces"])
        instances = parser.discover_instances(data, config)

        # Should use alias-name, not ots-name
        assert len(instances) == 1
        assert instances[0].instance_id == "Line-East-OTS"
