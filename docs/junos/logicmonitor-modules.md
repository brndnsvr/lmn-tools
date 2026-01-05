# LogicMonitor Modules Registry

This document tracks all custom LogicModules deployed to the LogicMonitor instance via API.

## Environment

| Setting | Value |
|---------|-------|
| Company | evoquedcs |
| Base URL | https://evoquedcs.logicmonitor.com |
| API Version | v3 |

---

## PropertySources

### Juniper_SRX_ClusterDetect

| Property | Value |
|----------|-------|
| **ID** | 169 |
| **Name** | Juniper_SRX_ClusterDetect |
| **Display Name** | Juniper SRX Cluster Detection |
| **Config File** | `configs/logicmonitor/propertysource-cluster-detect.json` |
| **Applies To** | `system.categories =~ "Juniper" && system.sysinfo =~ "SRX"` |
| **Interval** | 86400 seconds (24 hours) |
| **Script Type** | Groovy (embedded) |

**Purpose:** Automatically detects if an SRX firewall is operating in chassis cluster mode by querying the jnxJsChassisClusterMIB. Sets the `auto.cluster_mode` property which enables the Chassis Cluster DataSource.

**Properties Set:**
- `auto.cluster_mode` - "true" if clustered, "false" if standalone
- `auto.cluster_id` - Cluster ID (if clustered)
- `auto.cluster_node_id` - Node ID (if clustered)

**SNMP OIDs Used:**
- `1.3.6.1.4.1.2636.3.39.1.13.1.1.1.8.0` - jnxJsChassisClusterSwitchoverCount (cluster detection)
- `1.3.6.1.4.1.2636.3.39.1.13.1.1.1.1.0` - Cluster ID
- `1.3.6.1.4.1.2636.3.39.1.13.1.1.1.3.0` - Node ID

---

## DataSources

### Juniper_RoutingTable

| Property | Value |
|----------|-------|
| **ID** | 21328209 |
| **Name** | Juniper_RoutingTable |
| **Display Name** | Routing Table |
| **Config File** | `configs/logicmonitor/datasource-routing.json` |
| **Applies To** | `hasCategory("Juniper")` |
| **Collect Interval** | 300 seconds (5 minutes) |
| **Multi-Instance** | No |
| **Collect Method** | Groovy batchscript |

**Purpose:** Monitors routing table size and FIB utilization for capacity planning and anomaly detection.

**DataPoints:**

| Name | Description | Alert Threshold |
|------|-------------|-----------------|
| TotalRoutes | Total routes in routing table | - |
| ActiveRoutes | Active routes in routing table | - |
| HiddenRoutes | Hidden (inactive) routes | > 100 (warn) |
| FIBUtilization | FIB table utilization % | > 80 (warn), > 90 (error) |

**SNMP OIDs Used:**
- `1.3.6.1.2.1.4.24.6.0` - ipCidrRouteNumber (RFC 4292 IP-FORWARD-MIB)

> **Note:** Juniper-specific routing OIDs in enterprise MIB are not reliably available across platforms. The standard IP-FORWARD-MIB provides consistent route counts on all Juniper devices.

**Device Properties:**
- `routing.fib.limit` - Optional. FIB limit for utilization calculation (default: 256000)

---

### Juniper_EVPN_VXLAN

| Property | Value |
|----------|-------|
| **ID** | 21328204 |
| **Name** | Juniper_EVPN_VXLAN |
| **Display Name** | EVPN VXLAN |
| **Config File** | `configs/logicmonitor/datasource-evpn.json` |
| **Applies To** | `hasCategory("Juniper") && system.sysinfo =~ "QFX"` |
| **Collect Interval** | 300 seconds (5 minutes) |
| **Multi-Instance** | Yes (per VNI) |
| **Discovery Interval** | 60 minutes |
| **Collect Method** | Groovy batchscript |

**Purpose:** Monitors EVPN-VXLAN fabric health on QFX switches including VNI status, VTEP peers, and MAC tables.

**DataPoints:**

| Name | Description | Alert Threshold |
|------|-------------|-----------------|
| Status | VNI operational status (1=up, 0=down) | != 1 (critical) |
| VTEPPeerCount | Remote VTEP peers for this VNI | - |
| MACCount | MAC addresses learned for this VNI | - |
| MACUtilization | MAC table utilization % | > 80 (warn), > 90 (error) |

**SNMP OIDs Used:**
- `1.3.6.1.4.1.2636.3.77.1.1.2.1.2` - jnxVxlanTunnelVni (discovery)
- `1.3.6.1.4.1.2636.3.77.1.1.2.1.3` - jnxVxlanTunnelStatus
- `1.3.6.1.4.1.2636.3.77.1.1.2.1.4` - jnxVxlanRemoteVtep
- `1.3.6.1.4.1.2636.3.77.1.1.2.1.5` - jnxVxlanMacCount

**Device Properties:**
- `evpn.mac.limit` - Optional. MAC table limit for utilization calculation (default: 512000)

**Instance Properties Set:**
- `auto.vni.id` - VNI identifier

---

### Juniper_SRX_ChassisCluster

| Property | Value |
|----------|-------|
| **ID** | 21328205 |
| **Name** | Juniper_SRX_ChassisCluster |
| **Display Name** | SRX Chassis Cluster |
| **Config File** | `configs/logicmonitor/datasource-cluster.json` |
| **Applies To** | `hasCategory("Juniper") && system.sysinfo =~ "SRX" && auto.cluster_mode == "true"` |
| **Collect Interval** | 60 seconds |
| **Multi-Instance** | Yes (cluster + per-RG) |
| **Discovery Interval** | 60 minutes |
| **Collect Method** | Groovy batchscript |
| **Group** | Juniper |

