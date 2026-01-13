"""
Tests for NETCONF client module.

These tests use mocking since we can't connect to real devices in unit tests.
"""

from unittest.mock import Mock, patch

import pytest
from lxml import etree

from lmn_tools.collectors.optical.client import (
    NetconfClient,
    NetconfClientError,
    NetconfConnectionError,
    create_client_from_args,
)


class TestNetconfClientInit:
    """Tests for NetconfClient initialization."""

    def test_basic_init(self):
        """Test basic client initialization."""
        client = NetconfClient(
            hostname="device.example.com",
            username="admin",
            password="password123"
        )
        assert client.hostname == "device.example.com"
        assert client.username == "admin"
        assert client.password == "password123"
        assert client.port == 830  # Default
        assert client.timeout == 60  # Default

    def test_custom_port(self):
        """Test client with custom port."""
        client = NetconfClient(
            hostname="device.example.com",
            username="admin",
            password="password123",
            port=22830
        )
        assert client.port == 22830

    def test_custom_timeout(self):
        """Test client with custom timeout."""
        client = NetconfClient(
            hostname="device.example.com",
            username="admin",
            password="password123",
            timeout=120
        )
        assert client.timeout == 120

    def test_device_type(self):
        """Test client with device type."""
        client = NetconfClient(
            hostname="device.example.com",
            username="admin",
            password="password123",
            device_type="coriant"
        )
        assert client.device_type == "coriant"

    def test_not_connected_initially(self):
        """Test client is not connected initially."""
        client = NetconfClient(
            hostname="device.example.com",
            username="admin",
            password="password123"
        )
        assert not client.connected
        assert client.capabilities == []


class TestNetconfClientConnection:
    """Tests for NETCONF connection handling."""

    @patch('ncclient.manager')
    def test_connect_success(self, mock_manager_module):
        """Test successful connection."""
        mock_manager = Mock()
        mock_manager.server_capabilities = ["cap1", "cap2"]
        mock_manager_module.connect.return_value = mock_manager

        client = NetconfClient(
            hostname="device.example.com",
            username="admin",
            password="password123"
        )
        client.connect()

        assert client.connected
        assert len(client.capabilities) == 2
        mock_manager_module.connect.assert_called_once()

    @patch('ncclient.manager')
    def test_connect_auth_failure(self, mock_manager_module):
        """Test connection with authentication failure."""
        from ncclient.transport.errors import AuthenticationError

        mock_manager_module.connect.side_effect = AuthenticationError("Auth failed")

        client = NetconfClient(
            hostname="device.example.com",
            username="admin",
            password="wrongpassword"
        )

        with pytest.raises(NetconfConnectionError) as excinfo:
            client.connect()

        assert "Authentication failed" in str(excinfo.value)

    @patch('ncclient.manager')
    def test_connect_ssh_failure(self, mock_manager_module):
        """Test connection with SSH failure."""
        from ncclient.transport.errors import SSHError

        mock_manager_module.connect.side_effect = SSHError("SSH failed")

        client = NetconfClient(
            hostname="unreachable.example.com",
            username="admin",
            password="password123"
        )

        with pytest.raises(NetconfConnectionError) as excinfo:
            client.connect()

        assert "SSH connection failed" in str(excinfo.value)

    @patch('ncclient.manager')
    def test_disconnect(self, mock_manager_module):
        """Test disconnect."""
        mock_manager = Mock()
        mock_manager.server_capabilities = []
        mock_manager_module.connect.return_value = mock_manager

        client = NetconfClient(
            hostname="device.example.com",
            username="admin",
            password="password123"
        )
        client.connect()
        client.disconnect()

        assert not client.connected
        mock_manager.close_session.assert_called_once()


class TestNetconfClientContextManager:
    """Tests for context manager functionality."""

    @patch('ncclient.manager')
    def test_context_manager(self, mock_manager_module):
        """Test using client as context manager."""
        mock_manager = Mock()
        mock_manager.server_capabilities = []
        mock_manager_module.connect.return_value = mock_manager

        with NetconfClient(
            hostname="device.example.com",
            username="admin",
            password="password123"
        ) as client:
            assert client.connected

        # Should be disconnected after context exits
        mock_manager.close_session.assert_called_once()


