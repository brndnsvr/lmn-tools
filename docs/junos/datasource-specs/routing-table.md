# Routing Table Size DataSource Specification

## Overview

Custom LogicMonitor DataSource to track RIB/FIB growth for capacity planning on Juniper MX routers and SRX firewalls.

**Name**: `Juniper_RoutingTable`
**Collection Method**: SNMP + Script
**Collection Interval**: 5 minutes
**Multi-Instance**: Yes (per routing instance)

## AppliesTo

```
system.categories =~ "Juniper" && (system.sysinfo =~ "MX" || system.sysinfo =~ "SRX")
```

## SNMP OIDs

### Standard IP Route Table (RFC 4292)
| OID | Name | Description |
|-----|------|-------------|
| 1.3.6.1.2.1.4.24.6.0 | ipCidrRouteNumber | Total IPv4 routes (deprecated but widely supported) |
| 1.3.6.1.2.1.4.24.7.1 | inetCidrRouteTable | IPv4/IPv6 route table |

### Juniper-Specific Route MIB

> **WARNING:** The OIDs below (`.2636.3.1.13.x`) were documented as routing OIDs but testing revealed they are actually `jnxBoxAnatomy` (chassis component inventory: power supplies, fans, FPCs). Use the standard IP-FORWARD-MIB OID `1.3.6.1.2.1.4.24.6.0` instead for reliable route counts across all Juniper platforms.

| OID | Name | Description | Status |
|-----|------|-------------|--------|
| 1.3.6.1.4.1.2636.3.1.13.1.5 | jnxRtmTableRouteCount | Routes per routing table | ⚠️ Actually jnxBoxAnatomy |
| 1.3.6.1.4.1.2636.3.1.13.1.6 | jnxRtmTableActiveRouteCount | Active routes (used in FIB) | ⚠️ Actually jnxBoxAnatomy |
| 1.3.6.1.4.1.2636.3.1.13.1.7 | jnxRtmTableHiddenRouteCount | Hidden routes | ⚠️ Actually jnxBoxAnatomy |
| 1.3.6.1.4.1.2636.3.1.13.1.8 | jnxRtmTableHoldDownRouteCount | Routes in holddown | ⚠️ Actually jnxBoxAnatomy |

### FIB Statistics (jnxCosMIB related)
| OID | Name | Description |
|-----|------|-------------|
| 1.3.6.1.4.1.2636.3.15.1.1.3 | jnxCosIfqTailDropPkts | Packets dropped due to queue full |

## CLI Commands (Groovy Script)

For per-protocol breakdown and FIB utilization:

```groovy
// Route summary per protocol
def routeSummary = Ssh.exec("show route summary | display json")

// FIB statistics
def fibStats = Ssh.exec("show route forwarding-table summary | display json")

// Per-instance route counts
def instanceRoutes = Ssh.exec("show route instance detail | display json")

// Hardware table utilization (PFE)
def pfeUtil = Ssh.exec("show pfe statistics traffic | display json")
```

## DataPoints

### Device-Level (Aggregate)

| DataPoint | Description | Type | Alert Threshold |
|-----------|-------------|------|-----------------|
| `TotalIPv4Routes` | Total IPv4 routes across all instances | gauge | > baseline + 20% |
| `TotalIPv6Routes` | Total IPv6 routes across all instances | gauge | > baseline + 20% |
| `TotalActiveRoutes` | Active routes installed in FIB | gauge | > baseline + 20% |
| `TotalHiddenRoutes` | Hidden routes (not installed) | gauge | Trending |
| `FIBUtilization` | FIB table usage percentage | gauge | > 80% |
| `PFEMemoryUsed` | PFE memory for routing | gauge | > 80% |

### Instance-Level (per Routing Instance)

| DataPoint | Description | Type | Alert Threshold |
|-----------|-------------|------|-----------------|
| `RouteCount` | Total routes in this instance | gauge | > baseline + 20% |
| `ActiveRoutes` | Active routes (installed in FIB) | gauge | N/A |
| `HiddenRoutes` | Hidden routes | gauge | > 100 |
| `HolddownRoutes` | Routes in holddown state | gauge | > 50 |

### Per-Protocol DataPoints (from CLI parsing)

