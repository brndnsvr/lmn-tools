# Deployment Guide

This guide covers deploying the NETCONF Optical Device Collector to LogicMonitor collectors.

---

## Prerequisites

- LogicMonitor collector (Linux, version 30+)
- Python 3.9+ on collector
- Network access from collector to optical devices (port 830)
- NETCONF enabled on optical devices
- NETCONF credentials with read access

---

## Step 1: Install on Collector

### 1.1 Copy Files

Copy the `lm-netconf-optical` directory to each collector:

```bash
# Option A: Using scp
scp -r lm-netconf-optical collector:/usr/local/logicmonitor/

# Option B: Using rsync
rsync -av lm-netconf-optical collector:/usr/local/logicmonitor/

# Option C: Git clone directly on collector
ssh collector
cd /usr/local/logicmonitor
git clone <repository-url> lm-netconf-optical
```

### 1.2 Install Python Dependencies

```bash
ssh collector
cd /usr/local/logicmonitor/lm-netconf-optical
sudo pip3 install -r requirements.txt
```

Verify installation:
```bash
python3 -c "import ncclient; import lxml; import yaml; print('OK')"
```

### 1.3 Set Permissions

```bash
sudo chmod +x /usr/local/logicmonitor/lm-netconf-optical/scripts/*.py
sudo chown -R logicmonitor:logicmonitor /usr/local/logicmonitor/lm-netconf-optical
```

### 1.4 Test Connectivity

Test from the collector to verify NETCONF connectivity:

```bash
# Test Coriant device
python3 /usr/local/logicmonitor/lm-netconf-optical/scripts/coriant_discover.py \
    device.example.com admin password123 --debug

# Test Ciena device
python3 /usr/local/logicmonitor/lm-netconf-optical/scripts/ciena_discover.py \
    waveserver.example.com admin password123 --debug
```

---

## Step 2: Configure Device Properties

### 2.1 Create Device Properties

In LogicMonitor, add these properties to your optical devices (or device groups):

| Property | Value | Description |
|----------|-------|-------------|
| `netconf.user` | `admin` | NETCONF username |
| `netconf.pass` | `secret` | NETCONF password |
| `netconf.port` | `830` | NETCONF port (optional, default 830) |

**To add at device level:**
1. Go to **Resources** → Select device
2. Click **Manage** → **Properties**
3. Add properties

**To add at group level (recommended):**
1. Go to **Resources** → Select device group
2. Click **Manage** → **Properties**
3. Add properties (applies to all devices in group)

### 2.2 Add Device Categories

Add the appropriate category to enable automatic DataSource application:

| Vendor | Category |
|--------|----------|
| Coriant | `CoriantOptical` |
| Ciena | `CienaWaveServer` |

**To add category:**
1. Go to **Resources** → Select device
2. Click **Manage** → **Properties**
3. Add/update `system.categories` property

---

## Step 3: Import DataSources

### 3.1 Import from XML

1. Go to **Settings** → **LogicModules** → **DataSources**
2. Click **Add** → **Import from file**
3. Upload each XML file from `logicmonitor/` directory:
   - `Coriant_Optical_Interfaces.xml`
   - `Coriant_Chassis.xml`
   - `Ciena_WaveServer_Interfaces.xml`
   - `Ciena_WaveServer_Chassis.xml`

### 3.2 Update Script Paths

After import, edit each DataSource to verify the script path:

1. Open the DataSource
2. Find the Groovy collection script
3. Verify `scriptPath` matches your installation:
   ```groovy
   def scriptPath = "/usr/local/logicmonitor/lm-netconf-optical/scripts/coriant_discover.py"
   ```

### 3.3 Update AppliesTo

Modify the `appliesTo` field if needed:

