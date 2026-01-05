# EVPN-VXLAN Monitoring DataSource Specification

## Overview

Custom LogicMonitor DataSource to monitor EVPN-VXLAN fabric health on Juniper QFX switches.

**Name**: `Juniper_EVPN_VXLAN`
**Collection Method**: SNMP + Script
**Collection Interval**: 5 minutes
**Multi-Instance**: Yes (per VNI)

## AppliesTo

```
system.categories =~ "Juniper" && system.sysinfo =~ "QFX"
```

Optionally, add property-based filtering:
```
system.categories =~ "Juniper" && system.sysinfo =~ "QFX" && auto.evpn.enabled == "true"
```

## SNMP OIDs

### VXLAN Tunnel Table
| OID | Name | Description |
|-----|------|-------------|
| 1.3.6.1.4.1.2636.3.72.1.1.1.2 | jnxVxlanTunnelRemoteIp | Remote VTEP IP address |
| 1.3.6.1.4.1.2636.3.72.1.1.1.3 | jnxVxlanTunnelStatus | Tunnel operational state |
| 1.3.6.1.4.1.2636.3.72.1.1.1.4 | jnxVxlanTunnelVNI | VNI identifier |

### L2 Learning Table
| OID | Name | Description |
|-----|------|-------------|
| 1.3.6.1.4.1.2636.3.48.1.3.1.1.5 | jnxL2aldVlanFdbStatus | MAC learning status per VLAN |

### BGP EVPN (Standard BGP MIB with filtering)
| OID | Name | Description |
|-----|------|-------------|
| 1.3.6.1.2.1.15.3.1.2 | bgpPeerState | BGP peer state (filter for EVPN AFI/SAFI) |
| 1.3.6.1.2.1.15.3.1.9 | bgpPeerInUpdates | Received BGP updates |

## CLI Commands (Groovy Script)

For metrics not available via SNMP, parse CLI output:

```groovy
// show evpn database
def evpnDb = Ssh.exec("show evpn database summary | display json")

// show evpn statistics
def evpnStats = Ssh.exec("show evpn statistics | display json")

// show evpn instance
def evpnInstance = Ssh.exec("show evpn instance extensive | display json")
```

## DataPoints

### Instance-Level (per VNI)

| DataPoint | Description | Type | Alert Threshold |
|-----------|-------------|------|-----------------|
| `Status` | VNI operational state | enum | != 1 (up) |
| `VTEPCount` | Active remote VTEPs | gauge | < expected |
| `MACCount` | Learned MAC addresses | gauge | > 80% of limit |
| `Type2Routes` | EVPN Type-2 (MAC/IP) routes | gauge | Baseline deviation |
| `Type5Routes` | EVPN Type-5 (IP prefix) routes | gauge | Baseline deviation |
| `ARPSuppressionHits` | ARP suppression cache hits | counter | Trending |

### Device-Level (aggregate)

| DataPoint | Description | Type | Alert Threshold |
|-----------|-------------|------|-----------------|
| `TotalVNIs` | Count of configured VNIs | gauge | < expected |
| `TotalVTEPs` | Unique remote VTEP count | gauge | < expected |
| `TotalMACEntries` | Total MAC table entries | gauge | > 80% of limit |
| `BGPEvpnPeersUp` | EVPN BGP peers in Established | gauge | < expected |
| `BGPEvpnPeersDown` | EVPN BGP peers NOT Established | gauge | > 0 |

## Alert Thresholds

### Critical (Page)
- `BGPEvpnPeersDown > 0` - Any EVPN BGP peer down
- `Status != up` for any VNI - VNI failure

### Warning (Ticket)
- `TotalVNIs < ##evpn.expected.vnis##` - Missing VNIs
- `MACCount > ##evpn.mac.warn.threshold##` - MAC table filling up
- `Type2Routes` deviation > 20% from baseline

### Info (Log)
- VNI count changes
- New VTEP discovered

## Discovery Script (Groovy)

```groovy
import com.santaba.agent.groovyapi.expect.Expect
import com.santaba.agent.groovyapi.snmp.Snmp
import groovy.json.JsonSlurper

def host = hostProps.get("system.hostname")
def user = hostProps.get("ssh.user")
def pass = hostProps.get("ssh.pass")

// Check if EVPN is configured
def cli = Expect.open(host, user, pass)
cli.send("show evpn instance brief | display json\n")
def output = cli.expect(".*\\n")
cli.close()

def json = new JsonSlurper().parseText(output)
def instances = json?."evpn-instance-information"?."evpn-instance"

if (instances) {
    instances.each { instance ->
        def vni = instance."evpn-instance-name"
        println "${vni}##${vni}"
    }
}
```

## Collection Script (Groovy)

```groovy
import com.santaba.agent.groovyapi.snmp.Snmp
import groovy.json.JsonSlurper

def host = hostProps.get("system.hostname")
def wildvalue = instanceProps.get("wildvalue") // VNI name

// Collect via SNMP where possible
def snmpSession = Snmp.open(host, hostProps.get("snmp.community"))

// Get VXLAN tunnel count for this VNI
def vtepCount = 0
def tunnelTable = snmpSession.walk("1.3.6.1.4.1.2636.3.72.1.1.1")
tunnelTable.each { oid, value ->
    if (oid.contains(".4.${wildvalue}")) { // VNI column
        vtepCount++
    }
}

// Collect CLI metrics for detailed stats
def cli = Expect.open(host, hostProps.get("ssh.user"), hostProps.get("ssh.pass"))
cli.send("show evpn database instance ${wildvalue} summary | display json\n")
def output = cli.expect(".*\\n")
cli.close()

def json = new JsonSlurper().parseText(output)
def macCount = json?."evpn-database-information"?."evpn-database-count" ?: 0

// Output datapoints
println "VTEPCount=${vtepCount}"
println "MACCount=${macCount}"

snmpSession.close()
```

## Properties to Set

| Property | Description | Example |
|----------|-------------|---------|
| `auto.evpn.enabled` | Auto-discovered EVPN status | true/false |
| `evpn.expected.vnis` | Expected VNI count | 50 |
| `evpn.expected.vteps` | Expected VTEP count | 8 |
| `evpn.mac.warn.threshold` | MAC table warning % | 80 |

## Testing Procedure

1. Deploy datasource disabled
2. Enable on single QFX in POC environment
3. Verify discovery finds all VNIs
4. Check collection returns valid data
5. Validate SNMP poll time < 30 seconds
6. Review device CPU impact during collection

## Limitations

- Some metrics require CLI access (Groovy script)
- Type-2/Type-5 route counts may require parsing `show route summary`
- Very large fabrics may need increased collection interval

## References

- [Juniper EVPN-VXLAN Configuration Guide](https://www.juniper.net/documentation/en_US/junos/topics/concept/evpn-vxlan-understanding.html)
- [jnxVxlanMIB](https://www.juniper.net/documentation/en_US/junos/topics/reference/general/snmp-mib-explorer.html)
- [LogicMonitor Groovy Scripting](https://www.logicmonitor.com/support/datasources/scripted-data-collection)
