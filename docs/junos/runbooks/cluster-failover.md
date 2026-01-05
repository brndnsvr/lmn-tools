# SRX Chassis Cluster Alert Response Runbook

Procedures for responding to alerts from the `Juniper_SRX_ChassisCluster` custom datasource.

---

## Alert Summary

| Alert | Severity | Response Time | Escalation |
|-------|----------|---------------|------------|
| Cluster Health Degraded | Critical | 5 min | Immediate |
| Control Link Down | Critical | 5 min | Immediate |
| Fabric Link Down | Critical | 5 min | Immediate |
| Peer Unreachable | Critical | 5 min | Immediate |
| Failover Detected | Critical | 15 min | Immediate |
| RG State Changed | Warning | 30 min | Business hours |
| RG Weight Decreased | Warning | 1 hour | Business hours |

---

## Critical: Cluster Health Degraded

### Alert Details
- **DataPoint**: `ClusterHealthy != 1`
- **Impact**: High availability compromised
- **Urgency**: Immediate - single point of failure risk

### Triage Steps

1. **Check cluster status on BOTH nodes**:
   ```junos
   show chassis cluster status
   ```

2. **Identify the specific issue**:
   ```junos
   show chassis cluster information
   show chassis cluster interfaces
   ```

3. **Check for recent events**:
   ```junos
   show log messages | match "cluster|failover|redundancy"
   ```

### Expected Healthy Output
```
Monitor Failure codes:
    CS  Cold Sync monitoring        FL  Fabric Connection monitoring
    GR  GRES monitoring             HW  Hardware monitoring
    IF  Interface monitoring        IP  IP monitoring
    LB  Loopback monitoring         MB  Mbuf monitoring
    NH  Nexthop monitoring          NP  NPC monitoring
    SP  SPU monitoring              SM  Schedule monitoring
    CF  Config Sync monitoring

Cluster ID: 1
Node   Priority Status         Preempt Manual   Monitor-failures

Redundancy group: 0 , Failover count: 1
node0  100      primary        no      no       None
node1  1        secondary      no      no       None

Redundancy group: 1 , Failover count: 0
node0  100      primary        no      no       None
node1  1        secondary      no      no       None
```

### Common Causes & Resolutions

#### Cause: Monitor failure
Look for codes in `Monitor-failures` column:
- **IF**: Interface monitoring failure
- **IP**: IP monitoring failure
- **HW**: Hardware issue
- **SP**: SPU monitoring failure

```junos
# Check monitored interfaces
show chassis cluster interfaces

# Check IP monitoring
show configuration groups node0 interfaces | match monitor
show configuration groups node1 interfaces | match monitor
```
**Resolution**: Fix underlying interface/IP issue

#### Cause: Node in unexpected state
**Resolution**: May need manual intervention - see Failover section

---

## Critical: Control Link Down

### Alert Details
- **DataPoint**: `ControlLinkUp != 1`
- **Impact**: CRITICAL - Risk of split-brain
- **Urgency**: Immediate - potential dual-primary scenario

### What is the Control Link?
- Carries heartbeats between nodes
- Synchronizes configuration
- Coordinates failover decisions
- Usually `em0` or dedicated interface

### Triage Steps

1. **Check control link status**:
   ```junos
   show chassis cluster control-plane statistics
   show chassis cluster information detail | match "Control link"
   ```

2. **Check physical interface**:
   ```junos
   show interfaces em0 extensive
   # or
   show interfaces fxp1 extensive
   ```

3. **Verify cable connectivity**:
   - Physical inspection of control link cable
   - Check switch port if going through a switch (not recommended)

### Resolution Steps

1. **If cable issue**: Replace/reseat cable
2. **If interface issue**: Check for errors, may need RMA
3. **If switch issue**: Bypass switch - direct connection required

### CRITICAL WARNING
**Split-brain risk**: If control link is down AND both nodes think they're primary:
1. Do NOT make config changes
2. Identify which node should be primary
3. Gracefully disable cluster on secondary:
   ```junos
   # On secondary node
   request chassis cluster disable
   ```

---

## Critical: Fabric Link Down

### Alert Details
- **DataPoint**: `FabricLinkUp != 1`
- **Impact**: Session sync broken, asymmetric traffic may fail
- **Urgency**: Immediate

### What is the Fabric Link?
- Carries session state synchronization
- Carries inter-chassis data traffic (reth transit)
- Usually multiple physical links in LAG (`fab0`, `fab1`)

### Triage Steps

1. **Check fabric link status**:
   ```junos
   show chassis cluster data-plane statistics
   show chassis cluster information detail | match "Fabric"
   ```

2. **Check fabric interfaces**:
   ```junos
   show interfaces fab0
   show interfaces fab1
   ```

3. **Check child links if LAG**:
   ```junos
   show lacp interfaces
   show interfaces ae<x> extensive
   ```

### Resolution Steps

1. **Partial fabric down** (some links still up):
   - Less urgent but still needs attention
   - Identify failed member links
   - Replace cable/SFP as needed

2. **Complete fabric down**:
   - Session sync will fail
   - All sessions will be on primary only
   - Failover will cause session drops
   - Fix urgently!

---

## Critical: Peer Unreachable

### Alert Details
- **DataPoint**: `PeerReachable != 1`
- **Impact**: Cluster effectively split
- **Urgency**: Immediate

