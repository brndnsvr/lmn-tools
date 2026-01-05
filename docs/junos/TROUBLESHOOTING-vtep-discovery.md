# VTEP Discovery Troubleshooting Log

## Device Under Test
- **Name:** DL2632678LEF001
- **IP:** 10.32.4.71
- **LM Device ID:** 217
- **Model:** qfx5110-48s-4c
- **Junos:** 23.2R1-S2.5

## Issue Summary
VTEP discovery script was returning "JSchException: connection is closed by foreign host" instead of discovering VTEPs.

## Root Cause Analysis

### Initial Theories (Ruled Out)
1. **User permissions** - Initially thought `lm-poller` lacked permissions
   - Changed to `svc.bss` (full admin) - same error
   - **Ruled out**: Not a permission issue

2. **Wrong command syntax** - `show vxlan remote-vtep` doesn't exist on QFX5110
   - **Confirmed**: Command hierarchy differs by platform

### Actual Root Cause
The error was intermittent and related to:
1. **Script complexity** - Complex scripts with multiple features sometimes failed to compile/run
2. **Paging** - Large output (1100+ lines) from full VTEP command
3. **JSch exec channel behavior** - Different from interactive SSH

## Working Configuration

### Commands That Work via JSch
| Command | Result |
|---------|--------|
| `show version \| match Model \| no-more` | ✅ Works |
| `show evpn instance \| no-more` | ✅ Works (4 lines) |
| `show ethernet-switching vxlan-tunnel-end-point remote summary \| no-more` | ✅ Works (23 lines, 20 VTEPs) |

### Commands That Don't Work
| Command | Result |
|---------|--------|
| `show vxlan` | ❌ Syntax error - doesn't exist on QFX5110 |
| `show vxlan remote-vtep` | ❌ Syntax error |

### Key Findings
1. Use `summary` version of VTEP command - 23 lines vs 1100+ lines
2. Always append `| no-more` to disable paging
3. Keep Groovy scripts simple - complex scripts fail silently
4. Sequential commands work; avoid complex data structures in runCommand return

## VTEP Output Format (QFX5110, Junos 23.2)

```
Logical System Name       Id  SVTEP-IP         IFL   L3-Idx    SVTEP-Mode    ELP-SVTEP-IP
<default>                 0   10.32.2.71       lo0.0    0
 RVTEP-IP         L2-RTT                   IFL-Idx   Interface    NH-Id   RVTEP-Mode  ELP-IP        Flags
 131.226.192.1    default-switch           955       vtep.32780   2082    RNVE
 131.226.192.2    default-switch           893       vtep.32779   2004    RNVE
 10.32.2.72       default-switch           925       vtep.32774   2006    RNVE
 ...
```

### Parsing Logic
- Lines with RVTEP-IP start with whitespace followed by IP
- Regex: `/^\s+(\d+\.\d+\.\d+\.\d+)\s+/`
- SVTEP-IP (local) is in the header section, not in data lines

## Script Version History

| Version | Changes | Result |
|---------|---------|--------|
| v1.0-v1.6 | Various parsing attempts | Failed - wrong command or parsing |
| v1.7 | Static test | ✅ Proved discovery pipeline works |
| v1.8 | Minimal SSH test | ✅ Proved SSH works |
| v2.0-v2.5 | Various command tests | Failed - still connection errors |
| v3.0 | Summary command | Failed - script too complex |
| v3.1 | cli -c wrapper | Partial - SSH test worked |
| v3.2 | Multiple tests with stderr | Failed - script syntax issue |
| v3.3 | Simplified sequential | ✅ Version + EVPN work |
| v3.4 | Add VTEP summary test | ✅ All 3 commands work |
| v3.5 | Full parsing | Failed - back to connection error |
| v3.6 | Keep v3.4 structure, add parsing | Failed - exception in parsing |
| v3.7 | Step-by-step debug | ✅ Showed SSH connects, fails after |
| v3.8 | Mirror BGP script exactly | ✅ 20 VTEPs discovered! |
| v3.9 | Test with show version | ✅ Confirmed script runs |
| v4.0 | Production release | ✅ Working |

