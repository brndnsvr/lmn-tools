# Plan: EVPN-VXLAN Full Fabric Visibility

## Branch
`feature/evpn-fabric-visibility`

## Status: Phase 1 Complete (VNI Discovery)
- **v2.22.0** deployed and working
- **50 VNIs** discovered on test device (API verified 2025-01-01)
- Customer ID extraction working (e.g., VNI-5655 → Customer 630439)
- SSH pattern proven: direct commands, no `cli -c` wrapper

## API Validation Findings (2025-01-01)

### Test Device Status
```
Device ID: 217
Name: DL2632678LEF001
Collector: 66
SSH User: lm-poller
DeviceDataSource ID: 13874 (Juniper_EVPN_VXLAN)
Instances: 50 VNIs discovered
```

### Sample VNI Instances Discovered
| VNI | VLAN Name | Customer ID |
|-----|-----------|-------------|
| 5655 | VLAN_630439_226 | 630439 |
| 8596 | VLAN_630853_802 | 630853 |
| 5737 | VLAN_724876_10 | 724876 |
| 5368 | VLAN_723389_100 | 723389 |
| 5461 | VLAN_600001_900 | 600001 |

### Existing Juniper DataSources in LogicMonitor
```
ID: 21328204   Juniper_EVPN_VXLAN (our working datasource)
ID: 21328205   Juniper_SRX_ChassisCluster (not applicable to QFX)
ID: 21328209   Juniper_RoutingTable (1 instance on device 217)
ID: 1507       Juniper_RPM_Tests
ID: 1508       Juniper_IPsec_Tunnels
ID: 1537       Juniper_SRX_SPUs
```

### Routing Table Status on Device 217
```
DeviceDataSource ID: 14421
Instances: 1 (single-instance datasource)
Status: Active, no alerts
```

## Requirements
- **Priority**: Full comprehensive monitoring (BGP + VTEP + Interfaces)
- **ESI/Multi-homing**: Unknown - will auto-detect from `show evpn instance`
- **Scale**: 20+ QFX switches - requires phased rollout
- **Safety**: Read-only operations, no breaking changes
- **Blocker**: SSH allow rule rollout to DFW devices needs CR

---

## Architecture: Modular DataSources

Create **3 new DataSources** (separate from existing VNI datasource for safety):

| DataSource | Instances | Interval | Purpose |
|------------|-----------|----------|---------|
| `Juniper_EVPN_BGP` | Per BGP EVPN peer | 5 min | Control plane health |
| `Juniper_EVPN_VTEPs` | Per remote VTEP | 5 min | Fabric reachability |
| `Juniper_VNI_Interfaces` | Per VNI | 60 min | Port-to-VNI mapping |

**Existing** (no changes):
| DataSource | Status |
|------------|--------|
| `Juniper_EVPN_VXLAN` (v2.22.0) | Keep as-is |

---

## Proven SSH Pattern (from v2.22.0)

### JSch Direct Exec (NOT Expect API)
```groovy
import com.jcraft.jsch.JSch
import com.santaba.agent.util.Settings

def host = hostProps.get('system.hostname')  // Use hostname, NOT system.ips
def user = hostProps.get('ssh.user')
def pass = hostProps.get('ssh.pass')
def port = hostProps.get('ssh.port')?.toInteger() ?: 22
def timeout = 30000

def runCommand(session, cmd) {
    def channel = session.openChannel('exec')
    channel.setCommand(cmd)
    def output = channel.getInputStream()
    channel.connect()
    def result = output.text
    channel.disconnect()
    return result
}

// Connect
def jsch = new JSch()
def session = jsch.getSession(user, host, port)
session.setConfig('StrictHostKeyChecking', 'no')
def authMethod = Settings.getSetting(
    Settings.SSH_PREFEREDAUTHENTICATION,
    Settings.DEFAULT_SSH_PREFEREDAUTHENTICATION
)
session.setConfig('PreferredAuthentications', authMethod)
session.setTimeout(timeout)
if (pass) { session.setPassword(pass) }
session.connect()

// Run command - DIRECT (no cli -c wrapper needed!)
def output = runCommand(session, 'show command here | no-more')
session.disconnect()
```

### Discovery Output Format
```
wildvalue##displayname##description####auto.prop1=val1&auto.prop2=val2
```

