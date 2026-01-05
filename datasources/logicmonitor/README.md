# LogicMonitor DataSource Templates

This directory contains LogicMonitor DataSource XML templates for importing into your LogicMonitor portal.

## DataSources

### Coriant

| DataSource | Type | Description |
|------------|------|-------------|
| `Coriant_Optical_Interfaces.xml` | Multi-instance (BATCHSCRIPT) | Monitors OTS, OMS, OSC, GOPT interfaces |
| `Coriant_Chassis.xml` | Single-instance (SCRIPT) | Monitors chassis temperature, altitude, software state |

### Ciena WaveServer

| DataSource | Type | Description |
|------------|------|-------------|
| `Ciena_WaveServer_Interfaces.xml` | Multi-instance (BATCHSCRIPT) | Monitors PTPs and Ports |
| `Ciena_WaveServer_Chassis.xml` | Single-instance (SCRIPT) | Monitors software operational state |

## Installation

### 1. Install Python Scripts on Collectors

Copy the `lm-netconf-optical` directory to each collector:

```bash
# On each collector
sudo mkdir -p /usr/local/logicmonitor
sudo cp -r lm-netconf-optical /usr/local/logicmonitor/
sudo pip3 install -r /usr/local/logicmonitor/lm-netconf-optical/requirements.txt
```

### 2. Import DataSources

1. In LogicMonitor portal, go to **Settings** → **DataSources**
2. Click **Add** → **Import from XML**
3. Upload each XML file from this directory

### 3. Configure Device Properties

Add the following properties to your optical devices (or device groups):

| Property | Description | Example |
|----------|-------------|---------|
| `netconf.user` | NETCONF username | `admin` |
| `netconf.pass` | NETCONF password | `secret123` |
| `netconf.port` | NETCONF port (optional, default: 830) | `830` |

### 4. Apply Device Categories

For automatic DataSource application, add the appropriate category to your devices:

- **Coriant devices**: Add category `CoriantOptical`
- **Ciena devices**: Add category `CienaWaveServer`

Or modify the `appliesTo` field in each DataSource to match your environment.

## Customization

### Script Paths

The default script path is `/usr/local/logicmonitor/lm-netconf-optical/scripts/`. If you install the scripts elsewhere, update the `scriptPath` variable in each DataSource's Groovy collection script.

### Alert Thresholds

Default alert thresholds are configured for:

- **oper_status = 0**: Alert when interface is down
- **ne_temperature > 55/60/65**: Temperature warnings/errors (Coriant)
- **swload_active = 0**: No active software load (Coriant)
- **software_oper_state = 0**: Software state not normal (Ciena)

Modify the `alertExpr` fields in each DataSource to match your operational requirements.

### Collection Interval

Default collection interval is 300 seconds (5 minutes). Modify the `collectInterval` field to change this.

## Troubleshooting

### Test Scripts Manually

SSH to a collector and test the scripts directly:

```bash
# Test Coriant discovery
python3 /usr/local/logicmonitor/lm-netconf-optical/scripts/coriant_discover.py \
    device.example.com admin password123 --debug

# Test Ciena collection
python3 /usr/local/logicmonitor/lm-netconf-optical/scripts/ciena_collect.py \
    device.example.com admin password123 --debug
```

### Debug Output

All scripts support `--debug` flag for verbose output to stderr. This shows:
- Connection details
- NETCONF session info
- Filter being sent
- Raw XML response
- Parsing steps
- Instance/metric extraction details

### Common Issues

1. **Connection refused**: Verify NETCONF is enabled on port 830
2. **Authentication failed**: Check username/password and NETCONF permissions
3. **No instances discovered**: Enable debug mode and check if XML response contains expected elements
4. **Missing metrics**: Check XPath expressions in YAML config match device XML structure
