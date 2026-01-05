# Phased Rollout Plan

Safe deployment strategy for custom Juniper datasources to production LogicMonitor environment.

## Guiding Principles

1. **No impact to production monitoring during testing**
2. **POC environment first, then single site, then all sites**
3. **Each phase requires sign-off before proceeding**
4. **Rollback plan for each phase**
5. **Monitor collector health throughout**

## Environment Summary

| Component | Count | Details |
|-----------|-------|---------|
| Total Collectors | 45 | 10 data centers + POC |
| POC Collector | 1 | LOGICMON-POC (ID: 66) - 43 hosts |
| Juniper Devices | 60 | EX3400 switches |
| Sites | 10 | DAL1/2, LAX2, ATL1, WDC1, CHI1, PHX1, NYC3, SEA1, BOS1 |

## Timeline Overview

| Phase | Duration | Scope | Risk Level |
|-------|----------|-------|------------|
| Phase 1: POC | Week 1-2 | POC collector only | Minimal |
| Phase 2: Pilot | Week 3-4 | DAL1 site (4 devices) | Low |
| Phase 3: Rollout | Week 5-8 | All sites (one per day) | Medium |
| Phase 4: Hardening | Week 9-10 | Group migration, alerting | Low |

---

## Phase 1: POC Environment

**Duration**: Week 1-2
**Scope**: LOGICMON-POC collector only (ID: 66)
**Risk**: Minimal - isolated from production

### Prerequisites

- [ ] POC collector healthy and responsive
- [ ] At least 2 Juniper test devices available (or cloned)
- [ ] LogicMonitor API access for datasource creation
- [ ] SSH credentials configured for test devices

### Tasks

#### Day 1-2: Datasource Creation
1. Create `Juniper_EVPN_VXLAN` datasource (disabled)
2. Create `Juniper_SRX_ChassisCluster` datasource (disabled)
3. Create `Juniper_RoutingTable` datasource (disabled)
4. Create `Juniper_SRX_ClusterDetect` PropertySource (disabled)

#### Day 3-5: Test Device Setup
1. Clone 2-3 production Juniper devices to POC collector
   - OR use existing POC Juniper devices
2. Verify SNMP connectivity from POC collector
3. Verify SSH access from POC collector
4. Document test device IDs

#### Day 6-8: Enable and Validate
1. Enable PropertySource on test devices
2. Verify `auto.cluster_mode` and other properties set correctly
3. Enable datasources one at a time:
   - Start with `Juniper_RoutingTable` (simplest)
   - Then `Juniper_SRX_ChassisCluster` (if SRX available)
   - Then `Juniper_EVPN_VXLAN` (if QFX available)
4. Verify data collection in LogicMonitor UI
5. Check collector debug logs for errors

#### Day 9-10: Threshold Tuning
1. Review collected data for 48+ hours
2. Adjust alert thresholds based on observed values
3. Test alert triggering (temporarily lower threshold)
4. Document baseline values

### Success Criteria

- [ ] All applicable datasources collecting data
- [ ] No errors in collector logs (`/usr/local/logicmonitor/agent/logs/`)
- [ ] SNMP poll time < 30 seconds per device
- [ ] Device CPU impact < 5% during collection
- [ ] Alert thresholds tested and working

### Rollback Procedure

```
1. Disable all custom datasources
2. Delete cloned test devices (if created)
3. Document issues encountered
4. Return to development phase if needed
```

---

## Phase 2: Single Site Pilot

**Duration**: Week 3-4
**Scope**: DAL1 site - 4 Juniper devices
**Risk**: Low - limited scope, device-level enablement

### Prerequisites

- [ ] Phase 1 completed successfully
- [ ] Sign-off from Phase 1 review
- [ ] DAL1 collectors healthy (DAL1-MON1a/b, DAL1-MON2a/b)
- [ ] Change window approved (if required)

### Tasks

#### Week 3, Day 1-2: Device Selection
1. Identify 4 Juniper devices at DAL1:
   - 2 EX switches (DAL1-IS1, DAL1-IS2)
   - 2 additional devices if available
2. Verify device connectivity from DAL1 collectors
3. Document device IDs and current monitoring status

#### Week 3, Day 3-5: Enable Datasources
1. Apply custom datasources via **device-level override** (not group)
   - This prevents automatic application to other devices
2. Enable datasources with **alerting disabled**
3. Monitor for 72 hours

#### Week 3, Day 6-7: Validation
1. Compare collected data with manual CLI output
2. Verify no gaps in existing monitoring
3. Check collector CPU/memory:
   ```bash
   # On collector
   top -b -n 1 | grep sbproxy
   df -h /usr/local/logicmonitor
   ```
4. Check device CPU impact:
   ```junos
   show system processes extensive | match snmpd
   ```

#### Week 4, Day 1-3: Alert Testing
1. Enable alerting in **warning-only mode**
2. Route test alerts to non-production escalation chain
3. Verify alert formatting and content
4. Test acknowledgment workflow

#### Week 4, Day 4-5: Documentation
1. Document baseline values for each device
2. Update threshold recommendations if needed
3. Create site-specific notes

### Success Criteria

- [ ] 1 week of stable data collection
- [ ] Collector CPU increase < 10%
- [ ] Collector memory increase < 500MB
- [ ] SNMP poll times < 30 seconds
- [ ] No device CPU impact (snmpd < 5%)
- [ ] Warning alerts triggering correctly
- [ ] No false positives observed

### Rollback Procedure

```
1. Remove device-level datasource assignments:
   - LogicMonitor UI > Device > Datasources > [datasource] > Remove
2. Verify devices return to normal monitoring
3. Document issues
4. Return to Phase 1 if needed
```

