# SRX Chassis Cluster DataSource Specification

## Overview

Custom LogicMonitor DataSource to monitor SRX firewall HA cluster status, redundancy groups, and failover events.

**Name**: `Juniper_SRX_ChassisCluster`
**Collection Method**: SNMP + Script
**Collection Interval**: 1 minute (critical monitoring)
**Multi-Instance**: Yes (per Redundancy Group)

## AppliesTo

```
system.categories =~ "Juniper" && system.sysinfo =~ "SRX" && auto.cluster_mode == "true"
```

The `auto.cluster_mode` property should be set by a PropertySource that runs:
```
show chassis cluster status | match "Cluster ID"
```

## SNMP OIDs

### Chassis Cluster Table (jnxJsChassisClusterMIB)
| OID | Name | Description |
|-----|------|-------------|
| 1.3.6.1.4.1.2636.3.39.1.12.1.1.1.2 | jnxJsChassisClusterStatus | Cluster operational state |
| 1.3.6.1.4.1.2636.3.39.1.12.1.1.1.3 | jnxJsChassisClusterId | Cluster ID |
| 1.3.6.1.4.1.2636.3.39.1.12.1.1.1.4 | jnxJsChassisClusterNodeId | This node's ID (0 or 1) |

### Redundancy Group Table
| OID | Name | Description |
|-----|------|-------------|
| 1.3.6.1.4.1.2636.3.39.1.12.1.2.1.2 | jnxJsRedundancyGroupId | RG number (0=control, 1+=data) |
| 1.3.6.1.4.1.2636.3.39.1.12.1.2.1.3 | jnxJsRedundancyGroupStatus | RG state (primary/secondary/...) |
| 1.3.6.1.4.1.2636.3.39.1.12.1.2.1.4 | jnxJsRedundancyGroupPriority | Configured priority |
| 1.3.6.1.4.1.2636.3.39.1.12.1.2.1.5 | jnxJsRedundancyGroupWeight | Current priority weight |
| 1.3.6.1.4.1.2636.3.39.1.12.1.2.1.6 | jnxJsRedundancyGroupPreempt | Preemption enabled |

### Failover Statistics
| OID | Name | Description |
|-----|------|-------------|
| 1.3.6.1.4.1.2636.3.39.1.12.1.3.1.2 | jnxJsChassisClusterSwitchoverCount | Total failover events |
| 1.3.6.1.4.1.2636.3.39.1.12.1.3.1.3 | jnxJsChassisClusterSwitchoverTime | Epoch of last failover |
| 1.3.6.1.4.1.2636.3.39.1.12.1.3.1.4 | jnxJsChassisClusterSwitchoverReason | Reason for last failover |

### Control/Fabric Link Status
| OID | Name | Description |
|-----|------|-------------|
| 1.3.6.1.4.1.2636.3.39.1.12.1.4.1.2 | jnxJsChassisClusterControlLinkStatus | Control plane link state |
| 1.3.6.1.4.1.2636.3.39.1.12.1.4.1.3 | jnxJsChassisClusterFabricLinkStatus | Data plane fabric state |

## CLI Commands (Groovy Script)

For comprehensive status not in MIB:

```groovy
// Primary cluster status
def clusterStatus = Ssh.exec("show chassis cluster status | display json")

// Detailed RG info
def rgInfo = Ssh.exec("show chassis cluster information | display json")

// Interface monitoring status
def ifMonitor = Ssh.exec("show chassis cluster interfaces | display json")

// Statistics including failover history
def stats = Ssh.exec("show chassis cluster statistics | display json")
```

## DataPoints

### Device-Level (Overall Cluster Health)

| DataPoint | Description | Type | Alert Threshold |
|-----------|-------------|------|-----------------|
| `ClusterEnabled` | Cluster mode active | enum | != 1 (enabled) |
| `ClusterHealthy` | Overall cluster health | enum | != 1 (healthy) |
| `PeerReachable` | Peer node reachability | enum | != 1 (reachable) |
| `ControlLinkUp` | Control plane link status | enum | != 1 (up) |
| `FabricLinkUp` | Data plane fabric status | enum | != 1 (up) |
| `TotalFailovers` | Cumulative failover count | counter | Delta > 0 |
| `LastFailoverAge` | Seconds since last failover | gauge | < 3600 (recent) |

### Instance-Level (per Redundancy Group)

| DataPoint | Description | Type | Alert Threshold |
|-----------|-------------|------|-----------------|
| `RGStatus` | RG state (0=unknown, 1=primary, 2=secondary, 3=disabled) | enum | State change |
| `RGPriority` | Configured priority value | gauge | N/A |
| `RGWeight` | Current priority weight | gauge | Unexpected change |
| `RGPreempt` | Preemption enabled | enum | N/A |
| `RGFailovers` | Failovers for this RG | counter | Delta > 0 |

## Alert Rules

### Critical (Page Immediately)

```
# Cluster health degraded
DataPoint: ClusterHealthy != 1
Severity: Critical
Message: "SRX Cluster ##DEVICE## health degraded"

# Control link down
DataPoint: ControlLinkUp != 1
Severity: Critical
Message: "SRX Cluster ##DEVICE## control link DOWN"

# Fabric link down
DataPoint: FabricLinkUp != 1
Severity: Critical
Message: "SRX Cluster ##DEVICE## fabric link DOWN"

# Peer unreachable
DataPoint: PeerReachable != 1
Severity: Critical
Message: "SRX Cluster ##DEVICE## peer node UNREACHABLE"

# Failover occurred
DataPoint: TotalFailovers (delta > 0 in last 5 min)
Severity: Critical
Message: "SRX Cluster ##DEVICE## FAILOVER detected"
```

