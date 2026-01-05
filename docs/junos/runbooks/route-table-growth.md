# Routing Table Growth Alert Response Runbook

Procedures for responding to alerts from the `Juniper_RoutingTable` custom datasource.

---

## Alert Summary

| Alert | Severity | Response Time | Escalation |
|-------|----------|---------------|------------|
| FIB Utilization > 90% | Critical | 15 min | Immediate |
| Massive BGP Route Change | Critical | 15 min | Immediate |
| FIB Utilization > 80% | Warning | 4 hours | Business hours |
| Route Count Deviation | Warning | 24 hours | Review weekly |
| Static Route Change | Warning | 1 hour | Business hours |
| Hidden Routes High | Warning | 4 hours | Business hours |

---

## Critical: FIB Utilization > 90%

### Alert Details
- **DataPoint**: `FIBUtilization > 90`
- **Impact**: Risk of route drops, black-holing traffic
- **Urgency**: Immediate - potential outage imminent

### Understanding the Risk

When FIB is full:
- New routes cannot be installed
- Traffic to unknown destinations is dropped
- May cause routing instability

### Triage Steps

1. **Verify FIB utilization**:
   ```junos
   show route forwarding-table summary
   show pfe statistics traffic
   ```

2. **Identify route distribution**:
   ```junos
   show route summary
   show route summary table inet.0
   show route summary table inet6.0
   ```

3. **Check for sudden growth**:
   ```junos
   show route history
   show bgp summary
   ```

### Emergency Actions

#### Option 1: Filter routes (if BGP)
```junos
# Apply more restrictive BGP import policy
set policy-options policy-statement IMPORT-FILTER term REJECT then reject
set protocols bgp group <group> import IMPORT-FILTER
commit
```

#### Option 2: Reduce route table (if local routes)
```junos
# Identify unnecessary static routes
show route protocol static extensive

# Remove if safe
delete routing-options static route <prefix>
commit
```

#### Option 3: Emergency BGP session teardown
```junos
# LAST RESORT - tears down BGP session
set protocols bgp group <group> shutdown
commit

# Better: soft-clear to apply new filters
clear bgp neighbor <peer-ip> soft-in
```

### Root Cause Analysis

| Cause | Indicators | Resolution |
|-------|------------|------------|
| Internet full table growth | BGP routes > 900K | Filter routes or upgrade |
| Route leak | Sudden BGP increase | Apply filters, contact peer |
| Config error | Many hidden routes | Fix routing policy |
| Normal growth | Gradual increase | Capacity planning |

---

## Critical: Massive BGP Route Change

### Alert Details
- **DataPoint**: `BGPRoutes` increased > 50% in 5 minutes
- **Impact**: Possible route leak or security incident
- **Urgency**: Immediate investigation

### What is a Route Leak?

When BGP routes are:
- Advertised to wrong peers
- Accepted without proper filtering
- Propagating incorrect paths

### Triage Steps

1. **Identify the change**:
   ```junos
   show bgp summary
   show route protocol bgp | count
   show route receive-protocol bgp <peer-ip> | count
   ```

2. **Find source of new routes**:
   ```junos
   # For each peer, count received routes
   show route receive-protocol bgp <peer-1-ip> | count
   show route receive-protocol bgp <peer-2-ip> | count
   ```

3. **Check route characteristics**:
   ```junos
   # Sample new routes
   show route protocol bgp terse | head 50

   # Check AS path
   show route protocol bgp extensive | match "AS path"
   ```

### Containment Actions

1. **If peer is leaking**:
   ```junos
   # Apply prefix limit to protect FIB
   set protocols bgp group <group> neighbor <peer-ip> family inet unicast prefix-limit maximum <limit>
   set protocols bgp group <group> neighbor <peer-ip> family inet unicast prefix-limit teardown
   commit
   ```

2. **If downstream is affected**:
   ```junos
   # Apply strict outbound policy
   set protocols bgp group <downstream-group> export NO-EXPORT
   commit
   ```

3. **Contact offending peer/provider**

### Analysis Commands

```junos
# Compare routes before/after (if have baseline)
show route protocol bgp | match "10\." | count  # Private space check
show route protocol bgp | match "0\.0\.0\.0/0"  # Default route check

# Check for hijacked prefixes
show route <your-prefix> extensive
```

---

## Warning: FIB Utilization > 80%

### Alert Details
- **DataPoint**: `FIBUtilization > 80`
- **Impact**: Capacity planning needed
- **Urgency**: 4 hours

### Actions

1. **Document current state**:
   ```junos
   show route summary | tee /var/tmp/route-summary-$(date +%Y%m%d).txt
   show route forwarding-table summary
   ```

2. **Analyze growth trend**:
   - Review LogicMonitor historical data
   - Calculate growth rate (routes per month)
   - Project when 90% will be reached

3. **Capacity planning options**:

| Option | Effort | Timeline |
|--------|--------|----------|
| Filter more routes | Low | Days |
| Summarize routes | Medium | Weeks |
| Upgrade line card | High | Months |
| Add routers | High | Months |

