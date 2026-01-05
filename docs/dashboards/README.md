# LogicMonitor Customer Dashboard Builder

A Python tool that creates or updates customer network overview dashboards in LogicMonitor based on YAML configuration files.

## Features

- **Idempotent operation**: Re-running for the same BAN updates the dashboard, not duplicates it
- **Interface statistics tables**: Throughput, utilization, errors, discards
- **Traffic graphs**: Per-interface InMbps/OutMbps graphs organized by device
- **DOM optics graphs**: Laser bias, temperature, Rx/Tx power for leaf interfaces
- **BGP peer tables**: State, prefix count, flap count (optional)
- **Dashboard tokens**: Uses `##BAN##` and `##CUSTOMER_NAME##` for easy cloning
- **Dry-run mode**: Preview changes without modifying LogicMonitor

## Requirements

- Python 3.9+
- LogicMonitor API credentials (access ID and access key)

## Installation

```bash
# Clone or copy the project
cd lm-dashboard-maker

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
python build_customer_dashboard.py \
  --config configs/ban_724636.yml \
  --company evoqedcs \
  --access-id YOUR_ACCESS_ID \
  --access-key YOUR_ACCESS_KEY
```

### Using Environment Variables

```bash
export LM_COMPANY=evoqedcs
export LM_ACCESS_ID=your_access_id
export LM_ACCESS_KEY=your_access_key

python build_customer_dashboard.py --config configs/ban_724636.yml
```

### Dry Run Mode

Preview what would be created without making changes:

```bash
python build_customer_dashboard.py \
  --config configs/ban_724636.yml \
  --dry-run
```

### Debug Mode

Enable verbose logging:

```bash
python build_customer_dashboard.py \
  --config configs/ban_724636.yml \
  --company evoqedcs \
  --access-id YOUR_ACCESS_ID \
  --access-key YOUR_ACCESS_KEY \
  --debug
```

## YAML Configuration Schema

```yaml
customer:
  ban: "724636"                    # Required: BAN number
  name: "Customer Name"            # Required: Customer display name
  metros:                          # Optional: List of metros
    - DFW

logicmonitor:
  dashboard_group: "Folder/Subfolder"  # Dashboard folder path
  interface_datasource: "SNMP_Network_Interfaces"  # Optional, has default
  dom_datasource: "Juniper_Junos_DOM"              # Optional, has default
  bgp_datasource: "Juniper_BGP_Peers"              # Optional, has default

devices:
  - hostname: "DEVICE_HOSTNAME"    # Must match LM displayName or sysname
    role: "router"                 # Device role (router, leaf, etc.)
    metro: "DFW"
    interfaces:
      - name: "ae100.3"            # Interface name in LM
        alias: "VLAN_DESC"         # Interface alias/description
        role: "ISP1-Transit"       # Interface role for organization
        include_in_traffic_graphs: true
        include_in_table: true
        dom: false                 # Set true for DOM optics graphs

bgp_peers:                         # Optional section
  - device: "DEVICE_HOSTNAME"
    neighbor_ip: "10.0.0.1"
    description: "Peer description"
```

## Project Structure

```
lm-dashboard-maker/
├── build_customer_dashboard.py  # Main CLI entry point
├── lm_client.py                 # LogicMonitor API client with HMAC auth
├── lm_helpers.py                # Helper functions for LM operations
├── widget_builders.py           # Widget creation functions
├── configs/                     # Customer YAML configurations
│   └── ban_724636.yml          # Example configuration
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## How It Works

1. **Load Configuration**: Parses the YAML file and validates required fields
2. **Authenticate**: Connects to LogicMonitor API using HMAC authentication
3. **Resolve IDs**: Maps hostnames to deviceIds, interfaces to instanceIds
4. **Create Dashboard**: Ensures dashboard group and dashboard exist
5. **Build Widgets**: Creates all widgets (clears existing widgets first)
6. **Report Results**: Prints summary of what was created/resolved

## Widget Types Created

### Header Widget
- Customer name and BAN using dashboard tokens
- Contact information

### Interface Statistics Table
- All interfaces with `include_in_table: true`
- Columns: InMbps, OutMbps, Utilization, Errors, Discards

### Traffic Graphs
- One graph per interface with `include_in_traffic_graphs: true`
- Organized by device with section headers
- Shows InMbps and OutMbps lines

### DOM Optics Graphs (for leaf devices)
- Four graphs per interface with `dom: true`
- Laser Bias, Module Temperature, Rx Power, Tx Power

### BGP Peers Table
- Only if `bgp_peers` section exists
- Shows peer state, prefix count, flap count

## Error Handling

- Devices not found in LM are logged and skipped
- Interfaces not found are logged and skipped
- Summary at end shows what was resolved vs. unresolved
- Script continues even if some items can't be resolved

## Extending for Multiple Metros

The YAML schema includes `metros` and per-device `metro` fields. To extend:

1. Create separate YAML files per metro (e.g., `ban_724636_dfw.yml`)
2. Or include all metros in one file and filter by metro in the config
3. Dashboard group can include metro: `"DFW DEMO/Customer Dashboards"`

## Troubleshooting

### Device not found
- Verify hostname matches LM's `system.displayname` or `system.sysname`
- Use `--debug` to see the exact API queries

### Interface not found
- Check that the interface datasource is applied to the device
- Verify interface name/alias matches LM instance displayName or description

### Authentication errors
- Verify access ID and key are correct
- Ensure API user has permissions for dashboards and devices

## License

Internal use only.
