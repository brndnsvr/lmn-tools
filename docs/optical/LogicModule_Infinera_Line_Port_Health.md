# LogicModule: Infinera_Line_Port_Health

Monitors line port health metrics including optical power, status, and coherent DSP signal quality (OSNR, Q-Factor, BER) on Infinera Groove G30 optical transport systems.

---

## Basic Information (Info Tab)

| Field | Value |
|-------|-------|
| **Name** | `Infinera_Line_Port_Health` |
| **Resource Label** | `Line Port Health` |
| **Description** | Monitors line port health including optical power, status, and coherent DSP metrics (OSNR, Q-Factor, BER) |
| **Tags** | `optical,infinera,coherent,dsp` |
| **Group** | `Optical Transport` |
| **Collection Method** | `SCRIPT` |
| **Collection Schedule** | `2 minutes` |
| **Multi-Instance** | `Yes` |
| **Use Wildvalue as Unique Identifier** | `No` |
| **Enable Active Discovery** | `Yes` |
| **Technical Notes** | Line ports only (portType=2)<br>ochOs table for coherent DSP metrics<br>Post-FEC BER from PM table |

---

## AppliesTo

```
hasCategory("InfineraGroove")
```

---

## Active Discovery

| Field | Value |
|-------|-------|
| **Discovery Schedule** | `15 Minutes` |
| **Group Method** | `Manual` |
| **Disable Discovered Instances** | `No` |
| **Automatically Delete Instances** | `Yes` |
| **Delete Instance Data** | `Delete Immediately` |
| **Discovery Method** | `SCRIPT` |
| **Script Type** | `Embedded Groovy Script` |

### Active Discovery Script

```groovy
/*
 * Infinera Groove Line Port Health - Active Discovery Script
 *
 * Discovers LINE ports only (portType=2) for coherent DSP monitoring
 */

import com.santaba.agent.groovyapi.snmp.Snmp

def host = hostProps.get("system.hostname")

// Port table OIDs
def portNameOid = "1.3.6.1.4.1.42229.1.2.3.6.1.1.16"
def portTypeOid = "1.3.6.1.4.1.42229.1.2.3.6.1.1.17"
def portModeOid = "1.3.6.1.4.1.42229.1.2.3.6.1.1.18"
def portServiceLabelOid = "1.3.6.1.4.1.42229.1.2.3.6.1.1.23"

// Port mode to speed (bps) mapping
def portModeSpeedMap = [
    0: 0,
    5: 100000000000,   // qpsk100g
    6: 300000000000,   // 8qam300g
    7: 200000000000,   // 16qam200g
    10: 112000000000   // otu4
]

def portModeNameMap = [
    0: "N/A",
    5: "100G-QPSK",
    6: "300G-8QAM",
    7: "200G-16QAM",
    10: "OTU4"
]

def portNameData, portTypeData, portModeData, portServiceLabelData

try {
    portNameData = Snmp.walkAsMap(host, portNameOid, null)
    portTypeData = Snmp.walkAsMap(host, portTypeOid, null)
    portModeData = Snmp.walkAsMap(host, portModeOid, null)
    portServiceLabelData = Snmp.walkAsMap(host, portServiceLabelOid, null)
} catch (Exception e) {
    println "SNMP walk failed: ${e.message}"
    return 1
}

if (!portNameData || portNameData.isEmpty()) {
    return 0
}

portNameData.each { index, portName ->
    def parts = index.split("\\.")
    if (parts.size() < 4) return

    def shelf = parts[0]
    def slot = parts[1]
    def subslot = parts[2]
    def port = parts[3]

    // Skip management shelf/slot
    if (shelf == "99" || slot == "99") return

    // Only discover LINE ports (portType=2)
    def portTypeCode = portTypeData.get(index)?.toString() ?: ""
    try {
        if (portTypeCode.toInteger() != 2) return
    } catch (Exception e) {
        return
    }

    def portModeCode = portModeData.get(index)?.toString() ?: "0"
    def portModeInt = 0
    try {
        portModeInt = portModeCode.toInteger()
    } catch (Exception e) {}

    def speedBps = portModeSpeedMap.get(portModeInt) ?: 0
    def modeName = portModeNameMap.get(portModeInt) ?: "Unknown"

    def serviceLabel = portServiceLabelData.get(index)?.toString()?.trim() ?: ""

    def portPath
    if (subslot == "0") {
        portPath = "${shelf}/${slot}/${port}"
    } else {
        portPath = "${shelf}/${slot}.${subslot}/${port}"
    }

    def displayName = "${portPath} [line]"
    def description = portName?.toString()?.trim() ?: ""

    def props = "auto.port.speed=${speedBps}"
    props += "&auto.port.mode=${modeName}"
    props += "&auto.port.type=line"
    if (serviceLabel) {
        props += "&auto.service.label=${serviceLabel}"
    }

    println "${index}##${displayName}##${description}####${props}"
}

return 0
```