class TestNetconfClientRPC:
    """Tests for RPC operations."""

    @patch('ncclient.manager')
    def test_get_operation(self, mock_manager_module):
        """Test get RPC operation."""
        # Setup mock response
        mock_response = Mock()
        mock_response.data_ele = etree.fromstring(b"<data><ne/></data>")

        mock_manager = Mock()
        mock_manager.server_capabilities = []
        mock_manager.get.return_value = mock_response
        mock_manager_module.connect.return_value = mock_manager

        client = NetconfClient(
            hostname="device.example.com",
            username="admin",
            password="password123"
        )
        client.connect()

        result = client.get("<filter/>")

        assert result is not None
        mock_manager.get.assert_called_once()

    def test_get_without_connection(self):
        """Test get RPC without connection raises error."""
        client = NetconfClient(
            hostname="device.example.com",
            username="admin",
            password="password123"
        )

        with pytest.raises(NetconfClientError) as excinfo:
            client.get("<filter/>")

        assert "Not connected" in str(excinfo.value)


class TestBuildFilter:
    """Tests for filter building functionality."""

    def test_build_filter_removes_attributes(self):
        """Test that non-xmlns attributes are removed from filter."""
        client = NetconfClient(
            hostname="device.example.com",
            username="admin",
            password="password123"
        )

        config_xml = """
        <ne xmlns="http://example.com" class="metric" type="Gauge">
            <element class="label" help="test"/>
        </ne>
        """
        filter_elem = client.build_filter(config_xml)

        # Check that class, type, help attributes are removed
        assert "class" not in filter_elem.attrib
        assert "type" not in filter_elem.attrib

        # Check xmlns is preserved
        assert "{http://example.com}" in filter_elem.tag or "xmlns" in str(etree.tostring(filter_elem))

    def test_build_filter_preserves_xmlns(self):
        """Test that xmlns attributes are preserved."""
        client = NetconfClient(
            hostname="device.example.com",
            username="admin",
            password="password123"
        )

        config_xml = '<ne xmlns="http://coriant.com/yang/os/ne"/>'
        filter_elem = client.build_filter(config_xml)

        # xmlns should be preserved
        xml_str = etree.tostring(filter_elem, encoding='unicode')
        assert "xmlns" in xml_str or "{http://coriant.com/yang/os/ne}" in filter_elem.tag


class TestDetectDeviceType:
    """Tests for device type detection."""

    @patch('ncclient.manager')
    def test_detect_coriant(self, mock_manager_module):
        """Test detecting Coriant device."""
        mock_manager = Mock()
        mock_manager.server_capabilities = [
            "http://coriant.com/yang/os/ne",
            "urn:ietf:params:netconf:base:1.1"
        ]
        mock_manager_module.connect.return_value = mock_manager

        client = NetconfClient(
            hostname="device.example.com",
            username="admin",
            password="password123"
        )
        client.connect()

        device_type = client.detect_device_type()
        assert device_type == "coriant"

    @patch('ncclient.manager')
    def test_detect_ciena(self, mock_manager_module):
        """Test detecting Ciena device."""
        mock_manager = Mock()
        mock_manager.server_capabilities = [
            "urn:ciena:params:xml:ns:yang:ciena-ws-ptp",
            "urn:ietf:params:netconf:base:1.1"
        ]
        mock_manager_module.connect.return_value = mock_manager

        client = NetconfClient(
            hostname="device.example.com",
            username="admin",
            password="password123"
        )
        client.connect()

        device_type = client.detect_device_type()
        assert device_type == "ciena"

    @patch('ncclient.manager')
    def test_detect_unknown(self, mock_manager_module):
        """Test detecting unknown device type."""
        mock_manager = Mock()
        mock_manager.server_capabilities = [
            "urn:ietf:params:netconf:base:1.1"
        ]
        mock_manager_module.connect.return_value = mock_manager

        client = NetconfClient(
            hostname="device.example.com",
            username="admin",
            password="password123"
        )
        client.connect()

        device_type = client.detect_device_type()
        assert device_type is None


class TestCreateClientFromArgs:
    """Tests for create_client_from_args helper."""

    def test_create_from_args(self):
        """Test creating client from argparse namespace."""
        from argparse import Namespace

        args = Namespace(
            hostname="device.example.com",
            username="admin",
            password="password123",
            port=830,
            timeout=60,
            debug=False
        )

        client = create_client_from_args(args)

        assert client.hostname == "device.example.com"
        assert client.username == "admin"
        assert client.password == "password123"
        assert client.port == 830

    def test_create_with_missing_optional_args(self):
        """Test creating client with missing optional args."""
        from argparse import Namespace

        args = Namespace(
            hostname="device.example.com",
            username="admin",
            password="password123"
            # port, timeout, debug not set
        )

        client = create_client_from_args(args)

        assert client.hostname == "device.example.com"
        # Should use defaults
        assert client.port == NetconfClient.DEFAULT_PORT
        assert client.timeout == NetconfClient.DEFAULT_TIMEOUT
