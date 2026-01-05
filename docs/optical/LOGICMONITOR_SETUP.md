# LogicMonitor Configuration Guide

This guide explains how to configure LogicMonitor to graph and alert on data collected by the NETCONF optical scripts.

## Prerequisites

Before configuring LogicMonitor:

1. **Scripts tested successfully** — Run scripts with `--debug` against real devices
2. **Collectors prepared** — Python 3.9+ and dependencies installed on all collectors
3. **Device properties planned** — Know what credentials you'll use for NETCONF access

---

## Collector Preparation

LogicMonitor distributes your Python scripts automatically, but **you must pre-install Python and dependencies** on each collector.

### Option A: System Python (Simplest)
```bash
# RHEL/CentOS
sudo yum install python3 python3-pip
sudo pip3 install ncclient lxml pyyaml

# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip
sudo pip3 install ncclient lxml pyyaml
```

### Option B: Virtual Environment (Recommended)
```bash
# Create venv
sudo python3 -m venv /opt/lm-netconf-venv

# Install dependencies
sudo /opt/lm-netconf-venv/bin/pip install ncclient lxml pyyaml

# Verify
/opt/lm-netconf-venv/bin/python -c "import ncclient; print('OK')"
```

If using a venv, update the shebang in each script:
```python
#!/opt/lm-netconf-venv/bin/python3
```

### Option C: Ansible Automation (For Multiple Collectors)
```yaml
# playbook: setup_collectors.yml
- name: Prepare LM Collectors for NETCONF scripts
  hosts: lm_collectors
  become: yes
  tasks:
    - name: Install Python 3
      package:
        name: python3
        state: present

    - name: Install pip
      package:
        name: python3-pip
        state: present

    - name: Install NETCONF dependencies
      pip:
        name:
          - ncclient
          - lxml
          - pyyaml
        executable: pip3
```

Run: `ansible-playbook -i inventory setup_collectors.yml`

### Verify Installation

On each collector:
```bash
python3 -c "from ncclient import manager; from lxml import etree; import yaml; print('All dependencies OK')"
```

---

## Understanding Discovery vs Collection

LogicMonitor uses two separate processes:

| Process | Purpose | What It Does | How Often |
|---------|---------|--------------|-----------|
| **Active Discovery** | Find instances | Lists optical interfaces on device | Infrequently (4-24 hours) |
| **Collection** | Get metrics | Reads values for all known instances | Frequently (2-5 minutes) |

### Active Discovery

Answers: *"What optical interfaces exist on this device?"*

- Runs `coriant_discover.py`
- Returns list of instance IDs (e.g., `ots-1-1`, `osc-east`)
- LogicMonitor creates these as trackable instances
- **Frequency:** Every 4-24 hours is typical for optical equipment (interfaces rarely change)
- Can be triggered manually after configuration changes

### Collection

Answers: *"What are the current metric values for each interface?"*

- Runs `coriant_collect.py`
- Returns metrics for ALL instances in one call (BATCHSCRIPT mode)
- LogicMonitor stores values, updates graphs, evaluates alert thresholds
- **Frequency:** Every 2-5 minutes depending on how quickly you need to detect issues

### Why Separate?

- Discovery is expensive (enumerates everything) — run infrequently
- Collection is targeted (just gets values) — run frequently
- If an interface is removed, discovery updates the instance list
- Collection continues for known instances between discovery runs

---

## Step-by-Step: Create a DataSource

### Step 1: Create DataSource Definition

1. Go to **Settings → LogicModules → DataSources**
2. Click **Add → DataSource**
3. Fill in **General Information**:

| Field | Value | Notes |
|-------|-------|-------|
| Name | `Coriant_Optical_Interfaces` | Unique identifier |
| Display Name | `Optical Interfaces` | Shows in UI |
| Group | `Optical` | Organizes DataSources |
| Applies To | `netconf.vendor == "Coriant"` | Which devices get this DataSource |
| Collect every | `5 minutes` | Collection frequency |
| Multi-instance | ✓ Checked | Multiple interfaces per device |
| Collector | `BATCHSCRIPT` | Script runs once, returns all instances |

### Step 2: Configure Active Discovery