### Triage Steps

1. **Check cluster status**:
   ```junos
   show chassis cluster status
   ```

2. **Check both control and fabric**:
   ```junos
   show chassis cluster statistics
   ```

3. **Verify peer node is up**:
   - Check physical access to peer
   - Check for crash/hang on peer
   - Check power/console

### Common Causes

| Cause | Indicators | Resolution |
|-------|------------|------------|
| Peer crashed | Console unresponsive | Reboot peer |
| Control link failure | See Control Link section | Fix link |
| Both links failed | No stats from peer | Check physical connectivity |
| Network issue (if using network for control) | Traceroute fails | Fix network path |

---

## Critical: Failover Detected

### Alert Details
- **DataPoint**: `TotalFailovers` delta > 0
- **Impact**: Primary/secondary roles swapped
- **Urgency**: 15 minutes - determine if expected

### Triage Steps

1. **Confirm failover occurred**:
   ```junos
   show chassis cluster status
   show log messages | match "failover|JSRPD"
   ```

2. **Identify cause**:
   ```junos
   show chassis cluster information detail
   show chassis cluster statistics
   ```

3. **Check traffic flow**:
   - Verify sessions are working
   - Check for any service impact

### Failover Cause Analysis

Look at `Monitor-failures` and logs:

| Cause | Log Message Pattern | Action |
|-------|---------------------|--------|
| Interface monitoring | `IF monitoring` | Check reth member links |
| IP monitoring | `IP probe failed` | Check monitored IP targets |
| Manual failover | `Manual switchover` | Verify if intentional |
| Priority change | `Priority changed` | Check priority config |
| Heartbeat lost | `Heartbeat lost` | Check control link |

### Post-Failover Checklist

- [ ] Verify sessions are flowing correctly
- [ ] Check for dropped sessions during failover
- [ ] Determine if failover was expected
- [ ] Investigate root cause if unexpected
- [ ] Consider fail-back if appropriate

---

## Warning: RG State Changed

### Alert Details
- **DataPoint**: `RGStatus` changed value
- **Impact**: Redundancy group ownership changed
- **Urgency**: 30 minutes

### RG State Values

| Value | State | Meaning |
|-------|-------|---------|
| 1 | Primary | This node owns the RG |
| 2 | Secondary | This node is standby |
| 3 | Disabled | RG is disabled |
| 0 | Unknown | Error state |

### Triage Steps

1. **Check RG status**:
   ```junos
   show chassis cluster status
   ```

2. **Check RG history**:
   ```junos
   show log messages | match "redundancy-group"
   ```

### Common Causes

- Manual failover (expected)
- Interface/IP monitoring triggered
- Priority/weight change
- Node reboot

---

## Warning: RG Weight Decreased

### Alert Details
- **DataPoint**: `RGWeight` decreased from previous value
- **Impact**: Node closer to losing primary role
- **Urgency**: 1 hour

### What is RG Weight?
- Priority minus interface penalties
- Lower weight = more likely to lose primary
- Weight decrease often precedes failover

### Triage Steps

1. **Check current weight**:
   ```junos
   show chassis cluster status
   ```

2. **Identify weight reduction cause**:
   ```junos
   show chassis cluster interfaces
   ```

3. **Check for interface issues**:
   ```junos
   show interfaces reth<x> extensive
   show interfaces <child-link> extensive
   ```

### Common Causes

| Cause | Resolution |
|-------|------------|
| Monitored interface down | Restore interface |
| IP monitor failed | Check monitored IP reachability |
| Child link failed | Fix/replace link |

---

## Manual Failover Procedures

### Planned Failover (Graceful)

```junos
# Fail RG1 from node0 to node1
request chassis cluster failover redundancy-group 1 node 1

# Verify
show chassis cluster status

# Fail back when ready
request chassis cluster failover reset redundancy-group 1
```

### Emergency Failover

```junos
# If node is unresponsive, from working node:
request chassis cluster failover redundancy-group 1 node <local-node-id>
```

### Disable Cluster (Emergency)

```junos
# On node to disable
request chassis cluster disable reboot
```

---

## Useful Commands Reference

### Status Commands
```junos
show chassis cluster status
show chassis cluster information
show chassis cluster interfaces
show chassis cluster statistics
```

### Troubleshooting Commands
```junos
show chassis cluster control-plane statistics
show chassis cluster data-plane statistics
show chassis cluster information detail
show log messages | match "cluster|JSRPD|failover"
```

### reth Interface Commands
```junos
show interfaces reth<x> extensive
show interfaces reth<x> | match "Physical|Logical"
show lacp interfaces
```

---

## Escalation Contacts

| Level | Contact | Response Time |
|-------|---------|---------------|
| L1 | NOC/Security NOC | Immediate |
| L2 | Firewall Team | 15 min |
| L3 | Security Architecture | 30 min |
| Vendor | JTAC | Per contract |

---

## Related Documentation

- [Juniper Chassis Cluster Admin Guide](https://www.juniper.net/documentation/en_US/junos/topics/concept/chassis-cluster-srx-understanding.html)
- [Chassis Cluster Troubleshooting](https://www.juniper.net/documentation/en_US/junos/topics/task/troubleshooting/chassis-cluster-srx.html)
- Internal: Firewall Change Management Procedures
