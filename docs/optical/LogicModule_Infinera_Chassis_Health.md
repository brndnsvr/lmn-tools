# LogicModule: Infinera_Chassis_Health

Monitors chassis-level health metrics including CPU utilization, memory usage, temperature, and fan speed on Infinera Groove G30 optical transport systems.

---

## Basic Information (Info Tab)

| Field | Value |
|-------|-------|
| **DataSource ID** | `21328173` |
| **Name** | `Infinera_Chassis_Health` |
| **Resource Label** | `Chassis Health` |
| **Description** | Monitors CPU, memory, temperature, and fan metrics on Infinera Groove chassis |
| **Tags** | `optical,infinera,chassis` |
| **Group** | `Optical Transport` |
| **Collection Method** | `SCRIPT` |
| **Collection Schedule** | `2 minutes` |
| **Multi-Instance** | `No` |

---

## AppliesTo

```
hasCategory("InfineraGroove")
```

---

## Collection

| Field | Value |
|-------|-------|
| **Script Type** | `Embedded Groovy Script` |

### Collection Script

```groovy
/*
 * Infinera Groove Chassis Health - Collection Script
 * OIDs verified via SNMP walk
 */

import com.santaba.agent.groovyapi.snmp.Snmp

def host = hostProps.get("system.hostname")

// CORRECTED OIDs based on walk output
// Walk base + relative = full OID

// CPU utilization - walk base
def cpuUtilBase = "1.3.6.1.4.1.42229.1.2.3.35.1.1"

// Shelf table base: 1.3.6.1.4.1.42229.1.2.3.1 + relative
// 1.1.3.1 => inlet temp, 1.1.4.1 => outlet temp
def inletTempOid = "1.3.6.1.4.1.42229.1.2.3.1.1.1.3.1"
def outletTempOid = "1.3.6.1.4.1.42229.1.2.3.1.1.1.4.1"

// Memory table base: 1.3.6.1.4.1.42229.1.2.3.37 + relative
// 1.1.1.1.99 => avail, 1.1.2.1.99 => util
def memAvailOid = "1.3.6.1.4.1.42229.1.2.3.37.1.1.1.1.99"
def memUtilOid = "1.3.6.1.4.1.42229.1.2.3.37.1.1.2.1.99"

// Card table base: 1.3.6.1.4.1.42229.1.2.3.3 + relative
// 1.1.7.1.6 => fan speed slot 6
def fanSpeedOid = "1.3.6.1.4.1.42229.1.2.3.3.1.1.7.1.6"

// Initialize
def cpuUtil = "NaN"
def memAvail = "NaN"
def memUtil = "NaN"
def inletTemp = "NaN"
def outletTemp = "NaN"
def fanSpeed = "NaN"

// CPU - walk and get first
try {
    def cpuData = Snmp.walkAsMap(host, cpuUtilBase, null)
    if (cpuData && !cpuData.isEmpty()) {
        cpuUtil = cpuData.values().first().toString()
    }
} catch (Exception e) {}

// Direct GET for other metrics
try {
    def result = Snmp.get(host, inletTempOid)
    if (result != null && result != "") inletTemp = result.toString()
} catch (Exception e) {}

try {
    def result = Snmp.get(host, outletTempOid)
    if (result != null && result != "") outletTemp = result.toString()
} catch (Exception e) {}

try {
    def result = Snmp.get(host, memAvailOid)
    if (result != null && result != "") memAvail = result.toString()
} catch (Exception e) {}

try {
    def result = Snmp.get(host, memUtilOid)
    if (result != null && result != "") memUtil = result.toString()
} catch (Exception e) {}

try {
    def result = Snmp.get(host, fanSpeedOid)
    if (result != null && result != "") fanSpeed = result.toString()
} catch (Exception e) {}

println "CpuUtilization=${cpuUtil}"
println "MemoryAvailable=${memAvail}"
println "MemoryUtilized=${memUtil}"
println "InletTemperature=${inletTemp}"
println "OutletTemperature=${outletTemp}"
println "FanSpeed=${fanSpeed}"

return 0
```

---

## Datapoints

### Normal Datapoints (6)

| Name | Description | Metric Type | Post Processor | Threshold |
|------|-------------|-------------|----------------|-----------|
| **CpuUtilization** | Total CPU utilization percentage | Gauge | namevalue(CpuUtilization) | `> 70` (Warn), `> 85` (Crit) |
| **MemoryAvailable** | Total available memory in bytes | Gauge | namevalue(MemoryAvailable) | - |
| **MemoryUtilized** | Memory currently in use in bytes | Gauge | namevalue(MemoryUtilized) | - |
| **InletTemperature** | Shelf inlet temperature in Celsius | Gauge | namevalue(InletTemperature) | `> 23` (Warn), `> 27` (Crit) |
| **OutletTemperature** | Shelf outlet temperature in Celsius | Gauge | namevalue(OutletTemperature) | `> 35` (Warn), `> 44` (Crit) |
| **FanSpeed** | Fan speed as percentage of maximum | Gauge | namevalue(FanSpeed) | `> 80` (Warn), `> 95` (Crit) |