| DataPoint | Description | Type | Alert Threshold |
|-----------|-------------|------|-----------------|
| `BGPRoutes` | Routes learned via BGP | gauge | Deviation > 10% |
| `OSPFRoutes` | Routes learned via OSPF | gauge | Deviation > 10% |
| `ISISRoutes` | Routes learned via IS-IS | gauge | Deviation > 10% |
| `StaticRoutes` | Manually configured routes | gauge | Change > 5 |
| `DirectRoutes` | Directly connected routes | gauge | Change > 0 |
| `LocalRoutes` | Local routes | gauge | Change > 0 |

## Alert Rules

### Critical (Page)

```
# FIB table nearly full
DataPoint: FIBUtilization > 90
Severity: Critical
Message: "##DEVICE## FIB utilization at ##VALUE##% - risk of route drops"

# Massive route change (possible route leak)
DataPoint: BGPRoutes increased > 50% in 5 minutes
Severity: Critical
Message: "##DEVICE## BGP routes increased by ##DELTA##% - possible route leak"
```

### Warning (Ticket)

```
# FIB filling up
DataPoint: FIBUtilization > 80
Severity: Warning
Message: "##DEVICE## FIB utilization at ##VALUE##% - plan capacity increase"

# Significant route count change
DataPoint: TotalIPv4Routes deviation > 20% from baseline
Severity: Warning
Message: "##DEVICE## IPv4 route count deviated from baseline"

# Unexpected static route change
DataPoint: StaticRoutes change > 5
Severity: Warning
Message: "##DEVICE## static route count changed by ##DELTA##"

# Many hidden routes (possible config issue)
DataPoint: HiddenRoutes > 100
Severity: Warning
Message: "##DEVICE## has ##VALUE## hidden routes - check for config issues"
```

### Info (Log/Trending)

```
# Route table growth trend
DataPoint: TotalActiveRoutes
Severity: Info
Action: Log for capacity planning trending
```

## Discovery Script (Groovy)

```groovy
import com.santaba.agent.groovyapi.expect.Expect
import groovy.json.JsonSlurper

def host = hostProps.get("system.hostname")
def user = hostProps.get("ssh.user")
def pass = hostProps.get("ssh.pass")

def cli = Expect.open(host, user, pass)
cli.send("show route instance | display json\n")
def output = cli.expect(".*\\n")
cli.close()

def json = new JsonSlurper().parseText(output)
def instances = json?."instance-information"?."instance-core"

// Always include master instance
println "master##inet.0"

instances?.each { instance ->
    def name = instance."instance-name"
    // Skip internal instances
    if (name && !name.startsWith("__") && name != "master") {
        def tableName = "${name}.inet.0"
        println "${name}##${tableName}"
    }
}
```

## Collection Script (Groovy)

```groovy
import com.santaba.agent.groovyapi.snmp.Snmp
import com.santaba.agent.groovyapi.expect.Expect
import groovy.json.JsonSlurper

def host = hostProps.get("system.hostname")
def wildvalue = instanceProps.get("wildvalue") // routing instance name

// SNMP for standard route counts
def snmp = Snmp.open(host, hostProps)

// Walk route table entries for this instance
def routeTableOid = "1.3.6.1.4.1.2636.3.1.13.1" // jnxRtmTableEntry
def routeCount = 0
def activeCount = 0
def hiddenCount = 0

snmp.walk(routeTableOid).each { oid, value ->
    // Parse instance from OID and match
    // Structure: jnxRtmTableRouteCount.instanceIndex
    if (oid.contains(".5.")) {
        routeCount = value.toInteger()
    }
    if (oid.contains(".6.")) {
        activeCount = value.toInteger()
    }
    if (oid.contains(".7.")) {
        hiddenCount = value.toInteger()
    }
}

// CLI for per-protocol breakdown
def cli = Expect.open(host, hostProps.get("ssh.user"), hostProps.get("ssh.pass"))
cli.send("show route summary table ${wildvalue}.inet.0 | display json\n")
def output = cli.expect(".*\\n")
cli.close()

def json = new JsonSlurper().parseText(output)
def protocols = json?."route-summary-information"?."route-table"?."protocols"

def bgpRoutes = 0
def ospfRoutes = 0
def staticRoutes = 0
def directRoutes = 0

protocols?.each { proto ->
    def name = proto."protocol-name"?.toLowerCase()
    def count = proto."protocol-route-count"?.toInteger() ?: 0

    switch(name) {
        case "bgp": bgpRoutes = count; break
        case "ospf": ospfRoutes = count; break
        case "static": staticRoutes = count; break
        case "direct": directRoutes = count; break
    }
}

println "RouteCount=${routeCount}"
println "ActiveRoutes=${activeCount}"
println "HiddenRoutes=${hiddenCount}"
println "BGPRoutes=${bgpRoutes}"
println "OSPFRoutes=${ospfRoutes}"
println "StaticRoutes=${staticRoutes}"
println "DirectRoutes=${directRoutes}"

snmp.close()
```

