# EVPN-VXLAN Alert Response Runbook

Procedures for responding to alerts from the `Juniper_EVPN_VXLAN` custom datasource.

---

## Alert Summary

| Alert | Severity | Response Time | Escalation |
|-------|----------|---------------|------------|
| BGP EVPN Peer Down | Critical | 15 min | Immediate |
| VNI Status Down | Critical | 15 min | Immediate |
| VTEP Count Low | Warning | 4 hours | Next business day |
| MAC Table High | Warning | 4 hours | Next business day |
| Route Count Deviation | Info | 24 hours | Review weekly |

---

## Critical: BGP EVPN Peer Down

### Alert Details
- **DataPoint**: `BGPEvpnPeersDown > 0`
- **Impact**: Partial or complete fabric connectivity loss
- **Urgency**: Immediate

### Triage Steps

1. **Identify the affected peer**:
   ```junos
   show bgp summary | match EVPN
   show bgp neighbor <peer-ip> | match "EVPN|State"
   ```

2. **Check EVPN routes**:
   ```junos
   show route table bgp.evpn.0 summary
   show evpn database
   ```

3. **Verify underlay connectivity**:
   ```junos
   ping <peer-ip> source <loopback-ip>
   traceroute <peer-ip>
   ```

### Common Causes & Resolutions

#### Cause: Underlay network issue
```junos
# Check OSPF/ISIS adjacencies
show ospf neighbor
show isis adjacency

# Check physical interface
show interfaces <uplink> extensive | match "errors|drops"
```
**Resolution**: Fix underlay routing or physical connectivity

#### Cause: BGP configuration issue
```junos
# Verify BGP group configuration
show configuration protocols bgp group <evpn-group>

# Check for policy changes
show configuration policy-options policy-statement <evpn-policy>
```
**Resolution**: Restore correct BGP configuration

#### Cause: Resource exhaustion
```junos
# Check memory
show system memory

# Check route table limits
show route summary
```
**Resolution**: Investigate memory leak or reduce route scale

### Escalation

If not resolved within 30 minutes:
1. Page on-call network engineer
2. Open bridge call with fabric team
3. Notify affected application owners

---

## Critical: VNI Status Down

### Alert Details
- **DataPoint**: `Status != 1 (up)` for any VNI instance
- **Impact**: Layer 2 connectivity loss for affected VLAN
- **Urgency**: Immediate

### Triage Steps

1. **Identify affected VNI**:
   ```junos
   show evpn instance extensive | match "Instance|State"
   show evpn database instance <vni-name>
   ```

2. **Check VXLAN tunnels**:
   ```junos
   show ethernet-switching vxlan-tunnel-end-point remote
   show interfaces vtep
   ```

3. **Verify IRB interface (if applicable)**:
   ```junos
   show interfaces irb.<vni-id>
   show arp interface irb.<vni-id>
   ```

### Common Causes & Resolutions

#### Cause: All VTEPs unreachable
```junos
# Check if any remote VTEPs are up
show ethernet-switching vxlan-tunnel-end-point remote | match "Remote"
```
**Resolution**: Fix underlay connectivity (see BGP EVPN Peer Down)

#### Cause: Local IRB/VLAN misconfiguration
```junos
# Verify VLAN configuration
show vlans <vlan-name> extensive

# Check for interface membership
show ethernet-switching table vlan <vlan-name>
```
**Resolution**: Correct VLAN/IRB configuration

#### Cause: VNI mapping issue
```junos
# Verify VNI to VLAN mapping
show configuration vlans <vlan-name> | match vni
```
**Resolution**: Correct VNI-to-VLAN mapping

---

## Warning: VTEP Count Low

### Alert Details
- **DataPoint**: `VTEPPeerCount < expected`
- **Impact**: Reduced redundancy, potential single point of failure
- **Urgency**: 4 hours

### Triage Steps

1. **List current VTEPs**:
   ```junos
   show ethernet-switching vxlan-tunnel-end-point remote
   ```

