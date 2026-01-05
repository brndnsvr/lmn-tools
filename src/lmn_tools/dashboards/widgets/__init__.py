"""
Widget builders for LogicMonitor dashboards.

This package contains modular widget builders organized by type:
- common: Shared constants, utilities, and WidgetPosition class
- text_widgets: Text/HTML widgets (headers, section headers)
- noc_widgets: NOC-type widgets (interface tables, BGP tables)
- traffic_graphs: Traffic graphs (bandwidth, packets)
- dom_graphs: DOM optics graphs
- dynamic_tables: dynamicTable widgets (BGP statistics)
- alerts: NOC alert widgets (resource alerts, interface alerts, errors/discards)
"""

# Common utilities and classes
from .common import (
    WidgetPosition,
    GRID_COLUMNS,
    DEFAULT_WIDGET_WIDTH,
    DEFAULT_GRAPH_HEIGHT,
    DEFAULT_TABLE_HEIGHT,
    DEFAULT_TEXT_HEIGHT,
    INTERFACE_COLORS,
    get_interface_type,
)

# Text widgets
from .text_widgets import (
    create_text_widget,
    create_header_widget,
    create_section_header,
    create_noc_header_widget,
)

# NOC widgets
from .noc_widgets import (
    create_interface_table_widget,
    create_bgp_table_widget,
)

# Traffic graphs
from .traffic_graphs import (
    create_traffic_graph_widget,
    create_consolidated_traffic_graph,
    create_consolidated_packet_graph,
    build_traffic_graphs_by_type,
    build_traffic_graphs_by_device,
)

# DOM graphs
from .dom_graphs import (
    create_dom_graph_widget,
    create_dom_optical_power_graph,
    build_dom_graphs,
)

# Dynamic tables
from .dynamic_tables import (
    create_bgp_statistics_widget,
)

# Alert widgets
from .alerts import (
    create_resource_alerts_widget,
    create_interface_alerts_widget,
    create_errors_discards_table,
    create_discard_percentage_graph,
)

__all__ = [
    # Common
    'WidgetPosition',
    'GRID_COLUMNS',
    'DEFAULT_WIDGET_WIDTH',
    'DEFAULT_GRAPH_HEIGHT',
    'DEFAULT_TABLE_HEIGHT',
    'DEFAULT_TEXT_HEIGHT',
    'INTERFACE_COLORS',
    'get_interface_type',
    # Text widgets
    'create_text_widget',
    'create_header_widget',
    'create_section_header',
    'create_noc_header_widget',
    # NOC widgets
    'create_interface_table_widget',
    'create_bgp_table_widget',
    # Traffic graphs
    'create_traffic_graph_widget',
    'create_consolidated_traffic_graph',
    'create_consolidated_packet_graph',
    'build_traffic_graphs_by_type',
    'build_traffic_graphs_by_device',
    # DOM graphs
    'create_dom_graph_widget',
    'create_dom_optical_power_graph',
    'build_dom_graphs',
    # Dynamic tables
    'create_bgp_statistics_widget',
    # Alert widgets
    'create_resource_alerts_widget',
    'create_interface_alerts_widget',
    'create_errors_discards_table',
    'create_discard_percentage_graph',
]