## FIB Utilization Collection (Device-Level)

```groovy
import com.santaba.agent.groovyapi.expect.Expect
import groovy.json.JsonSlurper

def host = hostProps.get("system.hostname")
def user = hostProps.get("ssh.user")
def pass = hostProps.get("ssh.pass")

def cli = Expect.open(host, user, pass)

// Get FIB statistics
cli.send("show route forwarding-table summary\n")
def fibOutput = cli.expect(".*\\n")

// Get PFE memory stats (MX specific)
cli.send("show pfe statistics traffic\n")
def pfeOutput = cli.expect(".*\\n")

cli.close()

// Parse FIB utilization
// Example output parsing (actual format varies by platform)
def fibMatch = fibOutput =~ /(\d+)\s+routes.*(\d+)%\s+used/
if (fibMatch) {
    def routes = fibMatch[0][1].toInteger()
    def utilPct = fibMatch[0][2].toInteger()
    println "FIBUtilization=${utilPct}"
}

// Parse PFE memory (platform-specific)
def pfeMatch = pfeOutput =~ /Memory used:\s+(\d+)%/
if (pfeMatch) {
    println "PFEMemoryUsed=${pfeMatch[0][1]}"
}
```

## Platform-Specific Considerations

### MX Series
- Multiple PFEs (Trio chipset), each with own FIB capacity
- Use `show chassis fpc` to identify FPC types
- FIB limits vary: MX80 (1M), MX240/480/960 (2-4M per FPC)

### SRX Series
- Unified TCAM for routes and policies
- `show security flow statistics` for flow table usage
- Branch SRX has lower route limits than data center models

### Capacity Limits Reference

| Platform | FIB IPv4 | FIB IPv6 |
|----------|----------|----------|
| MX80 | 1M | 512K |
| MX240 (Trio) | 2M | 1M |
| MX480 (Trio) | 4M | 2M |
| SRX340 | 256K | 128K |
| SRX1500 | 1M | 512K |
| SRX4600 | 2M | 1M |

## Properties to Set

| Property | Description | Example |
|----------|-------------|---------|
| `routing.baseline.ipv4` | Expected IPv4 route count | 850000 |
| `routing.baseline.bgp` | Expected BGP route count | 800000 |
| `routing.fib.limit` | Platform FIB capacity | 2000000 |
| `routing.warn.deviation` | Alert threshold % | 20 |

## Baseline Establishment

Before enabling alerting:

1. Deploy datasource in collection-only mode (no alerts)
2. Collect data for 1-2 weeks
3. Run baseline script (see `scripts/baseline-routes.py`)
4. Set device properties with baseline values
5. Enable threshold-based alerting

## Testing Procedure

1. Deploy datasource disabled on POC router
2. Enable and verify discovery finds all routing instances
3. Validate route counts match `show route summary`
4. Compare FIB utilization with `show route forwarding-table summary`
5. Test alert by temporarily lowering threshold
6. Verify collection doesn't impact device CPU

## Capacity Planning Report

Use collected data to generate quarterly capacity planning reports:

```sql
-- LogicMonitor Report Query (example)
SELECT
    device_name,
    AVG(FIBUtilization) as avg_util,
    MAX(FIBUtilization) as peak_util,
    AVG(TotalActiveRoutes) as avg_routes,
    MAX(TotalActiveRoutes) as peak_routes
FROM datasource_data
WHERE datasource_name = 'Juniper_RoutingTable'
AND time > now() - 90d
GROUP BY device_name
ORDER BY peak_util DESC
```

## References

- [Juniper Route Table MIB](https://www.juniper.net/documentation/en_US/junos/topics/reference/general/snmp-mib-routing.html)
- [MX Series FIB Scaling](https://www.juniper.net/documentation/en_US/junos/topics/concept/mx-series-forwarding-table-scaling.html)
- [SRX Series Scaling Limits](https://www.juniper.net/documentation/en_US/release-independent/junos/topics/reference/general/srx-series-scaling-guidelines.html)
