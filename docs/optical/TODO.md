# Project TODO

## Current Status
- Phase 3 complete
- Coriant scripts validated against real device (10.62.4.125)
- Ciena scripts implemented but not yet tested against real device

---

## Phase 4: Ciena Validation
- [ ] Obtain access to Ciena WaveServer lab device
- [ ] Test ciena_discover.py against real device
- [ ] Test ciena_collect.py against real device
- [ ] Test ciena_chassis_collect.py against real device
- [ ] Document any XPath adjustments needed
- [ ] Validate instance ID format works in LogicMonitor

## Phase 5: LogicMonitor Integration
- [ ] Install Python dependencies on test collector
- [ ] Import Coriant DataSource templates
- [ ] Upload Coriant scripts via LM WebUI
- [ ] Add test device with netconf.* properties
- [ ] Verify discovery finds instances
- [ ] Verify collection populates graphs
- [ ] Test alerting on oper_status and optical power

## Phase 6: Production Deployment
- [ ] Document collector dependency installation (Ansible playbook)
- [ ] Import all DataSource templates to production LM
- [ ] Set device properties for all 140 optical devices
- [ ] Configure alert thresholds based on operational norms
- [ ] Create dashboards for optical network overview

## Phase 7: Advanced Features (Future)
- [ ] Ciena lane-level metrics (per-lane optical power)
- [ ] Alarms as LogicMonitor EventSource
- [ ] Performance monitoring counters
- [ ] Additional vendors (if needed)

---

## Known Considerations
- Instance IDs contain forward slash (/) — test in LM, may need sanitization
- -99 dBm values indicate "no signal" — consider special alert handling
- Timestamp fields with 0000-01-01 are silently skipped (expected for unset values)

---

## Completed Phases

### Phase 1: Core Framework ✅
- [x] Project structure and packaging
- [x] NETCONF client with context manager
- [x] XML parser for metric extraction
- [x] LogicMonitor output formatters
- [x] Utility functions (sanitization, string maps)
- [x] YAML configuration structure
- [x] Basic unit tests

### Phase 2: Coriant Support ✅
- [x] Coriant interface configuration (OTS, OMS, OSC, GOPT)
- [x] Discovery script
- [x] Collection script
- [x] Chassis configuration and script
- [x] Fallback instance ID logic
- [x] Error message improvements
- [x] Test fixtures

### Phase 3: Ciena WaveServer ✅
- [x] Ciena interface configuration (PTPs, Ports)
- [x] Ciena chassis configuration
- [x] Discovery script
- [x] Collection script
- [x] Chassis collection script
- [x] Enhanced --debug output
- [x] LogicMonitor DataSource XML templates
- [x] Test fixtures

### Phase 3.5: Real Device Testing (Coriant) ✅
- [x] Test against real Coriant device (10.62.4.125)
- [x] Verify NETCONF connection
- [x] Validate discovery output format
- [x] Validate metric collection
- [x] Fix XPath namespace issues
- [x] Fix duplicate swload_active output
- [x] Fix null timestamp warnings

---

## How to Continue Development

### Adding a New Metric (Existing Vendor)

1. **Update YAML config** (`configs/{vendor}.yaml`)
   ```yaml
   metrics:
     - name: new_metric
       xpath: "path/to/element"
       help: "Description"
       string_map:  # Optional, for status values
         disabled: 0
         enabled: 1
   ```

2. **Update NETCONF filter** in same config file to request the element

3. **Add test fixture** if needed

4. **Update DataSource template** (`logicmonitor/*.xml`) to include new datapoint

### Adding a New Vendor

1. **Create config file** (`configs/newvendor.yaml`)
2. **Create scripts** (`scripts/newvendor_*.py`)
3. **Add device type** to `NetconfClient.DEVICE_TYPES`
4. **Create test fixtures** and tests
5. **Create LogicMonitor templates** (`logicmonitor/NewVendor_*.xml`)