2. **Compare to expected**:
   - Check documentation for expected VTEP count
   - Verify property `evpn.expected.vteps` value

3. **Identify missing VTEP**:
   ```junos
   # Compare to list of leaf switches
   show bgp summary | match EVPN
   ```

### Common Causes & Resolutions

#### Cause: Leaf switch down
**Resolution**: Investigate leaf switch health, restore if needed

#### Cause: Planned maintenance
**Resolution**: Verify maintenance window, no action needed

#### Cause: Threshold misconfiguration
```
# In LogicMonitor, check device property
evpn.expected.vteps = <correct-value>
```
**Resolution**: Update expected count property

---

## Warning: MAC Table High

### Alert Details
- **DataPoint**: `MACCount > 80%` of limit
- **Impact**: Risk of MAC table exhaustion
- **Urgency**: 4 hours

### Triage Steps

1. **Check current MAC table size**:
   ```junos
   show ethernet-switching table summary
   show ethernet-switching table count
   ```

2. **Identify large consumers**:
   ```junos
   show ethernet-switching table | count
   show ethernet-switching table vlan <vlan-name> | count
   ```

3. **Check for MAC flapping**:
   ```junos
   show log messages | match "MAC|moved|flap"
   ```

### Common Causes & Resolutions

#### Cause: MAC address leak/loop
```junos
# Check for duplicate MACs
show ethernet-switching table | match <suspicious-mac>

# Check STP status
show spanning-tree interface
```
**Resolution**: Identify and break network loop

#### Cause: Legitimate growth
**Resolution**: Plan capacity upgrade or implement MAC aging tuning

#### Cause: VM sprawl
**Resolution**: Work with virtualization team to consolidate or segment

### Capacity Planning

Current limits by platform:
| Platform | MAC Limit |
|----------|-----------|
| QFX5100 | 288K |
| QFX5110 | 288K |
| QFX5120 | 512K |
| QFX10K | 2M |

---

## Info: Route Count Deviation

### Alert Details
- **DataPoint**: `Type2Routes` or `Type5Routes` deviated > 20%
- **Impact**: Informational - may indicate network changes
- **Urgency**: Review within 24 hours

### Triage Steps

1. **Check route table**:
   ```junos
   show route table bgp.evpn.0 summary
   show evpn database summary
   ```

2. **Compare to baseline**:
   - Review LogicMonitor historical data
   - Check if change correlates with known event

3. **Investigate if unexpected**:
   ```junos
   # Recent route changes
   show route table bgp.evpn.0 | match "recent"
   show log messages | match "BGP|route"
   ```

### Common Causes

- **Legitimate**: New VLANs added, hosts provisioned
- **Problematic**: Route leak, misconfig, security incident

### Actions

- If legitimate change: Update baseline property
- If unexpected: Investigate root cause, escalate if needed

---

## Useful Commands Reference

### Health Check Commands
```junos
# Overall EVPN status
show evpn instance extensive
show evpn database summary

# BGP EVPN peers
show bgp summary | match EVPN
show bgp neighbor | match "EVPN|Established"

# VXLAN tunnels
show ethernet-switching vxlan-tunnel-end-point remote
show interfaces vtep

# MAC/ARP tables
show ethernet-switching table summary
show evpn arp-table
```

### Troubleshooting Commands
```junos
# BGP detailed
show bgp neighbor <ip> extensive

# EVPN route details
show route table bgp.evpn.0 extensive

# Underlay connectivity
show ospf neighbor extensive
show isis adjacency extensive

# Logs
show log messages | match "EVPN|BGP|VXLAN"
```

---

## Escalation Contacts

| Level | Contact | Response Time |
|-------|---------|---------------|
| L1 | NOC | Immediate |
| L2 | Network Engineering | 30 min |
| L3 | Fabric SME | 1 hour |
| Vendor | JTAC | Per contract |
