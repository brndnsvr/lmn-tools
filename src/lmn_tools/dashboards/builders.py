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
    # Common utilities and classes
    WidgetPosition,
    GRID_COLUMNS,
    DEFAULT_WIDGET_WIDTH,
    DEFAULT_GRAPH_HEIGHT,
    DEFAULT_TABLE_HEIGHT,
    DEFAULT_TEXT_HEIGHT,
    INTERFACE_COLORS,
    get_interface_type,
    # Text widgets
    create_text_widget,
    create_header_widget,
    create_section_header,
    create_noc_header_widget,
    # NOC widgets
    create_interface_table_widget,
    create_bgp_table_widget,
    # Traffic graphs
    create_traffic_graph_widget,
    create_consolidated_traffic_graph,
    create_consolidated_packet_graph,
    build_traffic_graphs_by_type,
    build_traffic_graphs_by_device,
    # DOM graphs
    create_dom_graph_widget,
    create_dom_optical_power_graph,
    build_dom_graphs,
    # Dynamic tables
    create_bgp_statistics_widget,
    # Alert widgets
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
