# LogicModule: Infinera_Port_Status (Client Port Health)

Monitors Infinera Groove **client** port optical power, status, and throughput for both physical ports and subports. Line ports are excluded and monitored by the `Infinera_Line_Port_Health` DataSource.

---

## Basic Information (Info Tab)

| Field | Value |
|-------|-------|
| **Name** | `Infinera_Port_Status` |
| **Resource Label** | `Client Port Health` |
| **Description** | Monitors Infinera Groove client port optical power, status, and throughput (excludes line ports) |
| **Tags** | `optical` |
| **Group** | `Optical Transport` |
| **Collection Method** | `SCRIPT` |
| **Collection Schedule** | `2 minutes` |
| **Multi-Instance** | `Yes` |
| **Use Wildvalue as Unique Identifier** | `No` |
| **Enable Active Discovery** | `Yes` |

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
import com.santaba.agent.groovyapi.snmp.Snmp

def host = hostProps.get("system.hostname")

// Port table OIDs
def portNameOid = "1.3.6.1.4.1.42229.1.2.3.6.1.1.16"
def portTypeOid = "1.3.6.1.4.1.42229.1.2.3.6.1.1.17"
def portModeOid = "1.3.6.1.4.1.42229.1.2.3.6.1.1.18"
def portServiceLabelOid = "1.3.6.1.4.1.42229.1.2.3.6.1.1.23"

// Subport table OIDs
def subportIdOid = "1.3.6.1.4.1.42229.1.2.3.7.1.1.1"
def subportNameOid = "1.3.6.1.4.1.42229.1.2.3.7.1.1.2"
def subportTypeOid = "1.3.6.1.4.1.42229.1.2.3.7.1.1.3"
def subportModeOid = "1.3.6.1.4.1.42229.1.2.3.7.1.1.4"
def subportServiceLabelOid = "1.3.6.1.4.1.42229.1.2.3.7.1.1.9"

// Port type mapping
def portTypeMap = [1:"client", 2:"line", 3:"client-subport", 4:"optical", 5:"otdr", 6:"optical-nomon", 7:"ocm", 8:"osc", 9:"mgmt-eth"]

// Port mode to speed (bps) mapping
def portModeSpeedMap = [
    0: 0,
    1: 10000000000,
    2: 40000000000,
    3: 100000000000,
    4: 40000000000,
    5: 100000000000,
    6: 300000000000,
    7: 200000000000,
    8: 16000000000,
    9: 8000000000,
    10: 112000000000,
    22: 400000000000,
    45: 1000000000
]

def portModeNameMap = [
    0: "N/A", 1: "10GbE", 2: "40GbE", 3: "100GbE", 4: "4x10G",
    5: "100G-QPSK", 6: "300G-8QAM", 7: "200G-16QAM", 8: "16G-FC",
    9: "8G-FC", 10: "OTU4", 22: "400GbE", 45: "1GbE"
]

def portNameData, portTypeData, portModeData, portServiceLabelData
def subportIdData, subportNameData, subportTypeData, subportModeData, subportServiceLabelData

try {
    portNameData = Snmp.walkAsMap(host, portNameOid, null)
    portTypeData = Snmp.walkAsMap(host, portTypeOid, null)
    portModeData = Snmp.walkAsMap(host, portModeOid, null)
    portServiceLabelData = Snmp.walkAsMap(host, portServiceLabelOid, null)

    subportIdData = Snmp.walkAsMap(host, subportIdOid, null)
    subportNameData = Snmp.walkAsMap(host, subportNameOid, null)
    subportTypeData = Snmp.walkAsMap(host, subportTypeOid, null)
    subportModeData = Snmp.walkAsMap(host, subportModeOid, null)
    subportServiceLabelData = Snmp.walkAsMap(host, subportServiceLabelOid, null)
} catch (Exception e) {
    println "SNMP walk failed: ${e.message}"
    return 1
}

if (portNameData && !portNameData.isEmpty()) {
    portNameData.each { index, portName ->
        def parts = index.split("\\.")
        if (parts.size() < 4) return

        def shelf = parts[0]
        def slot = parts[1]
        def subslot = parts[2]
        def port = parts[3]

        if (shelf == "99" || slot == "99") return

        def portTypeCode = portTypeData.get(index)?.toString() ?: ""
        def portType = ""
        try {
            portType = portTypeMap.get(portTypeCode.toInteger()) ?: ""
        } catch (Exception e) {}

        // Skip line ports - they're handled by Line Port Health DataSource
        if (portType == "line") return

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

        def displayName = portType ? "${portPath} [${portType}]" : portPath
        def description = portName?.toString()?.trim() ?: ""

        def props = "auto.port.speed=${speedBps}"
        props += "&auto.port.mode=${modeName}"
        props += "&auto.port.type=${portType}"
        if (serviceLabel) {
            props += "&auto.service.label=${serviceLabel}"
        }
        props += "&auto.instance.type=port"

        println "${index}##${displayName}##${description}####${props}"
    }
}