## SSH Credentials
Changed from `lm-poller` to `svc.bss` during troubleshooting.
Both users have same effective permissions for these show commands.

## Resolution (2026-01-03)

### Final Working Configuration
- **Version**: v4.0.0
- **Command**: `show ethernet-switching vxlan-tunnel-end-point remote summary | no-more`
- **VTEPs Discovered**: 20 remote VTEPs
- **SSH User**: svc.bss (admin account)

### Key Fixes
1. **Script structure** - Copy exact pattern from working BGP EVPN script
2. **Use summary command** - 23 lines vs 1100+ lines (avoids timeout/paging issues)
3. **Timeout** - 30 seconds (matching BGP script)
4. **Regex pattern** - `/^\s+(\d+\.\d+\.\d+\.\d+)\s+/` to match RVTEP-IP lines

### Discovered VTEPs
```
10.32.2.72, 10.32.2.73, 10.32.2.74, 10.32.2.75, 10.32.2.76,
10.32.2.77, 10.32.2.78, 10.32.2.79, 10.32.2.80, 10.32.2.81,
10.32.2.82, 10.32.2.84, 10.32.2.87, 10.32.2.88, 10.32.2.89,
10.32.2.90, 10.32.2.91, 10.32.2.99, 131.226.192.1, 131.226.192.2
```

## Next Steps
1. Monitor collection data (Status, VNICount, TunnelCount)
2. Verify alerts trigger correctly when VTEP goes down
3. Deploy to additional devices in DXDFW group
4. Revert SSH credentials back to lm-poller once allowed

---

# VTEP Collection Troubleshooting (2026-01-03 Continued)

## Issue Summary
After discovery was fixed (v4.0.0), collection started returning Status=0 for all VTEPs.
Later, after script updates, collection started returning "No Data" for all datapoints.

## Current State

| Component | Status | Notes |
|-----------|--------|-------|
| Discovery | ✅ Working | 20 VTEPs found on device 217 |
| Collection | ❌ Broken | Returns "No Data" for all values |
| SSH from collector | ✅ Working | Ping datasource collects, BGP/VNI run (return 0s) |

## Comparison with Working DataSources

| DataSource | Discovery | Collection Data | Notes |
|------------|-----------|-----------------|-------|
| Juniper_EVPN_VXLAN | ✅ 60 VNIs | Status=0.0, MACCount=0.0 | Script runs, SSH works |
| Juniper_EVPN_BGP | ✅ 2 peers | PeerState=0.0 | Script runs, SSH works |
| Juniper_EVPN_VTEPs | ✅ 20 VTEPs | "No Data" | Script NOT running |
| Ping | ✅ | 0.0, 1.0 values | Working |

## Collection Script Versions Tested

| Version | Changes | Result |
|---------|---------|--------|
| v2.0.0 (original) | Basic collection with Status/VNICount/TunnelCount | Initially returned Status=0 |
| v2.1.0 | Added LineCount/SSHOk debug datapoints | ❌ "No Data" - broke collection |
| v2.0.0 (reverted) | Removed debug datapoints | ❌ Still "No Data" |
| v4.1.1 | Version bump to force refresh | ⏳ Pending verification |

## Theories Investigated

### Theory 1: SSH Credentials Not Set
- **Status**: ❌ Ruled out
- **Evidence**: ssh.user=svc.bss, ssh.pass=set (8 chars), system.hostname=10.32.4.71
- All properties verified via API

### Theory 2: Instance wildValue Not Set
- **Status**: ❌ Ruled out
- **Evidence**: Instance "VTEP-10.32.2.76" has wildValue=10.32.2.76
- Verified via API for multiple instances

### Theory 3: Script Syntax Error
- **Status**: ❌ Ruled out
- **Evidence**: Script identical to working BGP script pattern
- Braces balanced, parentheses balanced, valid UTF-8
- 63 lines, 1871 chars