### Warning (Ticket)

```
# RG state change
DataPoint: RGStatus changed
Severity: Warning
Message: "SRX Cluster ##DEVICE## RG##WILDVALUE## state changed to ##VALUE##"

# RG weight changed (interface down?)
DataPoint: RGWeight decreased
Severity: Warning
Message: "SRX Cluster ##DEVICE## RG##WILDVALUE## priority weight decreased"

# Recent failover (within last hour)
DataPoint: LastFailoverAge < 3600
Severity: Warning
Message: "SRX Cluster ##DEVICE## had failover within last hour"
```

## Discovery Script (Groovy)

```groovy
import com.santaba.agent.groovyapi.expect.Expect
import groovy.json.JsonSlurper

def host = hostProps.get("system.hostname")
def user = hostProps.get("ssh.user")
def pass = hostProps.get("ssh.pass")

def cli = Expect.open(host, user, pass)
cli.send("show chassis cluster status | display json\n")
def output = cli.expect(".*\\n")
cli.close()

def json = new JsonSlurper().parseText(output)
def rgList = json?."chassis-cluster-status"?."redundancy-group"

if (rgList) {
    rgList.each { rg ->
        def rgId = rg."redundancy-group-id"
        def rgName = rgId == "0" ? "RG0-Control" : "RG${rgId}-Data"
        println "${rgId}##${rgName}"
    }
}
```

## Collection Script (Groovy)

```groovy
import com.santaba.agent.groovyapi.snmp.Snmp
import com.santaba.agent.groovyapi.expect.Expect
import groovy.json.JsonSlurper

def host = hostProps.get("system.hostname")
def wildvalue = instanceProps.get("wildvalue") // RG ID

// SNMP collection
def snmp = Snmp.open(host, hostProps)
def rgStatusOid = "1.3.6.1.4.1.2636.3.39.1.12.1.2.1.3.${wildvalue}"
def rgWeightOid = "1.3.6.1.4.1.2636.3.39.1.12.1.2.1.5.${wildvalue}"

def rgStatus = snmp.get(rgStatusOid)
def rgWeight = snmp.get(rgWeightOid)

// CLI for additional detail
def cli = Expect.open(host, hostProps.get("ssh.user"), hostProps.get("ssh.pass"))
cli.send("show chassis cluster status redundancy-group ${wildvalue} | display json\n")
def output = cli.expect(".*\\n")
cli.close()

def json = new JsonSlurper().parseText(output)

// Map status values
def statusMap = [
    "primary": 1,
    "secondary": 2,
    "secondary-hold": 2,
    "disabled": 3,
    "unknown": 0
]

def statusText = json?."chassis-cluster-status"?."redundancy-group"?[0]?."device-stats"?."redundancy-group-status" ?: "unknown"
def statusNum = statusMap.get(statusText.toLowerCase(), 0)

println "RGStatus=${statusNum}"
println "RGWeight=${rgWeight}"

snmp.close()
```

## PropertySource for Cluster Detection

Create a PropertySource to auto-detect cluster mode:

**Name**: `Juniper_SRX_ClusterDetect`
**AppliesTo**: `system.categories =~ "Juniper" && system.sysinfo =~ "SRX"`

```groovy
import com.santaba.agent.groovyapi.expect.Expect

def host = hostProps.get("system.hostname")
def user = hostProps.get("ssh.user")
def pass = hostProps.get("ssh.pass")

try {
    def cli = Expect.open(host, user, pass)
    cli.send("show chassis cluster status | match 'Cluster ID'\n")
    def output = cli.expect(".*\\n", 10000)
    cli.close()

    if (output =~ /Cluster ID:\s*\d+/) {
        println "auto.cluster_mode=true"
        // Extract cluster ID
        def clusterId = (output =~ /Cluster ID:\s*(\d+)/)[0][1]
        println "auto.cluster_id=${clusterId}"
    } else {
        println "auto.cluster_mode=false"
    }
} catch (Exception e) {
    println "auto.cluster_mode=false"
}
```

## Testing Procedure

1. Deploy PropertySource first to detect cluster mode
2. Verify `auto.cluster_mode` property is set correctly
3. Deploy DataSource disabled
4. Enable on single SRX cluster pair in POC
5. Verify discovery finds all RGs (RG0 + data RGs)
6. Simulate failover in POC and verify alerts trigger
7. Check SNMP poll time < 15 seconds
8. Verify 1-minute collection doesn't impact device

## Manual Failover Test Commands

```junos
# Force failover of RG1 to secondary
request chassis cluster failover redundancy-group 1 node 1

# Check status after
show chassis cluster status

# Reset to normal (let priority decide)
request chassis cluster failover reset redundancy-group 1
```

## Important Considerations

- **1-minute polling**: Cluster state is critical; fast detection needed
- **Dual-node awareness**: Each SRX reports its own view; correlate with peer
- **Preemption**: If enabled, RGs may flip back after failover
- **Split-brain**: Control link failure requires manual intervention

## References

- [Juniper Chassis Cluster Admin Guide](https://www.juniper.net/documentation/en_US/junos/topics/concept/chassis-cluster-srx-understanding.html)
- [jnxJsChassisClusterMIB](https://www.juniper.net/documentation/en_US/junos/topics/reference/general/snmp-mib-js-chassis-cluster.html)
- [SRX Cluster Troubleshooting](https://www.juniper.net/documentation/en_US/junos/topics/task/troubleshooting/chassis-cluster-srx.html)