Example from working VNI discovery:
```
5655##VNI-5655##VLAN_630439_226 (Customer: 630439)####auto.vni.id=5655&auto.customer.id=630439&auto.vlan.name=VLAN_630439_226
```

### Collection Output Format
```
DataPointName=value
```

Example:
```
Status=1
MACCount=42
MACUtilization=0.01
```

### Key Lessons Learned
1. **Use `system.hostname`** - NOT `system.ips` (first IP may be loopback 128.0.0.127)
2. **Direct commands work** - User shell IS already Junos CLI, no wrapper needed
3. **JSch exec channel** - More reliable than Expect API for non-interactive commands
4. **`| no-more`** - Required to disable paging

---

## Phase 2: BGP EVPN Peers DataSource

**File**: `configs/logicmonitor/datasource-bgp-evpn.json`
**Priority**: P1 - Highest value (control plane visibility)

### Discovery Script
```bash
show bgp summary | no-more
```

Expected output format to parse:
```
Groups: 2 Peers: 4 Down peers: 0
Table          Tot Paths  Act Paths Suppressed    History Damp State    Pending
bgp.evpn.0         12345       6789          0          0          0          0
inet.0              5678       3456          0          0          0          0
Peer                     AS      InPkt     OutPkt    OutQ   Flaps Last Up/Dwn State|#Active/Received/Accepted/Damped...
10.32.255.1           65001     123456     654321       0       2     3w4d5h Establ
  bgp.evpn.0: 1234/2345/2345/0
  inet.0: 567/890/890/0
10.32.255.2           65001     234567     765432       0       1     5w2d3h Establ
  bgp.evpn.0: 2345/3456/3456/0
```

### Discovery Parsing Logic
```groovy
// Parse peers that have bgp.evpn.0 table entries
output.eachLine { line ->
    // Match peer line: IP, AS, stats, State
    def peerMatch = line =~ /^(\d+\.\d+\.\d+\.\d+)\s+(\d+)\s+.*\s+(Establ|Active|Connect|Idle)/
    if (peerMatch.find()) {
        currentPeer = peerMatch.group(1)
        currentAS = peerMatch.group(2)
    }
    // Match EVPN table reference
    def evpnMatch = line =~ /bgp\.evpn\.0:\s*(\d+)\/(\d+)/
    if (evpnMatch.find() && currentPeer) {
        println "${currentPeer}##BGP-${currentPeer}##AS${currentAS} EVPN Peer####auto.peer.ip=${currentPeer}&auto.peer.asn=${currentAS}"
    }
}
```

### Collection Script
```bash
show bgp neighbor <peer-ip> | no-more
```

### DataPoints
| Name | Type | Alert | Description | Parse Pattern |
|------|------|-------|-------------|---------------|
| PeerState | Gauge | `!= 6` | 6=Established | `State: (\w+)` -> enum |
| PrefixesReceived | Gauge | `< 10` | Type-2/Type-5 routes | `bgp.evpn.0: (\d+)/` |
| SessionUptime | Gauge | `< 300` | Seconds | `Last Up/Dwn: (\S+)` -> convert |
| MessagesIn | Counter | - | For graphing | `Total data.*received (\d+)` |
| MessagesOut | Counter | - | For graphing | `Total data.*sent (\d+)` |

### State Enum Mapping
```groovy
def stateMap = [
    'Idle': 1,
    'Connect': 2,
    'Active': 3,
    'OpenSent': 4,
    'OpenConfirm': 5,
    'Established': 6  // Only alert if != 6
]
```

### Instance Properties
- `auto.peer.ip` - Peer IP address (wildvalue)
- `auto.peer.asn` - Remote AS number
- `auto.peer.description` - Description if configured

### AppliesTo
```
hasCategory("Juniper") && system.sysinfo =~ "QFX"
```

### TODO: Validate on Device
- [ ] SSH to device 217, run `show bgp summary | no-more`
- [ ] Confirm EVPN peers exist (needs SSH allow rule for more devices)
- [ ] Capture sample output for regex development

---

## Phase 3: VTEP Peers DataSource

**File**: `configs/logicmonitor/datasource-evpn-vteps.json`
**Priority**: P2 - Data plane visibility (fabric mesh health)

