# Architecture

## Overview

This project provides NETCONF-based metric collection for optical transport devices, formatted for LogicMonitor ingestion.

## Supported Vendors

| Vendor | Device Types | Status |
|--------|--------------|--------|
| Coriant | Optical transport (OTS, OMS, OSC, GOPT) | ✅ Validated |
| Ciena | WaveServer (PTPs, Ports) | ⏳ Implemented, pending validation |

## Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  LogicMonitor   │     │    Collector    │     │ Optical Device  │
│    Platform     │     │   (Linux VM)    │     │ (Coriant/Ciena) │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│                 │     │                 │     │                 │
│ Triggers script │────▶│ Runs Python     │────▶│ NETCONF <get>   │
│ with device     │     │ script with     │     │ RPC over SSH    │
│ properties      │     │ host/user/pass  │     │ port 830        │
│                 │     │                 │     │                 │
│ Parses output   │◀────│ Outputs LM      │◀────│ Returns XML     │
│ stores metrics  │     │ formatted data  │     │ response        │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Detailed Flow

```
1. Script loads YAML config
       │
       ▼
2. NetconfClient connects to device (SSH port 830)
       │
       ▼
3. NETCONF subtree filter sent (from config)
       │
       ▼
4. XML response received from device
       │
       ▼
5. XmlParser extracts instances/metrics using XPath
       │
       ▼
6. OutputFormatter writes to stdout
       │
       ▼
7. LogicMonitor ingests data
```

---

## Design Decisions

### BATCHSCRIPT Mode
- Single NETCONF session per device per collection
- Efficient for devices with many interfaces
- Script outputs all instances in one run
- Reduces connection overhead vs per-instance collection

### Separate Chassis DataSource
- Chassis metrics are single-instance (one per device)
- Allows different collection intervals
- Cleaner separation of concerns
- Uses SCRIPT mode (not BATCHSCRIPT)

### YAML Configuration
- Metrics defined in YAML, not hardcoded
- Easy to add/modify metrics without code changes
- Embedded NETCONF filter XML
- String maps for converting state values to numbers

### Module Separation

| Module | Purpose |
|--------|---------|
| `netconf_client.py` | Connection handling, session management |
| `xml_parser.py` | Response parsing, XPath queries |
| `output_formatter.py` | LM output formatting |
| `debug_helper.py` | Troubleshooting output |
| `utils.py` | Sanitization, type conversion |

---

## Component Architecture

### Core Library (`src/`)

```
src/
├── netconf_client.py    # NETCONF connection management
├── xml_parser.py        # XML parsing and metric extraction
├── output_formatter.py  # LogicMonitor output formatting
├── debug_helper.py      # Debug output utilities
└── utils.py             # String sanitization, type conversion
```

### NetconfClient

Context manager for NETCONF sessions.

```python
with NetconfClient(hostname, username, password, port=830) as client:
    data = client.get(filter_xml)
```

**Features:**
- Automatic connection/disconnection
- Device type hints (coriant, ciena)
- Host key verification control
- Enhanced error messages with troubleshooting hints
- Debug output integration

### XmlParser

Extracts instances and metrics from NETCONF XML responses.

```python
parser = XmlParser(namespaces=config['namespaces'], debug=True)
instances = parser.discover_instances(data, config)
metrics = parser.collect_metrics(data, config)
```

**XPath Resolution Strategy:**
1. Try XPath with explicit namespaces
2. Try local-name() based XPath
3. Fall back to manual tree walking

### OutputFormatter

Formats data for LogicMonitor ingestion.

```python
formatter = OutputFormatter()
formatter.write_discovery(instances)  # Active Discovery format
formatter.write_collection(metrics)   # BATCHSCRIPT format
```

---

## LogicMonitor DataSources

| DataSource | Vendor | Type | Scripts |
|------------|--------|------|---------|
| Coriant_Optical_Interfaces | Coriant | BATCHSCRIPT | discover + collect |
| Coriant_Chassis | Coriant | SCRIPT | collect only |
| Ciena_WaveServer_Interfaces | Ciena | BATCHSCRIPT | discover + collect |
| Ciena_WaveServer_Chassis | Ciena | SCRIPT | collect only |

---

## Output Formats

### Active Discovery
```
instance_id##instance_name##description####auto.prop1=val1&auto.prop2=val2
```

### BATCHSCRIPT Collection
```
instance_id.datapoint_name=numeric_value
```

### Single-Instance Collection
```
datapoint_name=numeric_value
```

---

## Configuration Schema

### Interface Configuration (`configs/*.yaml`)

```yaml
# Device identification
device_type: coriant|ciena
vendor: Coriant|Ciena

# XML namespaces for XPath
namespaces:
  ne: "http://coriant.com/yang/os/ne"

# NETCONF subtree filter
netconf_filter: |
  <ne xmlns="http://coriant.com/yang/os/ne">
    <element-to-request/>
  </ne>

# Interface definitions
interfaces:
  interface_type:
    xpath: ".//element-name"           # XPath to find interfaces
    instance_key: "alias-name"          # Primary instance ID element
    fallback_id_key: "interface-name"   # Fallback if primary empty
    properties:                          # auto.* properties
      - fiber-type
    metrics:
      - name: metric_name
        xpath: "child/element"
        string_map:
          disabled: 0
          enabled: 1
```

---

## Instance ID Handling

### ID Resolution Order
1. **Primary key** (`instance_key`): Usually `alias-name` for user-defined names
2. **Fallback key** (`fallback_id_key`): Usually `{type}-name` (e.g., `ots-name`)

### ID Sanitization
Instance IDs are sanitized to remove invalid characters:
- `:` → `-`
- `#` → `-`
- `\` → `-`
- ` ` → `_`

---

## Error Handling

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success (data on stdout, may be empty) |
| 1 | Error (message on stderr) |

### Output Streams
- **stdout**: Data only (discovery/collection output)
- **stderr**: Errors, warnings, debug output

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Test Fixtures

XML files representing device responses:
- `coriant_response.xml` - Sample Coriant NETCONF response
- `ciena_ptp_response.xml` - Sample Ciena PTP/Port response
- `ciena_chassis_response.xml` - Sample Ciena chassis response

---

## Extending the System

### Adding a New Vendor

1. Create config: `configs/newvendor.yaml`
2. Add device params to `NetconfClient.DEVICE_TYPES`
3. Create scripts in `scripts/`
4. Add test fixtures
5. Create LogicMonitor templates

### Adding Metrics

1. Update YAML config with new metric definition
2. Update NETCONF filter to request the element
3. Add/update test fixtures
4. Update LogicMonitor DataSource template
