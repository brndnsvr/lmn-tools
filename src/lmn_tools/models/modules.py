"""
Pydantic models for LogicMonitor LogicModules.

Provides type-safe models for DataSources, PropertySources, and their components.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ModuleType(str, Enum):
    """LogicModule types."""

    DATASOURCE = "datasource"
    PROPERTYSOURCE = "propertysource"
    EVENTSOURCE = "eventsource"
    CONFIGSOURCE = "configsource"
    TOPOLOGYSOURCE = "topologysource"


class CollectMethod(str, Enum):
    """DataSource collection methods."""

    SCRIPT = "script"
    SNMP = "snmp"
    WEBSERVICE = "webservice"
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    PERFMON = "perfmon"
    WMI = "wmi"
    JDBC = "jdbc"
    JMXSCAN = "jmxscan"
    INTERNAL = "internal"
    BATCHSCRIPT = "batchscript"
    NETAPP = "netapp"
    NETAPPSCAN = "netappscan"
    XEN = "xen"
    ESX = "esx"
    ESXSCAN = "esxscan"


class DataPointAggregation(str, Enum):
    """Datapoint aggregation methods."""

    NONE = "none"
    PERCENTILE = "percentile"
    SUM = "sum"
    AVERAGE = "average"


class DataPointType(str, Enum):
    """Datapoint types."""

    GAUGE = "gauge"
    COUNTER = "counter"
    DERIVE = "derive"


class DataPoint(BaseModel):
    """A datapoint within a DataSource."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    description: str = ""
    alert_expr: str = Field("", alias="alertExpr")
    alert_subject: str = Field("", alias="alertSubject")
    alert_body: str = Field("", alias="alertBody")
    type: DataPointType | int = Field(DataPointType.GAUGE)
    post_processor_method: str = Field("", alias="postProcessorMethod")
    post_processor_param: str = Field("", alias="postProcessorParam")
    raw_data_field_name: str = Field("", alias="rawDataFieldName")
    max_value: str = Field("", alias="maxValue")
    min_value: str = Field("", alias="minValue")
    max_digits: int = Field(4, alias="maxDigits")
    user_param1: str = Field("", alias="userParam1")
    user_param2: str = Field("", alias="userParam2")
    user_param3: str = Field("", alias="userParam3")


class Graph(BaseModel):
    """A graph within a DataSource."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    title: str = ""
    vertical_label: str = Field("", alias="verticalLabel")
    rigid: bool = False
    max_value: float | None = Field(None, alias="maxValue")
    min_value: float | None = Field(None, alias="minValue")
    display_prio: int = Field(1, alias="displayPrio")
    time_scale: str = Field("1day", alias="timeScale")
    base_1024: bool = Field(False, alias="base1024")


class OverviewGraph(BaseModel):
    """An overview graph for a DataSource."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    title: str = ""
    vertical_label: str = Field("", alias="verticalLabel")
    display_prio: int = Field(1, alias="displayPrio")
    aggregated: bool = False


class DataSourceSummary(BaseModel):
    """Summary view of a DataSource (for list operations)."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    display_name: str = Field("", alias="displayName")
    group: str = ""
    applies_to: str = Field("", alias="appliesTo")
    collect_method: str = Field("", alias="collectMethod")
    has_multi_instances: bool = Field(False, alias="hasMultiInstances")
    collect_interval: int = Field(300, alias="collectInterval")
    version: int = 0


class DataSourceDetail(BaseModel):
    """Full DataSource with all fields."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    display_name: str = Field("", alias="displayName")
    group: str = ""
    description: str = ""
    applies_to: str = Field("", alias="appliesTo")
    collect_method: CollectMethod | str = Field(CollectMethod.SCRIPT, alias="collectMethod")
    has_multi_instances: bool = Field(False, alias="hasMultiInstances")
    collect_interval: int = Field(300, alias="collectInterval")
    technology: str = ""
    tags: str = ""
    version: int = 0
    checksum: str = ""

    # Embedded collections (may not always be present)
    data_points: list[DataPoint] = Field(default_factory=list, alias="dataPoints")
    graphs: list[Graph] = Field(default_factory=list)
    overview_graphs: list[OverviewGraph] = Field(default_factory=list, alias="overviewGraphs")


class PropertySourceSummary(BaseModel):
    """Summary view of a PropertySource."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    display_name: str = Field("", alias="displayName")
    group: str = ""
    applies_to: str = Field("", alias="appliesTo")
    technology: str = ""
    version: int = 0


class EventSourceSummary(BaseModel):
    """Summary view of an EventSource."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    display_name: str = Field("", alias="displayName")
    group: str = ""
    applies_to: str = Field("", alias="appliesTo")
    technology: str = ""
    version: int = 0


class ConfigSourceSummary(BaseModel):
    """Summary view of a ConfigSource."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    display_name: str = Field("", alias="displayName")
    group: str = ""
    applies_to: str = Field("", alias="appliesTo")
    technology: str = ""
    version: int = 0


class TopologySourceSummary(BaseModel):
    """Summary view of a TopologySource."""

    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    display_name: str = Field("", alias="displayName")
    group: str = ""
    applies_to: str = Field("", alias="appliesTo")
    version: int = 0


# Type alias for any LogicModule summary
LogicModuleSummary = (
    DataSourceSummary
    | PropertySourceSummary
    | EventSourceSummary
    | ConfigSourceSummary
    | TopologySourceSummary
)


def parse_module_summary(data: dict[str, Any], module_type: ModuleType) -> LogicModuleSummary:
    """
    Parse a module dictionary into the appropriate summary model.

    Args:
        data: Raw API response dictionary
        module_type: Type of module

    Returns:
        Typed summary model
    """
    match module_type:
        case ModuleType.DATASOURCE:
            return DataSourceSummary.model_validate(data)
        case ModuleType.PROPERTYSOURCE:
            return PropertySourceSummary.model_validate(data)
        case ModuleType.EVENTSOURCE:
            return EventSourceSummary.model_validate(data)
        case ModuleType.CONFIGSOURCE:
            return ConfigSourceSummary.model_validate(data)
        case ModuleType.TOPOLOGYSOURCE:
            return TopologySourceSummary.model_validate(data)
