"""
Tests for utility functions.
"""

import pytest
from src.utils import (
    sanitize_instance_id,
    sanitize_metric_name,
    apply_string_map,
    parse_string_map_definition,
    parse_timestamp,
    safe_float,
    safe_int,
    get_local_name,
    extract_element_text,
)


class TestSanitizeInstanceId:
    """Tests for sanitize_instance_id function."""

    def test_basic_sanitization(self):
        """Test basic character replacement."""
        assert sanitize_instance_id("port:1-1") == "port_1-1"
        assert sanitize_instance_id("slot#1") == "slot_1"
        assert sanitize_instance_id("interface 1") == "interface_1"
        assert sanitize_instance_id("path\\to\\port") == "path_to_port"

    def test_multiple_special_chars(self):
        """Test multiple special characters."""
        assert sanitize_instance_id("port:1#2 3") == "port_1_2_3"

    def test_collapse_underscores(self):
        """Test that multiple underscores are collapsed."""
        assert sanitize_instance_id("port::1") == "port_1"
        assert sanitize_instance_id("port  1") == "port_1"

    def test_strip_underscores(self):
        """Test that leading/trailing underscores are stripped."""
        assert sanitize_instance_id(":port") == "port"
        assert sanitize_instance_id("port:") == "port"

    def test_empty_input(self):
        """Test empty input."""
        assert sanitize_instance_id("") == ""
        assert sanitize_instance_id(None) == ""

    def test_valid_input(self):
        """Test that valid input passes through."""
        assert sanitize_instance_id("ots-1-1") == "ots-1-1"
        assert sanitize_instance_id("Line_East_OTS") == "Line_East_OTS"


class TestSanitizeMetricName:
    """Tests for sanitize_metric_name function."""

    def test_namespace_removal(self):
        """Test XML namespace removal."""
        assert sanitize_metric_name("{http://example.com}tag") == "tag"
        assert sanitize_metric_name("ns:tag") == "tag"

    def test_lowercase(self):
        """Test conversion to lowercase."""
        assert sanitize_metric_name("MyTag") == "mytag"
        assert sanitize_metric_name("RX_POWER") == "rx_power"

    def test_special_char_replacement(self):
        """Test special character replacement."""
        assert sanitize_metric_name("rx-optical-power") == "rx_optical_power"
        assert sanitize_metric_name("admin.status") == "admin_status"

    def test_underscore_collapse(self):
        """Test underscore collapsing."""
        assert sanitize_metric_name("rx--power") == "rx_power"

    def test_empty_input(self):
        """Test empty input."""
        assert sanitize_metric_name("") == ""
        assert sanitize_metric_name(None) == ""


class TestApplyStringMap:
    """Tests for apply_string_map function."""

    def test_basic_mapping(self):
        """Test basic string mapping."""
        string_map = {"up": 1, "down": 0}
        assert apply_string_map("up", string_map) == 1
        assert apply_string_map("down", string_map) == 0

    def test_default_value(self):
        """Test default value for unmapped strings."""
        string_map = {"up": 1, "down": 0}
        assert apply_string_map("unknown", string_map) == 0
        assert apply_string_map("unknown", string_map, default=99) == 99

    def test_no_map(self):
        """Test behavior with no string map."""
        assert apply_string_map("up", None) == 0
        assert apply_string_map("up", None, default=5) == 5


class TestParseStringMapDefinition:
    """Tests for parse_string_map_definition function."""

    def test_basic_parsing(self):
        """Test basic string map parsing."""
        result = parse_string_map_definition("down:0,up:1")
        assert result == {"down": 0, "up": 1}

    def test_with_spaces(self):
        """Test parsing with spaces."""
        result = parse_string_map_definition("down: 0, up: 1")
        assert result == {"down": 0, "up": 1}

    def test_multiple_values(self):
        """Test parsing multiple values."""
        result = parse_string_map_definition("Inactive:0,Active:1,unknown:2")
        assert result == {"Inactive": 0, "Active": 1, "unknown": 2}

    def test_empty_string(self):
        """Test empty string."""
        assert parse_string_map_definition("") == {}
        assert parse_string_map_definition(None) == {}


class TestParseTimestamp:
    """Tests for parse_timestamp function."""

    def test_iso_format(self):
        """Test ISO 8601 format parsing."""
        result = parse_timestamp("2024-11-26T14:30:00Z")
        assert result is not None
        assert isinstance(result, float)

    def test_iso_with_timezone(self):
        """Test ISO format with timezone."""
        result = parse_timestamp("2024-11-26T14:30:00+00:00")
        assert result is not None

    def test_invalid_timestamp(self):
        """Test invalid timestamp returns None."""
        assert parse_timestamp("not a timestamp") is None
        assert parse_timestamp("") is None
        assert parse_timestamp(None) is None


class TestSafeFloat:
    """Tests for safe_float function."""

    def test_valid_float(self):
        """Test valid float conversion."""
        assert safe_float("12.5") == 12.5
        assert safe_float("-3.14") == -3.14
        assert safe_float("0") == 0.0

    def test_integer_string(self):
        """Test integer string conversion."""
        assert safe_float("42") == 42.0

    def test_invalid_returns_default(self):
        """Test invalid input returns default."""
        assert safe_float("not a number") is None
        assert safe_float("not a number", default=0.0) == 0.0
        assert safe_float(None) is None


class TestSafeInt:
    """Tests for safe_int function."""

    def test_valid_int(self):
        """Test valid int conversion."""
        assert safe_int("42") == 42
        assert safe_int("-10") == -10

    def test_float_string(self):
        """Test float string conversion to int."""
        assert safe_int("12.5") == 12
        assert safe_int("12.9") == 12  # Truncates, doesn't round

    def test_invalid_returns_default(self):
        """Test invalid input returns default."""
        assert safe_int("not a number") is None
        assert safe_int("not a number", default=0) == 0


class TestGetLocalName:
    """Tests for get_local_name function."""

    def test_with_namespace(self):
        """Test extracting local name from namespaced tag."""
        assert get_local_name("{http://example.com}tag") == "tag"

    def test_with_prefix(self):
        """Test extracting local name from prefixed tag."""
        assert get_local_name("ns:tag") == "tag"

    def test_plain_tag(self):
        """Test plain tag passes through."""
        assert get_local_name("tag") == "tag"


class TestExtractElementText:
    """Tests for extract_element_text function."""

    def test_none_element(self):
        """Test None element returns default."""
        assert extract_element_text(None) == ""
        assert extract_element_text(None, default="N/A") == "N/A"
