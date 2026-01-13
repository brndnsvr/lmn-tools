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
# Alert widgets
from .alerts import (
    create_discard_percentage_graph,
    create_errors_discards_table,
    create_interface_alerts_widget,
    create_resource_alerts_widget,
)
from .common import (
    DEFAULT_GRAPH_HEIGHT,
    DEFAULT_TABLE_HEIGHT,
    DEFAULT_TEXT_HEIGHT,
    DEFAULT_WIDGET_WIDTH,
    GRID_COLUMNS,
    INTERFACE_COLORS,
    WidgetPosition,
    get_interface_type,
)

# DOM graphs
from .dom_graphs import (
    build_dom_graphs,
    create_dom_graph_widget,
    create_dom_optical_power_graph,
)

# Dynamic tables
from .dynamic_tables import (
    create_bgp_statistics_widget,
)

# NOC widgets
from .noc_widgets import (
    create_bgp_table_widget,
    create_interface_table_widget,
)

# Text widgets
from .text_widgets import (
    create_header_widget,
    create_noc_header_widget,
    create_section_header,
    create_text_widget,
)

# Traffic graphs
from .traffic_graphs import (
    build_traffic_graphs_by_device,
    build_traffic_graphs_by_type,
    create_consolidated_packet_graph,
    create_consolidated_traffic_graph,
    create_traffic_graph_widget,
)

__all__ = [
    'DEFAULT_GRAPH_HEIGHT',
    'DEFAULT_TABLE_HEIGHT',
    'DEFAULT_TEXT_HEIGHT',
    'DEFAULT_WIDGET_WIDTH',
    'GRID_COLUMNS',
    'INTERFACE_COLORS',
    # Common
    'WidgetPosition',
    'build_dom_graphs',
    'build_traffic_graphs_by_device',
    'build_traffic_graphs_by_type',
    # Dynamic tables
    'create_bgp_statistics_widget',
    'create_bgp_table_widget',
    'create_consolidated_packet_graph',
    'create_consolidated_traffic_graph',
    'create_discard_percentage_graph',
    # DOM graphs
    'create_dom_graph_widget',
    'create_dom_optical_power_graph',
    'create_errors_discards_table',
    'create_header_widget',
    'create_interface_alerts_widget',
    # NOC widgets
    'create_interface_table_widget',
    'create_noc_header_widget',
    # Alert widgets
    'create_resource_alerts_widget',
    'create_section_header',
    # Text widgets
    'create_text_widget',
    # Traffic graphs
    'create_traffic_graph_widget',
    'get_interface_type',
]
