# lmn-tools

Unified CLI for LogicMonitor operations.

## Installation

```bash
pip install lmn-tools

# With NETCONF support (for optical/transport devices)
pip install lmn-tools[netconf]

# With SNMP support
pip install lmn-tools[snmp]

# All features
pip install lmn-tools[all]
```

## Configuration

Set environment variables for LogicMonitor API access:

```bash
export LM_COMPANY=yourcompany
export LM_ACCESS_ID=your-access-id
export LM_ACCESS_KEY=your-access-key
```

Or use `lmn config` to manage credentials.

## Usage

```bash
lmn --help
```

### Commands

| Command | Description |
|---------|-------------|
| `config` | Manage lmn configuration |
| `discover` | Run Active Discovery on devices (NETCONF/SNMP) |
| `collect` | Collect metrics from devices |
| `device` | Manage devices |
| `group` | Manage device groups |
| `datasource` | Manage DataSources (alias: `ds`) |
| `propertysource` | Manage PropertySources (alias: `ps`) |
| `eventsource` | Manage EventSources (alias: `es`) |
| `configsource` | Manage ConfigSources (alias: `cs`) |
| `topologysource` | Manage TopologySources (alias: `ts`) |
| `alert` | Manage alerts |
| `alertrule` | Manage alert rules (alias: `ar`) |
| `chain` | Manage escalation chains |
| `integration` | Manage integrations |
| `sdt` | Manage SDT (maintenance windows) |
| `collector` | View collectors |
| `dashboard` | Manage dashboards |
| `website` | Manage website monitors (synthetic) |
| `user` | View users (read-only) |
| `report` | View reports |
| `api` | Raw API access |

### Examples

```bash
# List devices
lmn device list

# Get device details
lmn device get 12345

# List datasources
lmn ds list

# Run NETCONF discovery
lmn discover netconf router1.example.com -u admin -c config.yaml

# Collect metrics via SNMP
lmn collect snmp switch1.example.com -c public

# Raw API access
lmn api get /device/devices --filter "displayName:*router*"
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src/
mypy src/
```

## Requirements

- Python 3.10+
- LogicMonitor API credentials

## License

MIT