---

## Collection

| Field | Value |
|-------|-------|
| **Script Type** | `Embedded Groovy Script` |

### Collection Script

```groovy
/*
 * Infinera Groove Line Port Health - Collection Script
 *
 * Collects physical port metrics + coherent DSP metrics (OSNR, Q-Factor, BER)
 */

import com.santaba.agent.groovyapi.snmp.Snmp

def host = hostProps.get("system.hostname")
def wildvalue = instanceProps.get("wildvalue")

// Port table base OID
def portBase = "1.3.6.1.4.1.42229.1.2.3.6.1.1"

// ochOs table base OID (coherent DSP)
def ochOsBase = "1.3.6.1.4.1.42229.1.2.4.1.19.1.1"

// Post-FEC BER table base OID
def postFecBase = "1.3.6.1.4.1.42229.1.2.13.2.1.1"

// Physical port OIDs
def rxPowerOid = "${portBase}.4.${wildvalue}"
def txPowerOid = "${portBase}.5.${wildvalue}"
def adminStatusOid = "${portBase}.19.${wildvalue}"
def operStatusOid = "${portBase}.20.${wildvalue}"

// DSP metrics OIDs
def osnrOid = "${ochOsBase}.24.${wildvalue}"
def qFactorOid = "${ochOsBase}.25.${wildvalue}"
def preFecBerOid = "${ochOsBase}.26.${wildvalue}"
def postFecBerOid = "${postFecBase}.1.${wildvalue}.0"  // .0 for subportId (5-part index)

// Initialize all values
def rxPower = "NaN"
def txPower = "NaN"
def adminStatus = "NaN"
def operStatus = "NaN"
def osnr = "NaN"
def qFactor = "NaN"
def preFecBer = "NaN"
def postFecBer = "NaN"

// Collect physical port metrics
try {
    def rxResult = Snmp.get(host, rxPowerOid)
    if (rxResult != null && rxResult != "") {
        rxPower = rxResult.toString()
    }
} catch (Exception e) {}

try {
    def txResult = Snmp.get(host, txPowerOid)
    if (txResult != null && txResult != "") {
        txPower = txResult.toString()
    }
} catch (Exception e) {}

try {
    def adminResult = Snmp.get(host, adminStatusOid)
    if (adminResult != null && adminResult != "") {
        adminStatus = adminResult.toString()
    }
} catch (Exception e) {}

try {
    def operResult = Snmp.get(host, operStatusOid)
    if (operResult != null && operResult != "") {
        operStatus = operResult.toString()
    }
} catch (Exception e) {}

// Collect DSP metrics (may not exist for all ports)
try {
    def osnrResult = Snmp.get(host, osnrOid)
    if (osnrResult != null && osnrResult != "") {
        osnr = osnrResult.toString()
    }
} catch (Exception e) {}

try {
    def qResult = Snmp.get(host, qFactorOid)
    if (qResult != null && qResult != "") {
        qFactor = qResult.toString()
    }
} catch (Exception e) {}

try {
    def preFecResult = Snmp.get(host, preFecBerOid)
    if (preFecResult != null && preFecResult != "") {
        preFecBer = preFecResult.toString()
    }
} catch (Exception e) {}

try {
    def postFecResult = Snmp.get(host, postFecBerOid)
    if (postFecResult != null && postFecResult != "") {
        postFecBer = postFecResult.toString()
    }
} catch (Exception e) {}

// Output all metrics
println "RxOpticalPower=${rxPower}"
println "TxOpticalPower=${txPower}"
println "AdminStatus=${adminStatus}"
println "OperStatus=${operStatus}"
println "OSNR=${osnr}"
println "QFactor=${qFactor}"
println "PreFecBer=${preFecBer}"
println "PostFecBer=${postFecBer}"

return 0
```

