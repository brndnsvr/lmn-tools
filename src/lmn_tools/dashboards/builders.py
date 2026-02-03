"""
Widget builders for LogicMonitor dashboards.

This module re-exports all widget functions from the widgets/ submodule
for backwards compatibility. New code can import directly from
includes.widgets.<module> for more targeted imports.

Widget types:
- Text/HTML widgets (headers, section headers)
- NOC widgets (interface tables, BGP tables)
- Traffic graphs (bandwidth, packets)
- DOM optics graphs
- Dynamic tables (BGP statistics)
- Alert widgets (resource alerts, interface alerts, errors/discards)
"""

# Re-export everything from the widgets submodule
from .widgets import (
    DEFAULT_GRAPH_HEIGHT,
    DEFAULT_TABLE_HEIGHT,
    DEFAULT_TEXT_HEIGHT,
    DEFAULT_WIDGET_WIDTH,
    GRID_COLUMNS,
    INTERFACE_COLORS,
    # Common utilities and classes
    WidgetPosition,
    build_dom_graphs,
    build_traffic_graphs_by_device,
    build_traffic_graphs_by_type,
    # Dynamic tables
    create_bgp_statistics_widget,
    create_bgp_table_widget,
    create_consolidated_packet_graph,
    create_consolidated_traffic_graph,
    create_discard_percentage_graph,
    # DOM graphs
    create_dom_graph_widget,
    create_dom_optical_power_graph,
    create_errors_discards_table,
    create_header_widget,
    create_interface_alerts_widget,
    # NOC widgets
    create_interface_table_widget,
    create_noc_header_widget,
    # Alert widgets
    create_resource_alerts_widget,
    create_section_header,
    # Text widgets
    create_text_widget,
    # Traffic graphs
    create_traffic_graph_widget,
    get_interface_type,
)

__all__ = [
    "DEFAULT_GRAPH_HEIGHT",
    "DEFAULT_TABLE_HEIGHT",
    "DEFAULT_TEXT_HEIGHT",
    "DEFAULT_WIDGET_WIDTH",
    "GRID_COLUMNS",
    "INTERFACE_COLORS",
    # Common
    "WidgetPosition",
    "build_dom_graphs",
    "build_traffic_graphs_by_device",
    "build_traffic_graphs_by_type",
    # Dynamic tables
    "create_bgp_statistics_widget",
    "create_bgp_table_widget",
    "create_consolidated_packet_graph",
    "create_consolidated_traffic_graph",
    "create_discard_percentage_graph",
    # DOM graphs
    "create_dom_graph_widget",
    "create_dom_optical_power_graph",
    "create_errors_discards_table",
    "create_header_widget",
    "create_interface_alerts_widget",
    # NOC widgets
    "create_interface_table_widget",
    "create_noc_header_widget",
    # Alert widgets
    "create_resource_alerts_widget",
    "create_section_header",
    # Text widgets
    "create_text_widget",
    # Traffic graphs
    "create_traffic_graph_widget",
    "get_interface_type",
]
