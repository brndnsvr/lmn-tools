# Device Group Reorganization Plan

Strategy for organizing Juniper devices in LogicMonitor for optimal monitoring, alerting, and property inheritance.

## Current State

```
/Devices by Type/
  /Juniper Devices (ID: 46)
    Type: Dynamic Group
    AppliesTo: system.categories =~ "Juniper"
    Devices: 60 (all EX3400 switches)
    Properties: Minimal, mostly device-level
```

### Current Issues

1. **Flat structure** - All 60 devices in one group
2. **No device-type separation** - Can't apply SRX-specific vs EX-specific settings
3. **No site organization** - Hard to manage per-site alerting
4. **Property duplication** - Same credentials on each device instead of inherited

---

## Proposed Structure

```
/Network Infrastructure/
  /Juniper/
    ├── _All Juniper Devices (dynamic)
    │     AppliesTo: system.categories =~ "Juniper"
    │     Properties: SNMP credentials, SSH credentials
    │
    ├── /EX Switches/
    │     ├── _All EX Switches (dynamic)
    │     │     AppliesTo: system.categories =~ "Juniper" && system.sysinfo =~ "EX"
    │     │     Properties: juniper.device.type=EX, alert.team=network-ops
    │     │
    │     └── /By Site/
    │           ├── /DAL1-EX (dynamic: displayName =~ "DAL1-IS*")
    │           ├── /DAL2-EX
    │           ├── /LAX2-EX
    │           ├── /ATL1-EX
    │           ├── /WDC1-EX
    │           ├── /CHI1-EX
    │           ├── /PHX1-EX
    │           ├── /NYC3-EX
    │           ├── /SEA1-EX
    │           └── /BOS1-EX
    │
    ├── /QFX Switches/ (future)
    │     ├── _All QFX Switches (dynamic)
    │     │     AppliesTo: system.categories =~ "Juniper" && system.sysinfo =~ "QFX"
    │     │     Properties: juniper.device.type=QFX
    │     │
    │     ├── /Spine/
    │     └── /Leaf/
    │
    ├── /SRX Firewalls/ (future)
    │     ├── _All SRX Firewalls (dynamic)
    │     │     AppliesTo: system.categories =~ "Juniper" && system.sysinfo =~ "SRX"
    │     │     Properties: juniper.device.type=SRX, alert.team=security-ops
    │     │
    │     ├── /Perimeter/
    │     └── /Internal/
    │
    └── /MX Routers/ (future)
          ├── _All MX Routers (dynamic)
          │     AppliesTo: system.categories =~ "Juniper" && system.sysinfo =~ "MX"
          │     Properties: juniper.device.type=MX
          │
          ├── /Edge/
          └── /Core/
```

---

## Property Inheritance Strategy

### Level 1: `/Network Infrastructure/Juniper/`

Common properties for ALL Juniper devices:

```properties
# SNMP v3 Credentials
snmp.version=v3
snmp.security=SNMPROUSER
snmp.auth=SHA
snmp.authToken=<encrypted>
snmp.priv=AES128
snmp.privToken=<encrypted>

# SSH Credentials (for ConfigSource)
ssh.user=lm-config
ssh.pass=<encrypted>

# General Juniper settings
config.user=lm-config
config.pass=<encrypted>
```

### Level 2: Device Type Groups

#### EX Switches `/Juniper/EX Switches/`
```properties
juniper.device.type=EX
alert.routing.team=network-ops
alert.severity.default=warning
```

#### QFX Switches `/Juniper/QFX Switches/`
```properties
juniper.device.type=QFX
alert.routing.team=network-ops
evpn.expected.vnis=50
evpn.mac.warn.threshold=80
```

#### SRX Firewalls `/Juniper/SRX Firewalls/`
```properties
juniper.device.type=SRX
alert.routing.team=security-ops
alert.severity.default=critical
```

#### MX Routers `/Juniper/MX Routers/`
```properties
juniper.device.type=MX
alert.routing.team=network-ops
routing.baseline.bgp=850000
routing.warn.deviation=20
```

### Level 3: Site Groups (Example)

#### `/Juniper/EX Switches/By Site/DAL1-EX/`
```properties
location.site=DAL1
location.datacenter=Dallas Primary
alert.escalation.chain=DAL1-Network-Oncall
```

---

## AppliesTo Expressions

### Dynamic Group Queries

| Group | AppliesTo Expression |
|-------|---------------------|
| _All Juniper Devices | `system.categories =~ "Juniper"` |
| _All EX Switches | `system.categories =~ "Juniper" && system.sysinfo =~ "EX"` |
| _All QFX Switches | `system.categories =~ "Juniper" && system.sysinfo =~ "QFX"` |
| _All SRX Firewalls | `system.categories =~ "Juniper" && system.sysinfo =~ "SRX"` |
| _All MX Routers | `system.categories =~ "Juniper" && system.sysinfo =~ "MX"` |
| DAL1-EX | `system.categories =~ "Juniper" && displayName =~ "DAL1-IS*"` |
| DAL2-EX | `system.categories =~ "Juniper" && displayName =~ "DAL2-IS*"` |