```
// Default (uses categories)
hasCategory("CoriantOptical")

// Alternative (uses hostname pattern)
system.hostname =~ "optical.*"

// Alternative (uses sysoid)
system.sysoid == "1.3.6.1.4.1.XXXXX"

// Combination
hasCategory("CoriantOptical") || system.hostname =~ "cor-.*"
```

---

## Step 4: Verify Data Collection

### 4.1 Run Active Discovery

1. Go to **Resources** → Select device
2. Open the DataSource (e.g., "Coriant Optical Interfaces")
3. Click **Run Active Discovery**
4. Verify instances are discovered

### 4.2 Check Data

1. Wait for first collection interval (default: 5 minutes)
2. Go to device → DataSource → Instance
3. Click on a datapoint to view graph

### 4.3 Troubleshoot

If no data appears:

1. **Check collector logs:**
   ```bash
   tail -f /usr/local/logicmonitor/agent/logs/wrapper.log
   ```

2. **Run script manually with debug:**
   ```bash
   python3 /usr/local/logicmonitor/lm-netconf-optical/scripts/coriant_discover.py \
       device.example.com admin password123 --debug 2>&1
   ```

3. **Check device connectivity:**
   ```bash
   nc -zv device.example.com 830
   ```

4. **Verify credentials:**
   ```bash
   ssh admin@device.example.com -p 830  # Should show NETCONF banner
   ```

---

## Multi-Collector Deployment

For environments with multiple collectors:

### Option A: Ansible Playbook

```yaml
- hosts: logicmonitor_collectors
  tasks:
    - name: Copy NETCONF collector
      copy:
        src: lm-netconf-optical/
        dest: /usr/local/logicmonitor/lm-netconf-optical/
        owner: logicmonitor
        group: logicmonitor

    - name: Install Python dependencies
      pip:
        requirements: /usr/local/logicmonitor/lm-netconf-optical/requirements.txt
        executable: pip3
```

### Option B: Shared Storage

Mount shared storage on all collectors:
```bash
mount -t nfs nfs-server:/share/lm-netconf-optical /usr/local/logicmonitor/lm-netconf-optical
```

### Option C: Configuration Management

Use Puppet, Chef, or SaltStack to distribute files.

---

## Updating

To update the scripts:

1. Pull latest changes (or copy new files)
2. Restart collection:
   - No restart needed for script changes
   - DataSource changes require re-import

```bash
# Update via git
cd /usr/local/logicmonitor/lm-netconf-optical
git pull

# Or copy updated files
scp -r lm-netconf-optical/* collector:/usr/local/logicmonitor/lm-netconf-optical/
```

---

## Security Considerations

### Credential Storage

- Store `netconf.pass` as an encrypted property in LogicMonitor
- Use device groups to centralize credential management
- Consider read-only NETCONF accounts

### Network Security

- NETCONF uses SSH (encrypted)
- Restrict collector IP access on devices if possible
- Use firewall rules to limit NETCONF port access

### File Permissions

```bash
# Restrictive permissions
chmod 750 /usr/local/logicmonitor/lm-netconf-optical/scripts/*.py
chmod 640 /usr/local/logicmonitor/lm-netconf-optical/configs/*.yaml
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Connection refused | NETCONF not enabled | Enable NETCONF on device port 830 |
| Authentication failed | Wrong credentials | Verify netconf.user/netconf.pass properties |
| Timeout | Network issue | Check firewall, verify connectivity |
| No instances | Wrong filter | Enable debug, check XML response |
| Import module error | Missing Python package | Run `pip3 install -r requirements.txt` |

### Debug Commands

```bash
# Test NETCONF connectivity
python3 -c "
from ncclient import manager
m = manager.connect(host='device.example.com', port=830,
    username='admin', password='pass', hostkey_verify=False)
print(m.server_capabilities)
"

# Run with full debug
python3 scripts/coriant_discover.py device admin pass --debug 2>&1 | head -100

# Check Python environment
python3 --version
pip3 list | grep -E "ncclient|lxml|PyYAML"
```