### Theory 4: Script Returns Before Output
- **Status**: Possible
- **Evidence**: Script has `return 1` on lines 14-16 if properties not set
- But properties ARE set, so these shouldn't trigger
- Discovery uses same properties and works

### Theory 5: Collector Cache/State Issue
- **Status**: ⏳ Under investigation
- **Evidence**:
  - Collection worked initially (Status=0 values seen)
  - After v2.1.0 update: "No Data"
  - After v2.0.0 revert: Still "No Data"
- May need collector restart or datasource delete/recreate

### Theory 6: Datapoint Definition Corrupted
- **Status**: ❌ Ruled out
- **Evidence**: Datapoints verified via API:
  - Status: postProcessorMethod=namevalue, postProcessorParam=Status
  - VNICount: postProcessorMethod=namevalue, postProcessorParam=VNICount
  - TunnelCount: postProcessorMethod=namevalue, postProcessorParam=TunnelCount

## Key Observations

1. **Discovery vs Collection paradox**: Both use same SSH pattern, same command,
   same device. Discovery works, collection doesn't.

2. **Other datasources work**: BGP and VNI collection scripts (same SSH pattern)
   DO output values (even if 0). Only VTEP returns "No Data".

3. **Timing**: Issue started after adding debug datapoints (v2.1.0), persisted
   after reverting. Suggests collector cached broken state.

4. **Alert behavior**: When collection worked (Status=0), alerts fired.
   Now with "No Data", alert count is 0 (alertForNoData should trigger but doesn't).

---

# Resolution (2026-01-03)

## Root Cause: SSH Rate Limiting

### Investigation Results
Added debug datapoints to trace script execution:
- `ScriptStarted=1` - Script starts executing ✓
- `ChecksPassed=1` - All property checks pass ✓
- `SSHConnected=No Data` - SSH connection never completes
- `SSHFailed=1` - Exception caught in SSH block

### Key Finding
Out of 21 VTEP instances:
- **4 instances**: SSH connection succeeded
- **17 instances**: SSH connection failed

This pattern indicated **SSH rate limiting** on the Juniper device. The QFX has a limit
on concurrent SSH sessions. When collection runs for 21 instances simultaneously, most
connections are rejected.

### Why Discovery Worked
Discovery uses a single SSH connection to get all VTEP data at once.
Collection (per-instance script) was making 21 separate SSH connections.

## Solution: Batchscript Collection

Switched from `collectMethod: "script"` to `collectMethod: "batchscript"`.

### Script Collection (v4.x - broken)
```
script runs for VTEP-10.32.2.76 → SSH connection
script runs for VTEP-10.32.2.77 → SSH connection
script runs for VTEP-10.32.2.78 → SSH connection
... 21 total connections → rate limited
```

### Batchscript Collection (v5.0.0 - working)
```
script runs ONCE for all instances
  → single SSH connection
  → outputs: 10.32.2.76.Status=1, 10.32.2.77.Status=1, ...
```

### v5.0.0 Changes
1. `collectMethod: "batchscript"`
2. `collectorAttribute.name: "batchscript"`
3. Script outputs in format: `wildvalue.datapoint=value`
4. Datapoints use `##WILDVALUE##.Status` pattern
5. Single SSH connection serves all 20 VTEP instances

## Final Working Configuration

- **Discovery**: v5.0.0 - Single SSH connection, discovers VTEPs
- **Collection**: v5.0.0 - Batchscript, single SSH connection
- **Instances**: 20 VTEPs (all returning Status=1, TunnelCount=1)
- **SSH User**: svc.bss

## Lessons Learned

1. **SSH rate limiting is real** - Juniper devices limit concurrent sessions
2. **Use batchscript for multi-instance collection** - One connection vs N connections
3. **Debug datapoints are invaluable** - ScriptStarted/ChecksPassed/SSHFailed helped isolate the issue
4. **Discovery success ≠ Collection success** - Different execution patterns

## Files Modified
- `configs/logicmonitor/datasource-evpn-vteps.json` - v5.0.0
- `docs/TROUBLESHOOTING-vtep-discovery.md` - this file