---

## Datapoints

### Normal Datapoints (8)

| Name | Description | Metric Type | Raw Metric | Post Processor | Threshold |
|------|-------------|-------------|------------|----------------|-----------|
| **RxOpticalPower** | Received optical power (dBm) | Gauge | output | namevalue(RxOpticalPower) | - |
| **TxOpticalPower** | Transmitted optical power (dBm) | Gauge | output | namevalue(TxOpticalPower) | - |
| **AdminStatus** | Admin status: 1=up, 2=down | Gauge | output | namevalue(AdminStatus) | - |
| **OperStatus** | Oper status: 1=up, 2=down | Gauge | output | namevalue(OperStatus) | - |
| **OSNR** | Optical Signal-to-Noise Ratio (dB) | Gauge | output | namevalue(OSNR) | `< 21` (Warning) |
| **QFactor** | Q-Factor for signal quality | Gauge | output | namevalue(QFactor) | - |
| **PreFecBer** | Pre-FEC Bit Error Rate | Gauge | output | namevalue(PreFecBer) | `> 0.05` (Warning) |
| **PostFecBer** | Post-FEC Bit Error Rate | Gauge | output | namevalue(PostFecBer) | `> 0` (Warning) |

### Complex Datapoints (1)

| Name | Description | Expression | Threshold |
|------|-------------|------------|-----------|
| **QFactorAlert** | Q-Factor out of range alert | `QFactor,7,GE,QFactor,35,LE,AND,1,0,IF` | `< 1` (Warning) |

**Note:** QFactorAlert returns 1 when Q-Factor is in normal range (7-35), 0 when out of range.

### Datapoint Configuration Details

#### RxOpticalPower
```json
{
  "name": "RxOpticalPower",
  "description": "Received optical power in dBm",
  "type": "gauge",
  "dataType": 7,
  "useValue": "output",
  "interpretMethod": "namevalue",
  "interpretExpr": "RxOpticalPower",
  "noData": "Do not trigger an alert"
}
```

#### TxOpticalPower
```json
{
  "name": "TxOpticalPower",
  "description": "Transmitted optical power in dBm",
  "type": "gauge",
  "dataType": 7,
  "useValue": "output",
  "interpretMethod": "namevalue",
  "interpretExpr": "TxOpticalPower",
  "noData": "Do not trigger an alert"
}
```

#### AdminStatus
```json
{
  "name": "AdminStatus",
  "description": "Admin status: 1=up, 2=down, 3=upNoAlm",
  "type": "gauge",
  "dataType": 7,
  "useValue": "output",
  "interpretMethod": "namevalue",
  "interpretExpr": "AdminStatus",
  "noData": "Do not trigger an alert"
}
```

#### OperStatus
```json
{
  "name": "OperStatus",
  "description": "Operational status: 1=up, 2=down",
  "type": "gauge",
  "dataType": 7,
  "useValue": "output",
  "interpretMethod": "namevalue",
  "interpretExpr": "OperStatus",
  "noData": "Do not trigger an alert"
}
```

#### OSNR
```json
{
  "name": "OSNR",
  "description": "Optical Signal-to-Noise Ratio in dB. Values below 21 indicate degraded signal.",
  "type": "gauge",
  "dataType": 7,
  "useValue": "output",
  "interpretMethod": "namevalue",
  "interpretExpr": "OSNR",
  "threshold": "< 21",
  "noData": "Do not trigger an alert"
}
```

#### QFactor
```json
{
  "name": "QFactor",
  "description": "Q-Factor for signal quality. Normal range 7-35. Outside range indicates issues.",
  "type": "gauge",
  "dataType": 7,
  "useValue": "output",
  "interpretMethod": "namevalue",
  "interpretExpr": "QFactor",
  "noData": "Do not trigger an alert"
}
```

#### QFactorAlert (Complex)
```json
{
  "name": "QFactorAlert",
  "description": "Q-Factor out of range alert (warns when < 7 or > 35)",
  "type": "gauge",
  "dataType": 7,
  "interpretMethod": "expression",
  "interpretExpr": "QFactor,7,GE,QFactor,35,LE,AND,1,0,IF",
  "alertExpr": "< 1",
  "noData": "Do not trigger an alert"
}
```