Expand the **Active Discovery** section:

| Field | Value |
|-------|-------|
| Enable Active Discovery | ✓ Checked |
| Method | `Script` |
| Script Type | `Upload script file` |
| Linux/Unix Script | `coriant_discover.py` |
| Script Parameters | `##system.hostname## ##netconf.user## ##netconf.pass##` |
| Schedule | Every `720` minutes (12 hours) |

Click **Upload Script** and select `coriant_discover.py`.

**Parameter Explanation:**
- `##system.hostname##` — Device's hostname/IP from LM
- `##netconf.user##` — Custom property you set on the device
- `##netconf.pass##` — Custom property (encrypted) you set on the device

### Step 3: Configure Collection

Expand the **Collection** section:

| Field | Value |
|-------|-------|
| Script Type | `Upload script file` |
| Linux/Unix Script | `coriant_collect.py` |
| Script Parameters | `##system.hostname## ##netconf.user## ##netconf.pass##` |

Click **Upload Script** and select `coriant_collect.py`.

### Step 4: Define Datapoints

Datapoints tell LogicMonitor which metrics to extract from script output.

For each metric, click **Add Datapoint**:

#### rx_optical_power

| Field | Value |
|-------|-------|
| Name | `rx_optical_power` |
| Description | `Received optical power in dBm` |
| Type | `gauge` |
| Use script/batch output | Selected |
| Interpret as | `Multi-line key-value pairs` |
| Key | `##WILDVALUE##.rx_optical_power` |

#### tx_optical_power

| Field | Value |
|-------|-------|
| Name | `tx_optical_power` |
| Description | `Transmitted optical power in dBm` |
| Type | `gauge` |
| Key | `##WILDVALUE##.tx_optical_power` |

#### oper_status

| Field | Value |
|-------|-------|
| Name | `oper_status` |
| Description | `Operational status (1=up, 0=down)` |
| Type | `gauge` |
| Key | `##WILDVALUE##.oper_status` |

#### admin_status

| Field | Value |
|-------|-------|
| Name | `admin_status` |
| Description | `Administrative status (1=up, 0=down)` |
| Type | `gauge` |
| Key | `##WILDVALUE##.admin_status` |

#### measured_span_loss

| Field | Value |
|-------|-------|
| Name | `measured_span_loss` |
| Description | `Fiber span loss in dB` |
| Type | `gauge` |
| Key | `##WILDVALUE##.measured_span_loss` |

**How ##WILDVALUE## Works:**

LogicMonitor replaces `##WILDVALUE##` with each instance ID discovered. If discovery found instances `ots-1-1` and `ots-1-2`, then:

- For `ots-1-1`: LM looks for `ots-1-1.rx_optical_power` in script output
- For `ots-1-2`: LM looks for `ots-1-2.rx_optical_power` in script output

### Step 5: Set Alert Thresholds

On each datapoint, configure when to alert:

#### rx_optical_power Thresholds

| Level | Operator | Value | Meaning |
|-------|----------|-------|---------|
| Warning | `<` | `-20` | Signal getting weak |
| Error | `<` | `-25` | Signal degraded |
| Critical | `<` | `-30` | Signal critical/failing |
| Warning | `>` | `3` | Signal too strong (saturation risk) |

#### oper_status Thresholds

| Level | Operator | Value | Meaning |
|-------|----------|-------|---------|
| Critical | `==` | `0` | Interface is DOWN |

#### measured_span_loss Thresholds

| Level | Operator | Value | Meaning |
|-------|----------|-------|---------|
| Warning | `>` | `25` | Span loss elevated |
| Error | `>` | `30` | Span loss high |

### Step 6: Create Graphs (Optional)

LogicMonitor auto-generates basic graphs. For custom graphs:

1. Go to **Graphs** tab in DataSource
2. Click **Add Graph**
3. Example: "Optical Power"
   - Add datapoints: `rx_optical_power`, `tx_optical_power`
   - Y-axis label: `dBm`
   - Set appropriate scale

### Step 7: Save DataSource

Click **Save** to create the DataSource.

---

## Alternative: Import DataSource Templates

Pre-configured DataSource templates are in the `logicmonitor/` directory.