### Advanced Filtering Examples

```
# QFX in EVPN-VXLAN role
system.categories =~ "Juniper" && system.sysinfo =~ "QFX" && auto.evpn.enabled == "true"

# SRX in cluster mode
system.categories =~ "Juniper" && system.sysinfo =~ "SRX" && auto.cluster_mode == "true"

# MX with full BGP table
system.categories =~ "Juniper" && system.sysinfo =~ "MX" && routing.role == "edge"

# Production devices only
system.categories =~ "Juniper" && auto.environment == "production"
```

---

## Migration Steps

### Phase 1: Create Group Structure (Read-Only)

1. Create parent groups (empty):
   ```
   POST /device/groups
   {
     "name": "Network Infrastructure",
     "parentId": 1,
     "disableAlerting": false
   }
   ```

2. Create Juniper parent group:
   ```
   POST /device/groups
   {
     "name": "Juniper",
     "parentId": <network-infra-id>,
     "disableAlerting": false
   }
   ```

3. Create device-type subgroups:
   - EX Switches
   - QFX Switches (future)
   - SRX Firewalls (future)
   - MX Routers (future)

4. Create site subgroups under EX Switches

### Phase 2: Set Group Properties

1. Set SNMP/SSH credentials at `/Juniper/` level
2. Set device-type properties at type level
3. Set site-specific properties at site level

### Phase 3: Create Dynamic Groups

1. Create `_All Juniper Devices` with AppliesTo
2. Create `_All EX Switches` with AppliesTo
3. Create per-site dynamic groups
4. Verify device counts match expected

### Phase 4: Verify Inheritance

1. Check a device's effective properties
2. Verify SNMP polling works with inherited credentials
3. Verify SSH access works for ConfigSource
4. Confirm datasource discovery uses correct properties

### Phase 5: Migrate from Old Group

1. Note current `Juniper Devices` group ID (46)
2. Verify all devices now appear in new dynamic groups
3. Disable alerting on old group
4. After 1 week with no issues, delete old group

---

## API Examples

### Create Device Group

```bash
curl -X POST "https://evoquedcs.logicmonitor.com/santaba/rest/device/groups" \
  -H "Authorization: LMv1 ..." \
  -H "Content-Type: application/json" \
  -d '{
    "name": "EX Switches",
    "description": "All Juniper EX Series switches",
    "parentId": 123,
    "appliesTo": "system.categories =~ \"Juniper\" && system.sysinfo =~ \"EX\"",
    "customProperties": [
      {"name": "juniper.device.type", "value": "EX"},
      {"name": "alert.routing.team", "value": "network-ops"}
    ]
  }'
```

### Set Group Properties

```bash
curl -X PUT "https://evoquedcs.logicmonitor.com/santaba/rest/device/groups/123" \
  -H "Authorization: LMv1 ..." \
  -H "Content-Type: application/json" \
  -d '{
    "customProperties": [
      {"name": "snmp.version", "value": "v3"},
      {"name": "snmp.security", "value": "SNMPROUSER"},
      {"name": "snmp.auth", "value": "SHA"},
      {"name": "snmp.priv", "value": "AES128"}
    ]
  }'
```

### Verify Device Inheritance

```bash
curl -X GET "https://evoquedcs.logicmonitor.com/santaba/rest/device/devices/456/properties" \
  -H "Authorization: LMv1 ..."
```

---

## Benefits of New Structure

| Benefit | Description |
|---------|-------------|
| **Property inheritance** | Set credentials once at group level |
| **Device-type targeting** | Apply SRX datasources only to SRX devices |
| **Site-based alerting** | Route alerts to site-specific teams |
| **Scalability** | Easy to add new devices/sites |
| **Compliance** | Easier to audit and report by device type |
| **Reduced errors** | No manual property updates per device |

---

## Rollback Plan

If migration causes issues:

1. **Immediate**: Devices will still be monitored via dynamic group membership
2. **Credentials**: If inheritance fails, re-add device-level properties
3. **Alerts**: Re-enable alerting on old `Juniper Devices` group
4. **Permanent rollback**: Delete new groups, keep old structure

---

## Maintenance Procedures

### Adding a New Site

1. Create site subgroup under appropriate device-type group
2. Set AppliesTo: `displayName =~ "NEWSITE-IS*"`
3. Set site-specific properties if different from parent
4. Verify devices appear in new group

### Adding a New Device Type

1. Create device-type group under `/Juniper/`
2. Set AppliesTo based on `system.sysinfo`
3. Create site subgroups as needed
4. Set device-type-specific properties
5. Enable relevant custom datasources

### Removing Decommissioned Devices

1. Remove device from LogicMonitor (devices auto-leave dynamic groups)
2. No group maintenance required
3. Historical data retained per retention policy
