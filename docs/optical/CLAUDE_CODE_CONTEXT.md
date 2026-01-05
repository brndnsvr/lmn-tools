# Claude Code Context

This document provides context for continuing development with Claude Code or similar AI coding assistants.

## Project Summary

NETCONF-based optical device monitoring for LogicMonitor. Replaces a Prometheus exporter with collector-side scripts that output LogicMonitor-compatible formats.

---

## What's Complete

### Phase 1-3: Core Implementation
- Coriant discovery, collection, and chassis scripts
- Ciena discovery, collection, and chassis scripts
- YAML-based metric configuration
- Debug output for troubleshooting
- LogicMonitor DataSource XML templates

### Validated
- Coriant scripts tested against real device (10.62.4.125)
- Output formats confirmed correct for LogicMonitor

### Not Yet Validated
- Ciena scripts (no lab device access yet)
- LogicMonitor end-to-end integration
- Forward slash (/) in instance IDs within LM

---

## Key Files

| File | Purpose |
|------|---------|
| `configs/coriant.yaml` | Coriant interface metric definitions |
| `configs/coriant_chassis.yaml` | Coriant chassis metric definitions |
| `configs/ciena.yaml` | Ciena PTP/Port metric definitions |
| `configs/ciena_chassis.yaml` | Ciena chassis metric definitions |
| `src/xml_parser.py` | Core parsing logic with XPath |
| `src/netconf_client.py` | NETCONF connection handling |
| `src/output_formatter.py` | LogicMonitor output formatting |
| `src/utils.py` | Sanitization, type conversion |
| `scripts/*.py` | Entry points for LogicMonitor |
| `logicmonitor/*.xml` | Importable DataSource templates |

---

## Common Tasks

### Adding a Metric

1. Edit `configs/{vendor}.yaml`
2. Add metric under appropriate interface type:
   ```yaml
   metrics:
     - name: new_metric_name
       xpath: "path/to/element"
       help: "Description of metric"
       string_map:  # Optional
         disabled: 0
         enabled: 1
   ```
3. Update NETCONF filter to request the element
4. Test with `--debug` flag
5. Update DataSource template if needed

### Fixing XPath Issues

1. Run script with `--debug` to see raw XML response
2. Find correct element path in the XML
3. Update xpath in YAML config
4. Re-test with `--debug`

Common XPath patterns:
- `.//element-name` - Find anywhere in document
- `child-element/grandchild` - Relative path from parent
- `*[local-name()='element']` - Namespace-agnostic matching

### Adding New Vendor

1. Create `configs/newvendor.yaml` with:
   - Device type and vendor name
   - Namespaces
   - NETCONF filter
   - Interface definitions with metrics
2. Create scripts:
   - `scripts/newvendor_discover.py`
   - `scripts/newvendor_collect.py`
   - `scripts/newvendor_chassis_collect.py` (optional)
3. Add device type to `NetconfClient.DEVICE_TYPES` if needed
4. Create test fixtures in `tests/fixtures/`
5. Create LogicMonitor templates in `logicmonitor/`

---

## Reference Material

The `reference/` directory contains the original Prometheus exporter code. Useful for understanding NETCONF patterns but not used at runtime.

Key reference files:
- `reference/app/config/coriant-interfaces.xml` - Coriant interface structure
- `reference/app/config/ciena-waveserver-ptps.xml` - Ciena PTP structure

---

## Validated Test Output

### Discovery (coriant_discover.py)
```
ots-1/3.1/1##ots-1/3.1/1##1/3.1/1####auto.fiber_type=SSMF&auto.interface_type=ots
oms-1/3.1/1##oms-1/3.1/1##1/3.1/1####auto.grid_mode=fixed_100G_48ch&auto.interface_type=oms
osc-1/3.1/1##osc-1/3.1/1##1/3.1/1####auto.osc_mode=155M52&auto.interface_type=osc
gopt-1/3.1/2##gopt-1/3.1/2##1/3.1/2####auto.interface_type=gopt
```

### Collection (coriant_collect.py)
```
ots-1/3.1/1.admin_status=1.0
ots-1/3.1/1.oper_status=0.0
ots-1/3.1/1.fiber_length_tx_derived=107.619
oms-1/3.1/1.rx_optical_power=-48.3
oms-1/3.1/1.tx_optical_power=-40.2
```

### Chassis (coriant_chassis_collect.py)
```
ne_temperature=18.3
ne_altitude=0.0
swload_active=1
```

---

## Questions to Answer

- Does forward slash (/) work in LM instance IDs?
- What alert thresholds are appropriate for production?
- Are there additional metrics needed beyond current set?

---

## Architecture Overview

```
LogicMonitor          Collector           Optical Device
    │                     │                     │
    │ triggers script     │                     │
    │────────────────────▶│                     │
    │                     │ NETCONF <get>       │
    │                     │────────────────────▶│
    │                     │                     │
    │                     │◀────────────────────│
    │                     │ XML response        │
    │◀────────────────────│                     │
    │ formatted output    │                     │
```

---

## Testing

```bash
# Run unit tests
pytest tests/ -v

# Test against real device
python scripts/coriant_discover.py <host> <user> <pass> --debug
python scripts/coriant_collect.py <host> <user> <pass> --debug
python scripts/coriant_chassis_collect.py <host> <user> <pass> --debug
```

---

## Known Edge Cases

1. **Null timestamps**: "0000-01-01T00:00:00.000Z" means unset - silently skipped
2. **-99 dBm**: Indicates "no signal" - not an error
3. **Empty alias-name**: Falls back to interface-name for instance ID
4. **Namespace variations**: Parser uses multiple fallback strategies