### Complex Datapoints (1)

| Name | Description | Expression | Threshold |
|------|-------------|------------|-----------|
| **MemoryPercent** | Memory utilization as percentage | `MemoryUtilized / MemoryAvailable * 100` | `> 75` (Warn), `> 90` (Crit) |

---

## Graphs

**Note:** This is a single-instance DataSource, so graphs are instance graphs (not overview graphs).

### Graph 1: CPU Utilization

| Field | Value |
|-------|-------|
| **Displayed Title** | `CPU Utilization` |
| **Y-Axis Label** | `Percent` |
| **Display Priority** | `1` |
| **Min Value** | `0` |
| **Max Value** | `100` |

#### Lines
| Datapoint | Legend | Color |
|-----------|--------|-------|
| CpuUtilization | CPU % | Blue |

### Graph 2: Memory Utilization

| Field | Value |
|-------|-------|
| **Displayed Title** | `Memory Utilization` |
| **Y-Axis Label** | `Percent` |
| **Display Priority** | `2` |
| **Min Value** | `0` |
| **Max Value** | `100` |

#### Lines
| Datapoint | Legend | Color |
|-----------|--------|-------|
| MemoryPercent | Memory % | Orange |

### Graph 3: Temperature

| Field | Value |
|-------|-------|
| **Displayed Title** | `Temperature` |
| **Y-Axis Label** | `Celsius` |
| **Display Priority** | `3` |

#### Lines
| Datapoint | Legend | Color |
|-----------|--------|-------|
| InletTemperature | Inlet | Blue |
| OutletTemperature | Outlet | Red |

**Note:** Inlet temperature represents ambient/room temperature entering the chassis. Outlet temperature represents heated exhaust air. The difference indicates heat generated by the equipment.

### Graph 4: Fan Speed

| Field | Value |
|-------|-------|
| **Displayed Title** | `Fan Speed` |
| **Y-Axis Label** | `Percent` |
| **Display Priority** | `4` |
| **Min Value** | `0` |
| **Max Value** | `100` |

#### Lines
| Datapoint | Legend | Color |
|-----------|--------|-------|
| FanSpeed | Fan % | Green |

---

## Alert Thresholds

| Datapoint | Warning | Error | Critical | Notes |
|-----------|---------|-------|----------|-------|
| CpuUtilization | > 70% | > 70% | > 85% | High CPU load |
| MemoryPercent | > 75% | > 75% | > 90% | Memory exhaustion |
| InletTemperature | > 23°C | > 23°C | > 27°C | Ambient too warm |
| OutletTemperature | > 35°C | > 35°C | > 44°C | Equipment overheating |
| FanSpeed | > 80% | > 80% | > 95% | Fans working hard (possible cooling issue) |

---

## OID Reference

### CPU State Table
**Base OID:** `1.3.6.1.4.1.42229.1.2.3.35`
**Index:** `shelf.slot` (virtual slot 99 for management)

| Column | OID | Field | Description |
|--------|-----|-------|-------------|
| 1 | .1.1 | cpuStateCpuTotalUtilization | Total CPU % |

### Memory State Table
**Base OID:** `1.3.6.1.4.1.42229.1.2.3.37`
**Index:** `shelf.slot` (virtual slot 99)

| Column | OID | Field | Description |
|--------|-----|-------|-------------|
| 1 | .1.1 | memoryStateAvailable | Total memory (bytes) |
| 2 | .1.2 | memoryStateUtilized | Used memory (bytes) |

### Shelf Table
**Base OID:** `1.3.6.1.4.1.42229.1.2.3.1`
**Index:** `shelf`

| Column | OID | Field | Description |
|--------|-----|-------|-------------|
| 3 | .1.1.3 | shelfInletTemperature | Inlet temp (°C) |
| 4 | .1.1.4 | shelfOutletTemperature | Outlet temp (°C) |

### Card Table (Fan Speed)
**Base OID:** `1.3.6.1.4.1.42229.1.2.3.3`
**Index:** `shelf.slot`

| Column | OID | Field | Description |
|--------|-----|-------|-------------|
| 7 | .1.1.7 | cardFanSpeedRate | Fan speed % (FAN cards only) |

---

## Notes

- **Single Instance:** This is a single-instance DataSource (no Active Discovery) as it monitors chassis-level metrics
- **Slot 99:** CPU and Memory metrics come from virtual slot 99, which represents the management plane
- **Fan Speed:** Collected from slot 6 which is the first fan card. Multiple fans exist (slots 6-10) but typically run at the same speed
- **Temperature Difference:** Normal inlet-outlet difference is 10-15°C. Larger differences may indicate airflow problems
- **Memory:** MemoryPercent is calculated as `(Utilized / Available) * 100`