### Capacity Limits by Platform

| Platform | FIB IPv4 | FIB IPv6 | Notes |
|----------|----------|----------|-------|
| MX80 | 1M | 512K | Entry-level |
| MX104 | 1M | 512K | Entry-level |
| MX240 (Trio) | 2-4M | 1-2M | Per MPC type |
| MX480 (Trio) | 2-4M | 1-2M | Per MPC type |
| MX960 (Trio) | 2-4M | 1-2M | Per MPC type |
| SRX1500 | 1M | 512K | |
| SRX4600 | 2M | 1M | |

---

## Warning: Route Count Deviation

### Alert Details
- **DataPoint**: Route count deviated > 20% from baseline
- **Impact**: Network change detected
- **Urgency**: 24 hours

### Triage Steps

1. **Identify what changed**:
   ```junos
   show route summary
   ```

2. **Check per-protocol**:
   ```junos
   show route summary | match "BGP|OSPF|ISIS|Static"
   ```

3. **Correlate with events**:
   - Check change tickets
   - Review maintenance calendar
   - Check peer notifications

### Common Causes

| Protocol | Increase Cause | Decrease Cause |
|----------|----------------|----------------|
| BGP | New peer, route leak | Peer down, filter applied |
| OSPF | New area, redistribution | Area withdrawn |
| Static | New static routes | Routes removed |
| Direct | New interfaces | Interfaces removed |

### Actions

- **If expected**: Update baseline property in LogicMonitor
- **If unexpected**: Investigate root cause

---

## Warning: Static Route Change

### Alert Details
- **DataPoint**: `StaticRoutes` changed by > 5
- **Impact**: Configuration change detected
- **Urgency**: 1 hour - verify authorized

### Triage Steps

1. **Check current static routes**:
   ```junos
   show route protocol static
   show configuration routing-options static
   ```

2. **Compare with backup**:
   ```junos
   show system rollback compare 0 1 | match static
   ```

3. **Verify change authorization**:
   - Check change ticket system
   - Contact recent config editors

### Actions

- **If authorized**: Document and close
- **If unauthorized**: Investigate, rollback if needed

---

## Warning: Hidden Routes High

### Alert Details
- **DataPoint**: `HiddenRoutes > 100`
- **Impact**: Routing policy issues
- **Urgency**: 4 hours

### What are Hidden Routes?

Routes that are:
- In RIB but not FIB
- Rejected by policy
- Have unreachable next-hop
- Lower preference than active route

### Triage Steps

1. **Find hidden routes**:
   ```junos
   show route hidden
   show route hidden extensive | head 100
   ```

2. **Identify reason**:
   ```junos
   show route <hidden-prefix> hidden detail
   ```

### Common Causes

| Reason | Resolution |
|--------|------------|
| Policy rejection | Review import policy |
| Unreachable next-hop | Fix next-hop resolution |
| Lower preference | Expected behavior |
| Martian/bogon | Expected filtering |

---

## Baseline Management

### Establishing Baselines

1. **Collect data for 2 weeks**
2. **Run baseline script**:
   ```bash
   python scripts/baseline-routes.py --device <hostname> --days 14
   ```

3. **Set device properties**:
   ```
   routing.baseline.ipv4 = 850000
   routing.baseline.bgp = 800000
   routing.baseline.ospf = 500
   routing.warn.deviation = 20
   ```

### Updating Baselines

Quarterly or after significant network changes:

1. Review current route counts
2. Compare to existing baseline
3. Update properties if legitimate change
4. Document reason for change

---

## Useful Commands Reference

### Route Summary Commands
```junos
show route summary
show route summary table inet.0
show route summary table inet6.0
show route forwarding-table summary
```

### Protocol-Specific Commands
```junos
# BGP
show bgp summary
show bgp neighbor extensive
show route protocol bgp | count

# OSPF
show ospf overview
show ospf route
show route protocol ospf | count

# Static
show route protocol static
show configuration routing-options static
```

### Troubleshooting Commands
```junos
# Route details
show route <prefix> extensive
show route <prefix> hidden detail

# FIB details
show route forwarding-table destination <prefix>
show pfe statistics traffic

# History
show route history
show log messages | match "routing|bgp|ospf"
```

### Capacity Commands
```junos
# PFE utilization (MX)
show pfe statistics traffic

# Memory
show system memory
show task memory detail | match "Routing"
```

---

## Escalation Contacts

| Level | Contact | Response Time |
|-------|---------|---------------|
| L1 | NOC | Immediate |
| L2 | Network Engineering | 30 min |
| L3 | Routing SME | 1 hour |
| Vendor | JTAC | Per contract |

---

## Related Documentation

- [Juniper Routing Table MIB](https://www.juniper.net/documentation/en_US/junos/topics/reference/general/snmp-mib-routing.html)
- [MX Series FIB Scaling](https://www.juniper.net/documentation/en_US/junos/topics/concept/mx-series-forwarding-table-scaling.html)
- Internal: BGP Peering Policy
- Internal: Route Filtering Standards