**Note:** QFactorAlert handles the dual-threshold requirement for Q-Factor (< 7 OR > 35) using RPN logic.

#### PreFecBer
```json
{
  "name": "PreFecBer",
  "description": "Pre-FEC Bit Error Rate. Values above 0.05 indicate critical signal degradation.",
  "type": "gauge",
  "dataType": 7,
  "useValue": "output",
  "interpretMethod": "namevalue",
  "interpretExpr": "PreFecBer",
  "threshold": "> 0.05 0.05 0.05",
  "noData": "Do not trigger an alert"
}
```

#### PostFecBer
```json
{
  "name": "PostFecBer",
  "description": "Post-FEC Bit Error Rate. Any value above 0 indicates uncorrectable errors.",
  "type": "gauge",
  "dataType": 7,
  "useValue": "output",
  "interpretMethod": "namevalue",
  "interpretExpr": "PostFecBer",
  "threshold": "> 0 0 0",
  "noData": "Do not trigger an alert"
}
```

---

## Graphs

### Graph 1: Port Status

| Field | Value |
|-------|-------|
| **Displayed Title** | `Port Status` |
| **Graph Name** | `Port Status` |
| **Y-Axis Label** | `Status` |
| **Display Priority** | `0` |
| **Min Value** | `-9` |
| **Max Value** | `9` |
| **Time Range** | `Last 24 hours` |
| **Scale by units of 1024** | `No` |

#### Datapoints
| Datapoint | Name | Consolidation Function |
|-----------|------|------------------------|
| AdminStatus | AdminStatus | Average |
| OperStatus | OperStatus | Average |

#### Virtual Datapoints
| Name | Expression |
|------|------------|
| AdminStatusGraph | `AdminStatus,1,GT,-6,6,IF` |
| OperStatusGraph | `OperStatus,1,GT,-7,7,IF` |

#### Lines
| Datapoint | Type | Legend | Color | isVirtual |
|-----------|------|--------|-------|-----------|
| AdminStatusGraph | Line | Admin | Blue | Yes |
| OperStatusGraph | Line | Oper | Olive | Yes |

```json
{
  "title": "Port Status",
  "name": "Port Status",
  "verticalLabel": "Status",
  "displayPriority": 0,
  "min": -9,
  "max": 9,
  "timeScale": "1day",
  "scale1024": false,
  "datapoints": [
    {"datapointName": "AdminStatus", "consolidationFn": "average", "name": "AdminStatus"},
    {"datapointName": "OperStatus", "consolidationFn": "average", "name": "OperStatus"}
  ],
  "virtualDatapoints": [
    {"name": "AdminStatusGraph", "expr": "AdminStatus,1,GT,-6,6,IF"},
    {"name": "OperStatusGraph", "expr": "OperStatus,1,GT,-7,7,IF"}
  ],
  "lines": [
    {"datapointName": "AdminStatusGraph", "color": "blue", "legend": "Admin", "isVirtual": true, "type": "line"},
    {"datapointName": "OperStatusGraph", "color": "olive", "legend": "Oper", "isVirtual": true, "type": "line"}
  ]
}
```

### Graph 2: Optical Power

| Field | Value |
|-------|-------|
| **Displayed Title** | `Optical Power` |
| **Graph Name** | `Optical Power` |
| **Y-Axis Label** | `dBm` |
| **Display Priority** | `1` |
| **Time Range** | `Last 24 hours` |
| **Scale by units of 1024** | `No` |

#### Datapoints
| Datapoint | Name | Consolidation Function |
|-----------|------|------------------------|
| RxOpticalPower | RxOpticalPower | Average |
| TxOpticalPower | TxOpticalPower | Average |

#### Lines
| Datapoint | Type | Legend | Color | isVirtual |
|-----------|------|--------|-------|-----------|
| RxOpticalPower | Line | Rx Power | Blue 1 | No |
| TxOpticalPower | Line | Tx Power | Green 2 | No |

```json
{
  "title": "Optical Power",
  "name": "Optical Power",
  "verticalLabel": "dBm",
  "displayPriority": 1,
  "timeScale": "1day",
  "scale1024": false,
  "datapoints": [
    {"datapointName": "RxOpticalPower", "consolidationFn": "average", "name": "RxOpticalPower"},
    {"datapointName": "TxOpticalPower", "consolidationFn": "average", "name": "TxOpticalPower"}
  ],
  "lines": [
    {"datapointName": "RxOpticalPower", "color": "blue", "legend": "Rx Power", "isVirtual": false, "type": "line"},
    {"datapointName": "TxOpticalPower", "color": "olive", "legend": "Tx Power", "isVirtual": false, "type": "line"}
  ]
}
```