### Discovery Script
```bash
show ethernet-switching vxlan-tunnel-end-point remote | no-more
```

Expected output format:
```
Logical System Name       Id  SVTEP-IP         IFL   RVTEP-IP        IFL-Idx   VNID         MC-Group-IP        Flags
<default>                 0   10.32.255.10     lo0.0 10.32.255.11    xxxx      *            0.0.0.0            N/A
<default>                 0   10.32.255.10     lo0.0 10.32.255.12    xxxx      *            0.0.0.0            N/A
<default>                 0   10.32.255.10     lo0.0 10.32.255.13    xxxx      *            0.0.0.0            N/A
```

### Discovery Parsing Logic
```groovy
def vtepSet = [] as Set  // Dedupe VTEPs
output.eachLine { line ->
    // Skip headers
    if (line.startsWith('Logical') || line.trim().isEmpty()) return

    // Parse: RVTEP-IP is the remote VTEP
    def fields = line.split(/\s+/)
    if (fields.size() >= 5) {
        def rvtepIp = fields[4]  // RVTEP-IP column
        if (rvtepIp =~ /^\d+\.\d+\.\d+\.\d+$/ && !vtepSet.contains(rvtepIp)) {
            vtepSet.add(rvtepIp)
            println "${rvtepIp}##VTEP-${rvtepIp}##Remote VTEP####auto.vtep.ip=${rvtepIp}"
        }
    }
}
```

### Collection Script
```bash
show ethernet-switching vxlan-tunnel-end-point remote detail | no-more
```

Or count VNIs per VTEP:
```bash
show ethernet-switching vxlan-tunnel-end-point remote | match <vtep-ip> | count
```

### DataPoints
| Name | Type | Alert | Description | Parse Pattern |
|------|------|-------|-------------|---------------|
| Status | Gauge | `!= 1` | 1=up, 0=down | VTEP in output = 1 |
| VNICount | Gauge | - | VNIs shared with VTEP | Count lines matching VTEP IP |
| TunnelCount | Gauge | - | Active tunnels | Line count for this VTEP |

### Instance Properties
- `auto.vtep.ip` - Remote VTEP loopback IP (wildvalue)
- `auto.vtep.local` - Local VTEP IP (from SVTEP-IP)

### AppliesTo
```
hasCategory("Juniper") && system.sysinfo =~ "QFX"
```

### TODO: Validate on Device
- [ ] SSH to device 217, run `show ethernet-switching vxlan-tunnel-end-point remote | no-more`
- [ ] Confirm remote VTEPs are visible
- [ ] Check if detail output provides more metrics

---

## Phase 4: VNI Interface Mapping DataSource

**File**: `configs/logicmonitor/datasource-vni-interfaces.json`
**Priority**: P3 - Operational visibility (port-to-VNI mapping)
**Note**: Consider if this duplicates existing VNI datasource functionality

### Alternative: Extend Existing VNI DataSource
Instead of new datasource, could add `InterfaceCount` to `Juniper_EVPN_VXLAN`:
- Same VLAN discovery already working
- Add `show vlans <vlan-name> | no-more` to collection
- Parse interface membership

### If New DataSource Needed

### Discovery Script
```bash
show vlans | display set | match "vxlan vni" | no-more
```
(Same as VNI datasource - could reuse discovery)

### Collection Script
```bash
show vlans <vlan-name> extensive | no-more
```

Expected output format:
```
VLAN: VLAN_630439_226, Tag: 226, Interfaces: et-0/0/48.0*, ae0.226*
  VXLAN Enabled
    VNI: 5655
    Encapsulation: vxlan
    Ingress Node Replication Enabled
  Number of interfaces: Tagged 2 (Active 2), Untagged 0 (Active 0)
    et-0/0/48.0*, tagged, trunk
    ae0.226*, tagged, trunk
```

### DataPoints
| Name | Type | Alert | Description | Parse Pattern |
|------|------|-------|-------------|---------------|
| InterfaceCount | Gauge | `< 1` | Ports in this VNI | Count interface lines |
| TaggedCount | Gauge | - | Tagged interfaces | `Tagged (\d+)` |
| UntaggedCount | Gauge | - | Access ports | `Untagged (\d+)` |
| ActiveCount | Gauge | - | Active interfaces | `Active (\d+)` |