1. Go to **Settings → LogicModules → DataSources**
2. Click **Add → Import**
3. Select XML file (e.g., `Coriant_Optical_Interfaces.xml`)
4. Review settings and confirm

**Note:** You still need to upload the Python scripts after import.

---

## Add Devices and Set Properties

### Add Optical Device to LogicMonitor

If not already monitored:
1. Go to **Resources → Add → Device**
2. Enter hostname/IP
3. Assign to appropriate group
4. Select collector(s)

### Set Device Properties

On each optical device, add custom properties:

1. Go to device → **Info** tab
2. Click **+** to add property

| Property | Value | Notes |
|----------|-------|-------|
| `netconf.user` | `admin` | NETCONF username |
| `netconf.pass` | `secretpassword` | NETCONF password (LM encrypts this) |
| `netconf.port` | `830` | Optional, default is 830 |
| `netconf.vendor` | `Coriant` | Must match Applies To logic |

**Tip:** Set properties at group level if all devices share credentials.

---

## Verify Data Collection

### Check Discovery Ran

1. Go to device → **DataSources** tab
2. Find your DataSource
3. Look for discovered instances

If no instances:
- Check **Active Discovery** task log
- Run discovery script manually with `--debug`

### Check Collection Working

1. Click on an instance
2. Go to **Raw Data** tab
3. Should see recent values

If "No Data":
- Check **Collection** task log
- Verify script parameters are correct
- Test script manually on collector

### View Graphs

1. Device → **Graphs** tab
2. Select DataSource and instance
3. Should see metrics plotted over time

---

## Troubleshooting

### No Instances Discovered

**Symptoms:** DataSource applied but no instances shown

**Check:**
1. Device has correct `netconf.vendor` property
2. Discovery script uploaded successfully
3. Run manually: `python3 coriant_discover.py <host> <user> <pass> --debug`
4. Check collector has Python dependencies

### Instances Found but No Data

**Symptoms:** Instances exist but metrics show "No Data"

**Check:**
1. Collection script uploaded successfully
2. Script parameters match discovery parameters
3. Run manually: `python3 coriant_collect.py <host> <user> <pass> --debug`
4. Verify output format matches datapoint keys

### Script Errors in Task Log

**Common issues:**

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: ncclient` | Dependencies not installed | Install on collector |
| `Connection refused` | Device unreachable or wrong port | Check network/firewall |
| `Authentication failed` | Wrong credentials | Verify device properties |
| `No matching element` | XPath query issue | Check with `--debug`, adjust config |

### Test Script Directly on Collector

SSH to collector and run:
```bash
# Find where LM puts scripts
ls /usr/local/logicmonitor/agent/local/bin/

# Run discovery
python3 /usr/local/logicmonitor/agent/local/bin/coriant_discover.py \
  192.168.1.100 admin password123 --debug

# Run collection
python3 /usr/local/logicmonitor/agent/local/bin/coriant_collect.py \
  192.168.1.100 admin password123 --debug
```

---

## DataSource Summary

After setup, you should have:

| DataSource | Vendor | Type | Scripts | Instances |
|------------|--------|------|---------|-----------|
| Coriant_Optical_Interfaces | Coriant | BATCHSCRIPT | discover + collect | OTS, OSC, OMS |
| Coriant_Chassis | Coriant | SCRIPT | collect only | Single |
| Ciena_WaveServer_Interfaces | Ciena | BATCHSCRIPT | discover + collect | PTPs, Ports |
| Ciena_WaveServer_Chassis | Ciena | SCRIPT | collect only | Single |

---

## Quick Reference: Output Formats

### Discovery Script Output
```
instance_id##instance_name##description####auto.property=value
```

### Collection Script Output (BATCHSCRIPT)
```
instance_id.datapoint_name=numeric_value
```

### Single-Instance Collection Output
```
datapoint_name=numeric_value
```

---

## Next Steps

1. Complete collector preparation (Python + dependencies)
2. Import DataSource templates or create manually
3. Upload Python scripts via WebUI
4. Add devices and set NETCONF properties
5. Verify discovery finds instances
6. Verify collection returns data
7. Tune alert thresholds based on your environment