### Graph 3: OSNR

| Field | Value |
|-------|-------|
| **Displayed Title** | `OSNR` |
| **Graph Name** | `OSNR` |
| **Y-Axis Label** | `dB` |
| **Display Priority** | `2` |
| **Time Range** | `Last 24 hours` |
| **Scale by units of 1024** | `No` |

#### Datapoints
| Datapoint | Name | Consolidation Function |
|-----------|------|------------------------|
| OSNR | OSNR | Average |

#### Lines
| Datapoint | Type | Legend | Color | isVirtual |
|-----------|------|--------|-------|-----------|
| OSNR | Line | OSNR | Blue | No |

```json
{
  "title": "OSNR",
  "name": "OSNR",
  "verticalLabel": "dB",
  "displayPriority": 2,
  "timeScale": "1day",
  "scale1024": false,
  "datapoints": [
    {"datapointName": "OSNR", "consolidationFn": "average", "name": "OSNR"}
  ],
  "lines": [
    {"datapointName": "OSNR", "color": "blue", "legend": "OSNR", "isVirtual": false, "type": "line"}
  ]
}
```

### Graph 4: Q-Factor

| Field | Value |
|-------|-------|
| **Displayed Title** | `Q-Factor` |
| **Graph Name** | `Q-Factor` |
| **Y-Axis Label** | `Q` |
| **Display Priority** | `3` |
| **Time Range** | `Last 24 hours` |
| **Scale by units of 1024** | `No` |

#### Datapoints
| Datapoint | Name | Consolidation Function |
|-----------|------|------------------------|
| QFactor | QFactor | Average |

#### Lines
| Datapoint | Type | Legend | Color | isVirtual |
|-----------|------|--------|-------|-----------|
| QFactor | Line | Q-Factor | Orange | No |

```json
{
  "title": "Q-Factor",
  "name": "Q-Factor",
  "verticalLabel": "Q",
  "displayPriority": 3,
  "timeScale": "1day",
  "scale1024": false,
  "datapoints": [
    {"datapointName": "QFactor", "consolidationFn": "average", "name": "QFactor"}
  ],
  "lines": [
    {"datapointName": "QFactor", "color": "orange", "legend": "Q-Factor", "isVirtual": false, "type": "line"}
  ]
}
```

### Graph 5: Pre-FEC Bit Error Rate

| Field | Value |
|-------|-------|
| **Displayed Title** | `Pre-FEC Bit Error Rate` |
| **Graph Name** | `Pre-FEC Bit Error Rate` |
| **Y-Axis Label** | `BER` |
| **Display Priority** | `4` |
| **Time Range** | `Last 24 hours` |
| **Scale by units of 1024** | `No` |

#### Datapoints
| Datapoint | Name | Consolidation Function |
|-----------|------|------------------------|
| PreFecBer | PreFecBer | Average |

#### Lines
| Datapoint | Type | Legend | Color | isVirtual |
|-----------|------|--------|-------|-----------|
| PreFecBer | Line | Pre-FEC BER | Red | No |

```json
{
  "title": "Pre-FEC Bit Error Rate",
  "name": "Pre-FEC Bit Error Rate",
  "verticalLabel": "BER",
  "displayPriority": 4,
  "timeScale": "1day",
  "scale1024": false,
  "datapoints": [
    {"datapointName": "PreFecBer", "consolidationFn": "average", "name": "PreFecBer"}
  ],
  "lines": [
    {"datapointName": "PreFecBer", "color": "red", "legend": "Pre-FEC BER", "isVirtual": false, "type": "line"}
  ]
}
```

### Graph 6: Post-FEC Bit Error Rate

| Field | Value |
|-------|-------|
| **Displayed Title** | `Post-FEC Bit Error Rate` |
| **Graph Name** | `Post-FEC Bit Error Rate` |
| **Y-Axis Label** | `BER` |
| **Display Priority** | `5` |
| **Min Value** | `-0.0001` |
| **Max Value** | `0.0001` |
| **Time Range** | `Last 24 hours` |
| **Scale by units of 1024** | `No` |

