# EVPN Fabric Monitoring - Future Work

## Customer Path Mapping (Deferred)

### Goal
Create customer-specific dashboards showing full path through fabric:
Customer → VNIs → VTEPs → Physical Switches

### Prerequisites (In Progress)
- [x] Test device (217) fully monitored
- [ ] All QFX switches monitored with EVPN datasources
- [ ] MX route reflectors monitored
- [ ] SSH credentials on all devices
- [ ] Verified data collection across fabric

### Required Enhancements

#### 1. VNI-to-VTEP Correlation
- Extend VNI datasource to track which VTEPs carry each VNI
- Parse `show vlans <vlan> extensive` for VTEP peer list
- Add `auto.vtep.list` property to VNI instances

#### 2. Multi-Device Topology
- Correlate VTEP IPs to device hostnames
- Map spine/leaf relationships
- Identify route reflector paths
- Consider LLDP neighbor discovery

#### 3. Customer Dashboard
- Filter by `auto.customer.id` property
- Show all VNIs for customer across all devices
- Aggregate VTEP reachability status
- Alert on customer-affecting issues

### Data Already Available
| Property | Source | Example |
|----------|--------|---------|
| `auto.customer.id` | VNI instances | 630439 |
| `auto.vtep.ip` | VTEP instances | 10.32.2.72 |
| `auto.peer.ip` | BGP instances | 10.32.2.21 |
| `auto.vni.id` | VNI instances | 5655 |

### LogicMonitor Implementation Options

1. **Dynamic Groups** - Filter by customer ID property
2. **Service Insights** - Service-based monitoring views
3. **Topology Mapping** - Visual fabric representation
4. **External Integration** - NetBox/ServiceNow CMDB data

---

## Device Inventory (DXDFW)

| Type | Count | Status |
|------|-------|--------|
| QFX | 28 | Monitoring enabled |
| MX | 2 | Needs investigation |
| EX | 4 | No EVPN (standard monitoring) |
| SRX | 1 | Cluster monitoring |

---

## Completed Work

- [x] VNI Discovery (Juniper_EVPN_VXLAN v2.22.0)
- [x] BGP EVPN Peers (Juniper_EVPN_BGP v1.0.0)
- [x] VTEP Peers (Juniper_EVPN_VTEPs v5.0.0) - Fixed with batchscript collection
- [x] SSH credentials on test device (217)
- [x] Collection scripts verified - VTEP uses batchscript to avoid SSH rate limiting
- [x] Alerting configured
- [x] VTEP collection working (20 VTEPs, Status=1, TunnelCount=1)