**Purpose:** Monitors SRX chassis cluster HA status including redundancy groups, control/fabric links, failover events, and peer reachability.

**DataPoints:**

| Name | Description | Alert Threshold |
|------|-------------|-----------------|
| ClusterHealthy | Overall cluster health (1=healthy) | != 1 (critical) |
| ControlLinkUp | Control link status | != 1 (critical) |
| FabricLinkUp | Fabric link status | != 1 (critical) |
| PeerReachable | Peer node reachability | != 1 (critical) |
| TotalFailovers | Failover count since last clear | - |
| RGStatus | RG status (1=primary, 2=sec-hold, 3=secondary) | - |
| RGWeight | Current RG weight (priority minus penalties) | - |
| Preempt | Preemption enabled (1=yes, 0=no) | - |
| MonitorFailures | Active interface/IP monitor failures | > 0 (warn) |

**SNMP OIDs Used:**
- `1.3.6.1.4.1.2636.3.39.1.13.1.1.1.5.0` - Control link status
- `1.3.6.1.4.1.2636.3.39.1.13.1.1.1.6.0` - Fabric link status
- `1.3.6.1.4.1.2636.3.39.1.13.1.1.1.7.0` - Peer status
- `1.3.6.1.4.1.2636.3.39.1.13.1.1.1.8.0` - Failover count
- `1.3.6.1.4.1.2636.3.39.1.13.2.1.1.2` - RG table (discovery)
- `1.3.6.1.4.1.2636.3.39.1.13.2.1.1.3` - RG status
- `1.3.6.1.4.1.2636.3.39.1.13.2.1.1.5` - RG weight
- `1.3.6.1.4.1.2636.3.39.1.13.2.1.1.6` - RG preempt
- `1.3.6.1.4.1.2636.3.39.1.13.2.1.1.7` - Monitor failures

**Discovered Instances:**
- `cluster` - Cluster-wide health metrics
- `rg0` - Control Plane (RG0)
- `rg1`, `rg2`, etc. - Data Plane redundancy groups

**Instance Properties Set:**
- `auto.instance.type` - "cluster" for cluster instance
- `auto.rg.id` - Redundancy group ID
- `auto.rg.type` - "control" or "data"

---

## Management Commands

```bash
# List DataSources
python scripts/manage_lm_modules.py list datasources --filter "Juniper"

# List PropertySources
python scripts/manage_lm_modules.py list propertysources --filter "Juniper"

# Delete a DataSource
python scripts/manage_lm_modules.py delete datasource <ID>

# Create a DataSource
python scripts/manage_lm_modules.py create datasource configs/logicmonitor/datasource-routing.json

# Update a DataSource (PATCH - preserves version history)
python scripts/manage_lm_modules.py update datasource <ID> configs/logicmonitor/datasource-routing.json

# Deploy all Juniper modules
python scripts/manage_lm_modules.py deploy
```

---

## Version History

| Date | Module | Action | Notes |
|------|--------|--------|-------|
| 2024-12-21 | All | Initial deployment | Created via deploy_lm_configs.py |
| 2024-12-21 | All | Deleted | Broken SNMP scripts - missing credentials |
| 2024-12-21 | PropertySource 169 | Created | Fixed with proper SNMP params |
| 2024-12-21 | DataSources 21328199-21328201 | Created | Fixed Groovy scripts with snmpParams map |
| 2024-12-21 | DataSources 21328199-21328202 | Deleted | SNMP method signature errors |
| 2024-12-21 | DataSources 21328203-21328205 | Created | Fixed SNMP API signatures (5-arg v2c, 4-arg v3) |
| 2024-12-22 | DataSource 21328203 | Deleted | Wrong OIDs (.3.48. instead of .3.1.13.) |
| 2024-12-22 | DataSource 21328206 | Created | Fixed OIDs to use jnxRouteTable MIB (.3.1.13.1.x) |
| 2024-12-22 | DataSource 21328206 | Deleted | Still wrong OIDs - .3.1.13 is jnxBoxAnatomy (chassis), not routing |
| 2024-12-22 | DataSource 21328207 | Created | Simplified 3-arg SNMP signature, still wrong OIDs |
| 2024-12-22 | DataSource 21328207 | Deleted | OID discovery via snmpwalk confirmed wrong MIB |
| 2024-12-22 | DataSource 21328208 | Created | **Fixed: Uses standard IP-FORWARD-MIB OID 1.3.6.1.2.1.4.24.6.0** |
| 2024-12-22 | DataSource 21328208 | Deleted | Recreated as 21328209 with 2-arg SNMP signature |
| 2024-12-22 | DataSource 21328209 | Created | Working 2-arg SNMP.get(host, oid) - data collecting |
| 2024-12-23 | DataSource 21328209 | Updated (PATCH) | v1.1.0 - Updated graphs: Route Counts, Active vs Hidden, FIB Utilization |

---

## Troubleshooting

### No Data Collecting

1. **Check AuditVersion** - Must be > 0 (committed in UI)
2. **Check SNMP access** - Device must have working SNMP credentials
3. **Wait for collection cycle** - New DataSources need 5 minutes
4. **Check collector** - Device must have an active collector

### DataSource Not Applied

1. **Check AppliesTo** - Verify device matches the expression
2. **Check categories** - Device must have "Juniper" category
3. **Check sysinfo** - For QFX/SRX specific modules

### Cluster DataSource Not Appearing

1. **Check PropertySource** - Must have `auto.cluster_mode = true`
2. **Trigger property scan** - PATCH device with `scanProperties: true`
3. **Wait 24 hours** - PropertySource runs daily by default