**Note:** Fixed Y-axis range centers 0 to highlight any deviations from the ideal value of 0.

#### Datapoints
| Datapoint | Name | Consolidation Function |
|-----------|------|------------------------|
| PostFecBer | PostFecBer | Average |

#### Lines
| Datapoint | Type | Legend | Color | isVirtual |
|-----------|------|--------|-------|-----------|
| PostFecBer | Line | Post-FEC BER | Purple | No |

```json
{
  "title": "Post-FEC Bit Error Rate",
  "name": "Post-FEC Bit Error Rate",
  "verticalLabel": "BER",
  "displayPriority": 5,
  "min": -0.0001,
  "max": 0.0001,
  "timeScale": "1day",
  "scale1024": false,
  "datapoints": [
    {"datapointName": "PostFecBer", "consolidationFn": "average", "name": "PostFecBer"}
  ],
  "lines": [
    {"datapointName": "PostFecBer", "color": "purple", "legend": "Post-FEC BER", "isVirtual": false, "type": "line"}
  ]
}
```

---

## Alert Thresholds

| Datapoint | Warning | Error | Critical | Notes |
|-----------|---------|-------|----------|-------|
| OSNR | < 21 | - | - | Signal degradation |
| QFactorAlert | < 1 | - | - | Triggers when Q-Factor < 7 or > 35 (uses RPN logic) |
| PreFecBer | > 0.05 | > 0.05 | > 0.05 | Severe signal degradation |
| PostFecBer | > 0 | > 0 | > 0 | Any uncorrectable errors |

**Note:** Q-Factor alerting uses the QFactorAlert complex datapoint because LogicMonitor doesn't support OR conditions in standard thresholds. The RPN expression `QFactor,7,GE,QFactor,35,LE,AND,1,0,IF` returns 1 when in range (7-35) and 0 when out of range.

---

## Instance Properties

Set during Active Discovery for each line port:

| Property | Description | Example |
|----------|-------------|---------|
| `auto.port.speed` | Speed in bps | `100000000000` |
| `auto.port.mode` | Human-readable mode | `100G-QPSK` |
| `auto.port.type` | Always "line" | `line` |
| `auto.service.label` | Circuit description | `NYC-LAX-01` |

---

## OID Reference

### Physical Port Metrics
**Base OID:** `1.3.6.1.4.1.42229.1.2.3.6.1.1`

| Column | OID | Field | Description |
|--------|-----|-------|-------------|
| 4 | .4 | portRxOpticalPower | Rx power (dBm) |
| 5 | .5 | portTxOpticalPower | Tx power (dBm) |
| 19 | .19 | portAdminStatus | 1=up, 2=down, 3=upNoAlm |
| 20 | .20 | portOperStatus | 1=up, 2=down |

### Coherent DSP Metrics (ochOs Table)
**Base OID:** `1.3.6.1.4.1.42229.1.2.4.1.19.1.1`

| Column | OID | Field | Description |
|--------|-----|-------|-------------|
| 24 | .24 | ochOsOSNR | Optical SNR (dB) |
| 25 | .25 | ochOsQFactor | Q-Factor |
| 26 | .26 | ochOsPreFecBer | Pre-FEC BER |

### Post-FEC BER
**Base OID:** `1.3.6.1.4.1.42229.1.2.13.2.1.1`

| Column | OID | Field | Description |
|--------|-----|-------|-------------|
| 1 | .1 | bitErrorRatePostFecInstant | Current Post-FEC BER |

---

## Notes

- **Line Ports Only:** This DataSource only discovers ports with portType=2 (line ports)
- **Coherent DSP:** OSNR, Q-Factor, and Pre-FEC BER come from the ochOs table which is populated for coherent optics
- **Post-FEC BER Index:** The Post-FEC BER table uses a 5-part index (shelf.slot.subslot.port.subport). The script appends `.0` as subportId since line ports have no subports.
- **Separate BER Graphs:** Pre-FEC and Post-FEC BER are displayed on separate graphs to allow independent Y-axis scaling (Post-FEC values are typically orders of magnitude smaller)
- **-99.0 Value:** For optical power, -99.0 indicates no signal / laser off
- **NaN Values:** DSP metrics return NaN if the ochOs table entry doesn't exist for a port