### Instance Properties
- `auto.vlan.name` - VLAN name (wildvalue)
- `auto.vni.id` - VNI (link to existing datasource)
- `auto.vlan.tag` - 802.1Q tag

### AppliesTo
```
hasCategory("Juniper") && system.sysinfo =~ "QFX"
```

### Discovery Interval
**60 minutes** - Interface membership changes infrequently

### Decision Point
- **Option A**: Add InterfaceCount to existing `Juniper_EVPN_VXLAN` (simpler)
- **Option B**: Separate datasource (cleaner separation, but more overhead)

Recommend: **Option A** - extend existing datasource in v2.23.0

---

## Phase 5 (Optional): ESI Status

**Only implement if fabric uses multi-homing**

Detection: Check `show evpn instance extensive` for ESI presence

**File**: `configs/logicmonitor/datasource-evpn-esi.json`

### DataPoints
| Name | Type | Alert | Description |
|------|------|-------|-------------|
| ESIState | Gauge | `!= 1` | 1=active, 0=standby/failed |
| DFStatus | Gauge | - | Designated Forwarder status |
| PeerCount | Gauge | `< 2` | Multi-homing peers |

---

## Implementation Order

### Prerequisites (Before Implementation)
1. **SSH Allow Rule CR** - Roll out SSH allow from LOGICMON-POC (10.232.3.14) to DFW test devices
2. **Manual Command Validation** - SSH to device 217, capture sample output for each command
3. **Regex Development** - Build and test regexes against real output

### Step 1: BGP EVPN Peers (Highest Value)
1. SSH to device, capture `show bgp summary | no-more` output
2. Develop discovery regex, validate against output
3. Create `datasource-bgp-evpn.json` (copy structure from datasource-evpn.json)
4. Deploy disabled, test on device 217
5. Verify peer discovery and state detection
6. Enable alerts, deploy to 2-3 more devices
7. Staged rollout to full DFW site

### Step 2: VTEP Peers
1. SSH to device, capture `show ethernet-switching vxlan-tunnel-end-point remote | no-more`
2. Develop discovery regex
3. Create `datasource-evpn-vteps.json`
4. Deploy disabled, test discovery
5. Staged rollout

### Step 3: Interface Mapping (Extend Existing)
1. Add `InterfaceCount` datapoint to existing `Juniper_EVPN_VXLAN`
2. Modify collection script to also run `show vlans <vlan-name> | no-more`
3. Parse interface count from output
4. Version bump to v2.23.0
5. Test on device 217

### Step 4: ESI (If Applicable)
1. SSH to device, run `show evpn instance extensive | no-more`
2. Check for ESI configuration in output
3. If ESI present, create `datasource-evpn-esi.json`
4. If not present, skip this phase

---

## Files to Create/Modify

| File | Action | Priority |
|------|--------|----------|
| `configs/logicmonitor/datasource-bgp-evpn.json` | Create new | P1 |
| `configs/logicmonitor/datasource-evpn-vteps.json` | Create new | P2 |
| `configs/logicmonitor/datasource-evpn.json` | Modify (add InterfaceCount) | P3 |
| `configs/logicmonitor/datasource-evpn-esi.json` | Create new (if ESI used) | P4 |
| `docs/datasource-specs/evpn-fabric-monitoring.md` | Create new | P1 |
| `PLAN.md` | Create in repo root | P0 |

## Files to Keep Unchanged

| File | Reason |
|------|--------|
| `datasource-routing.json` | Unrelated, working |
| `datasource-cluster.json` | Unrelated, SRX-only |

---

## API Tooling for Validation

Use `scripts/manage_lm_modules.py` for testing:

```bash
# Check device info and SSH properties
python scripts/manage_lm_modules.py device 217

# Check datasource status and instances
python scripts/manage_lm_modules.py status 217 Juniper_EVPN_VXLAN

# Trigger discovery (after deploying new datasource)
python scripts/manage_lm_modules.py discover 217 Juniper_EVPN_BGP --wait 60

# List all Juniper datasources
python scripts/manage_lm_modules.py list datasources --filter "Juniper"

# Deploy new datasource
python scripts/manage_lm_modules.py create datasource configs/logicmonitor/datasource-bgp-evpn.json

# Update existing datasource
python scripts/manage_lm_modules.py update datasource 21328204 configs/logicmonitor/datasource-evpn.json
```