if (subportIdData && !subportIdData.isEmpty()) {
    subportIdData.each { index, subportId ->
        def parts = index.split("\\.")
        if (parts.size() < 5) return

        def shelf = parts[0]
        def slot = parts[1]
        def subslot = parts[2]
        def port = parts[3]
        def subport = parts[4]

        if (shelf == "99" || slot == "99") return

        def subportTypeCode = subportTypeData.get(index)?.toString() ?: ""
        def subportType = ""
        try {
            subportType = portTypeMap.get(subportTypeCode.toInteger()) ?: "client-subport"
        } catch (Exception e) {
            subportType = "client-subport"
        }

        def speedBps = 10000000000
        def modeName = "10GbE"

        def serviceLabel = subportServiceLabelData.get(index)?.toString()?.trim() ?: ""
        def subportName = subportNameData.get(index)?.toString()?.trim() ?: ""

        def portPath
        if (subslot == "0") {
            portPath = "${shelf}/${slot}/${port}/${subport}"
        } else {
            portPath = "${shelf}/${slot}.${subslot}/${port}/${subport}"
        }

        def displayName = "${portPath} [${subportType}]"
        def description = subportName ?: ""

        def props = "auto.port.speed=${speedBps}"
        props += "&auto.port.mode=${modeName}"
        props += "&auto.port.type=${subportType}"
        if (serviceLabel) {
            props += "&auto.service.label=${serviceLabel}"
        }
        props += "&auto.instance.type=subport"

        println "${index}##${displayName}##${description}####${props}"
    }
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
import com.santaba.agent.groovyapi.snmp.Snmp

def host = hostProps.get("system.hostname")
def wildvalue = instanceProps.get("wildvalue")
def instanceType = instanceProps.get("auto.instance.type") ?: "port"

def portBase = "1.3.6.1.4.1.42229.1.2.3.6.1.1"
def subportBase = "1.3.6.1.4.1.42229.1.2.3.7.1.1"

def rxPowerOid, txPowerOid, adminStatusOid, operStatusOid

if (instanceType == "subport") {
    rxPowerOid = "${subportBase}.16.${wildvalue}"
    txPowerOid = "${subportBase}.17.${wildvalue}"
    adminStatusOid = "${subportBase}.5.${wildvalue}"
    operStatusOid = "${subportBase}.6.${wildvalue}"
} else {
    rxPowerOid = "${portBase}.4.${wildvalue}"
    txPowerOid = "${portBase}.5.${wildvalue}"
    adminStatusOid = "${portBase}.19.${wildvalue}"
    operStatusOid = "${portBase}.20.${wildvalue}"
}

def rxPower = "NaN"
def txPower = "NaN"
def adminStatus = "NaN"
def operStatus = "NaN"

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

println "RxOpticalPower=${rxPower}"
println "TxOpticalPower=${txPower}"
println "AdminStatus=${adminStatus}"
println "OperStatus=${operStatus}"

return 0
```

---

## Datapoints

### Normal Datapoints (4)

| Name | Description | Metric Type | Raw Metric | Post Processor | Threshold |
|------|-------------|-------------|------------|----------------|-----------|
| **AdminStatus** | Admin status: 1=up, 2=down | Gauge | output | namevalue(AdminStatus) | - |
| **OperStatus** | Oper status: 1=up, 2=down | Gauge | output | namevalue(OperStatus) | - |
| **RxOpticalPower** | Received optical power in dBm | Gauge | output | namevalue(RxOpticalPower) | < 10 (24h, Dynamic: 10) |
| **TxOpticalPower** | Transmitted optical power in dBm | Gauge | output | namevalue(TxOpticalPower) | - |

### Complex Datapoints (1)

| Name | Description | Metric Type | Method | Calculation |
|------|-------------|-------------|--------|-------------|
| **RxOpticalPowerAlert** | Rx power for alerting (NaN when admin-down) | Gauge | Expression | `AdminStatus,1,EQ,RxOpticalPower,100,IF` |

### Datapoint Configuration Details

#### AdminStatus
```json
{
  "name": "AdminStatus",
  "description": "AdminStatus",
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
  "description": "OperStatus",
  "type": "gauge",
  "dataType": 7,
  "useValue": "output",
  "interpretMethod": "namevalue",
  "interpretExpr": "OperStatus",
  "noData": "Do not trigger an alert"
}
```

#### RxOpticalPower
```json
{
  "name": "RxOpticalPower",
  "description": "RxOpticalPower",
  "type": "gauge",
  "dataType": 7,
  "useValue": "output",
  "interpretMethod": "namevalue",
  "interpretExpr": "RxOpticalPower",
  "threshold": "< 10",
  "noData": "Do not trigger an alert"
}
```

#### TxOpticalPower
```json
{
  "name": "TxOpticalPower",
  "description": "TxOpticalPower",
  "type": "gauge",
  "dataType": 7,
  "useValue": "output",
  "interpretMethod": "namevalue",
  "interpretExpr": "TxOpticalPower",
  "noData": "Do not trigger an alert"
}
```

#### RxOpticalPowerAlert (Complex)
```json
{
  "name": "RxOpticalPowerAlert",
  "description": "Rx power for alerting (NaN when admin-down)",
  "type": "gauge",
  "dataType": 7,
  "interpretMethod": "expression",
  "interpretExpr": "AdminStatus,1,EQ,RxOpticalPower,100,IF",
  "noData": "Do not trigger an alert"
}
```

---

## Graphs

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
| AdminStatusGraph | Line | Admin | Blue 1 | Yes |
| OperStatusGraph | Line | Oper | Green 2 | Yes |

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

---

## Instance Properties

Set during Active Discovery for each port/subport:

| Property | Description | Example |
|----------|-------------|---------|
| `auto.instance.type` | "port" or "subport" | `subport` |
| `auto.port.speed` | Speed in bps | `10000000000` |
| `auto.port.mode` | Human-readable mode | `10GbE` |
| `auto.port.type` | Port type string | `client-subport` |
| `auto.service.label` | Circuit description | `12AD1:ACT` |

---

## Notes

- **Port vs Subport:** Discovery script discovers both ports and subports, with collection script routing to correct OIDs based on `auto.instance.type` property
- **-99.0 Value:** Indicates no signal / laser off
- **Virtual Datapoints:** Port Status graph uses virtual datapoints to create visual indication (6/-6 for up/down)