---

## Phase 3: Site-by-Site Rollout

**Duration**: Week 5-8
**Scope**: All remaining 9 sites, one per day
**Risk**: Medium - production impact possible

### Prerequisites

- [ ] Phase 2 completed successfully
- [ ] Sign-off from Phase 2 review
- [ ] Monitoring dashboard for collector health
- [ ] On-call team notified of rollout schedule

### Rollout Order

| Day | Site | Collector IDs | Rationale |
|-----|------|---------------|-----------|
| 1 | DAL2 | 10-13 | Similar to DAL1, validates consistency |
| 2 | PHX1 | 22-25 | Different region, tests latency |
| 3 | LAX2 | 14-17 | West coast validation |
| 4 | CHI1 | 30-33 | Midwest region |
| 5 | (buffer) | - | Catch-up / issue resolution |
| 6 | ATL1 | 18-21 | Southeast region |
| 7 | WDC1 | 26-29 | East coast |
| 8 | NYC3 | 34-37 | Major metro |
| 9 | (buffer) | - | Catch-up / issue resolution |
| 10 | SEA1 | 38-41 | Pacific Northwest |
| 11 | BOS1 | 42-45 | Northeast |

### Daily Procedure

**Morning (before 10am local time):**

1. Pre-flight checks:
   ```
   - Verify target site collectors healthy
   - Check for existing critical alerts at site
   - Confirm no scheduled maintenance
   ```

2. Apply datasources:
   ```
   - Apply to all Juniper devices at site via device-level override
   - Enable with alerting enabled (production mode)
   ```

3. Verify collection started:
   ```
   - Check LogicMonitor UI for data flow
   - Verify instance discovery completed
   ```

**Afternoon (after 2pm local time):**

4. Validation:
   ```
   - Confirm data collection stable
   - Check collector health metrics
   - Review any alerts generated
   ```

**Next morning:**

5. Sign-off:
   ```
   - Review 24-hour data
   - Confirm no issues
   - Document any site-specific findings
   - Proceed to next site
   ```

### Monitoring During Rollout

**Collector Health Dashboard:**
- CPU utilization per collector
- Memory usage per collector
- SNMP poll queue depth
- Failed collection attempts

**Alert Monitoring:**
- New alerts from custom datasources
- Alert volume comparison (before/after)
- False positive tracking

### Success Criteria

- [ ] All 60 Juniper devices monitored by custom datasources
- [ ] No collector CPU > 80% sustained
- [ ] No collector memory > 90%
- [ ] Alert rules routing correctly
- [ ] No more than 5% false positive rate

### Rollback Procedure (Per Site)

```
1. Identify affected site
2. Disable datasources on all devices at that site:
   - Use bulk operation or script
3. Verify devices return to normal
4. Investigate root cause
5. Resume rollout when resolved
```

### Bulk Disable Script (Emergency)

```python
# disable_datasources_by_site.py
import requests

SITE = "DAL2"  # Site prefix to disable
DATASOURCES = [
    "Juniper_EVPN_VXLAN",
    "Juniper_SRX_ChassisCluster",
    "Juniper_RoutingTable"
]

# Get devices at site
devices = lm_api.get_devices(filter=f"displayName~{SITE}*")

for device in devices:
    for ds_name in DATASOURCES:
        # Find device datasource
        ds = lm_api.get_device_datasource(device.id, ds_name)
        if ds:
            # Disable alerting
            lm_api.update_device_datasource(device.id, ds.id, {"disableAlerting": True})
            # Stop monitoring
            lm_api.update_device_datasource(device.id, ds.id, {"stopMonitoring": True})

print(f"Disabled datasources for {len(devices)} devices at {SITE}")
```

---

## Phase 4: Production Hardening

**Duration**: Week 9-10
**Scope**: Finalization and group-level management
**Risk**: Low

### Tasks

#### Week 9: Group Migration

1. **Create device group structure** (if not exists):
   ```
   /Network Infrastructure/Juniper/
   ```

2. **Move datasource assignment to group level**:
   - Remove device-level overrides
   - Enable datasources on Juniper device group
   - Verify inheritance working correctly

3. **Set group properties**:
   - Baseline values
   - Alert thresholds
   - Contact information

#### Week 10: Operational Readiness

1. **Finalize alert thresholds**:
   - Review 6+ weeks of data
   - Adjust thresholds based on observed patterns
   - Remove any temporary test configurations

2. **Create dashboards**:
   - Juniper overview dashboard
   - Per-site drill-down views
   - Capacity planning widgets

3. **Update documentation**:
   - Runbook procedures
   - Escalation paths
   - Known issues

4. **Train operations team**:
   - Alert response procedures
   - Dashboard usage
   - Troubleshooting guides

### Success Criteria

- [ ] Datasources managed at group level
- [ ] Device-level overrides removed
- [ ] Alert thresholds finalized
- [ ] Dashboards deployed
- [ ] Runbooks updated
- [ ] Team trained

---

## Post-Rollout

### Ongoing Maintenance

- **Monthly**: Review alert volume and false positive rate
- **Quarterly**: Review threshold appropriateness
- **As needed**: Update datasources for new Junos versions

### Future Enhancements

1. Add Mist integration when adopted
2. Extend to additional device types (QFX spine/leaf)
3. Build custom dashboards per team/site
4. Integrate with ticketing system

---

## Appendix: Contact Information

| Role | Contact | Escalation |
|------|---------|------------|
| Project Lead | TBD | Primary |
| LogicMonitor Admin | TBD | Technical |
| Network Operations | TBD | Alert response |
| On-call | TBD | After hours |