### Testing Workflow
1. Create datasource JSON file
2. Deploy with `create datasource` command
3. Note returned ID
4. Check status: `status 217 <datasource-name>`
5. Trigger discovery: `discover 217 <datasource-name>`
6. Verify instances found in LM UI or via status command

---

## SSH Command Safety

All commands are **read-only show commands**:
```
show bgp summary                              # Safe
show bgp neighbor <ip>                        # Safe
show ethernet-switching vxlan-tunnel-end-point # Safe
show vlans extensive                          # Safe
show evpn instance extensive                  # Safe
```

No configuration changes, no writes.

---

## Scale Considerations (20+ Switches)

1. **Collection Timeout**: Set 30-second timeout per SSH command
2. **Connection Pooling**: One SSH session per collection, disconnect after
3. **Discovery Interval**: 60 minutes for interface mapping (infrequent changes)
4. **Rollout**: Test on 1 device -> 3 devices -> full deployment
5. **Monitoring**: Watch collector resource usage during rollout

---

## Alertable Scenarios

### Critical (Immediate Page)
- BGP EVPN peer down (`PeerState != 6`)
- All VTEPs unreachable for a VNI
- Session uptime < 60s (recent crash/flap)

### Warning (4-hour response)
- VTEP count decreased (partial fabric issue)
- MAC table > 80% utilization
- BGP prefix count deviation > 20%

### Info (Dashboard only)
- New VTEP discovered
- New VNI added
- Interface membership changed

---

## Graphs

### BGP EVPN Dashboard
- Peer state timeline (up/down events)
- Prefixes received per peer (stacked area)
- Messages in/out rate

### VTEP Dashboard
- VTEP count per device over time
- MAC distribution across VTEPs
- VTEP reachability heatmap

### VNI Dashboard (existing + new)
- MAC counts per VNI (existing)
- Interface count per VNI (new)
- Customer-filtered views (existing)

---

## Rollout Plan

| Phase | Devices | Duration | Criteria to Proceed |
|-------|---------|----------|---------------------|
| Test | Device 217 only | 1 day | All metrics collecting |
| Pilot | 3 devices | 2 days | No errors, alerts working |
| Staged | 10 devices | 3 days | Performance OK |
| Full | All 20+ | Ongoing | Monitoring stable |

---

## Blocking Items

| Blocker | Status | Owner | Notes |
|---------|--------|-------|-------|
| SSH allow rule CR for DFW devices | Pending | User | Need CR to roll out from 10.232.3.14 to DFW test group |
| Manual command output capture | Pending | User | Need SSH access to validate command output formats |
| ESI usage determination | Unknown | User | Run `show evpn instance` to check for ESI |

---

## Success Criteria

### Phase 1: BGP EVPN (P1)
- [x] `show bgp summary` output captured from device 217
- [x] Discovery regex tested against real output
- [x] `datasource-bgp-evpn.json` created and deployed (ID: 21328210)
- [x] At least 1 BGP EVPN peer discovered on device 217 (Found 2: 10.32.2.21, 10.32.2.22)
- [ ] PeerState alert triggers when peer is not Established (waiting for collection)

### Phase 2: VTEP Peers (P2)
- [ ] `show ethernet-switching vxlan-tunnel-end-point remote` output captured
- [ ] Discovery regex tested
- [x] `datasource-evpn-vteps.json` created and deployed (ID: 21328211)
- [ ] Remote VTEPs discovered - **0 found on device 217** (needs investigation)
- [ ] Status datapoint reflects VTEP reachability

### Phase 3: Interface Mapping (P3)
- [ ] `show vlans <vlan-name>` output analyzed
- [ ] InterfaceCount added to existing VNI datasource
- [ ] v2.23.0 deployed
- [ ] Interface count visible in LM graphs

### Phase 4: ESI (P4 - if applicable)
- [ ] ESI presence confirmed in fabric
- [ ] `datasource-evpn-esi.json` created
- [ ] DF status monitored

### Overall
- [ ] All new datasources collecting data
- [ ] Alerts firing correctly on test failures
- [ ] Graphs showing historical trends
- [ ] No collector resource usage increase > 10%
- [ ] No SSH timeout errors
- [ ] Deployed to all DFW site QFX devices
