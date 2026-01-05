# LogicModule: Infinera_Groove_StandingAlarms

Monitors active/standing alarms on Infinera Groove G30 optical transport systems.

---

## Basic Information (Info Tab)

| Field | Value |
|-------|-------|
| **Name** | `Infinera_Groove_StandingAlarms` |
| **Resource Label** | `Standing Alarms` |
| **Description** | Monitors active/standing alarms on Infinera Groove G30 optical transport systems |
| **Tags** | `alarm,dx,infinera,optical` |
| **Group** | `Optical Transport` |
| **Collection Method** | `SNMP` |
| **Collection Schedule** | `3 minutes` |
| **Multi-Instance** | `Yes` |
| **Use Wildvalue as Unique Identifier** | `No` |
| **Technical Notes** | Enterprise OID: .1.3.6.1.4.1.42229<br>MIB: CORIANT-GROOVE-MIB<br>Table: standingConditionTable |

---

## AppliesTo

```
hasCategory("InfineraGroove")
```

---

## Active Discovery

| Field | Value |
|-------|-------|
| **Discovery Schedule** | `0 minutes` (run once / on demand) |
| **Group Method** | `Manual` |
| **Disable Discovered Instances** | `No` |
| **Automatically Delete Instances** | `Yes` |
| **Delete Instance Data** | `Delete Immediately` |
| **Discovery Method** | `SCRIPT` |
| **Script Type** | `Embedded Groovy Script` |

### Active Discovery Script

```groovy
/*
 * Infinera Groove Standing Alarms - Active Discovery Script v7
 *
 * Fixed: Index starts at tableOidLen + 3 (table.entry.column.columnIndex.INDEX)
 */

import com.santaba.agent.groovyapi.snmp.Snmp

def host = hostProps.get("system.hostname")

def fmEntityOid = "1.3.6.1.4.1.42229.1.2.1.6.1.1.1"
def descriptionOid = "1.3.6.1.4.1.42229.1.2.1.6.1.1.9"

def fmEntityData
def descriptionData

try {
    fmEntityData = Snmp.walkAsMap(host, fmEntityOid, null)
    descriptionData = Snmp.walkAsMap(host, descriptionOid, null)
} catch (Exception e) {
    println "SNMP walk failed: ${e.message}"
    return 1
}

if (!fmEntityData || fmEntityData.isEmpty()) {
    return 0
}

/**
 * Detects entity type and returns [type, patternPartCount]
 */
def detectEntityType(String oidValue) {
    if (!oidValue) return ["unknown", 0]

    def patterns = [
        ["1.3.6.1.4.1.42229.1.2.3.1", "shelf", 11],
        ["1.3.6.1.4.1.42229.1.2.3.2", "card", 11],
        ["1.3.6.1.4.1.42229.1.2.3.5", "subcard", 11],
        ["1.3.6.1.4.1.42229.1.2.3.8", "pluggable", 11],
        ["1.3.6.1.4.1.42229.1.2.4.1.1", "100gbe", 12],
        ["1.3.6.1.4.1.42229.1.2.4.1.2", "40gbe", 12],
        ["1.3.6.1.4.1.42229.1.2.4.1.3", "10gbe", 12],
        ["1.3.6.1.4.1.42229.1.2.4.1.5", "odu", 12],
        ["1.3.6.1.4.1.42229.1.2.4.1.9", "otu", 12],
        ["1.3.6.1.4.1.42229.1.2.4.5.2", "ots", 12],
        ["1.3.6.1.4.1.42229.1.2.4.5.5", "gopt", 12],
        ["1.3.6.1.4.1.42229.1.2.4.5.12", "nmc", 12],
        ["1.3.6.1.4.1.42229.1.2.6.2", "xcon", 11],
        ["1.3.6.1.4.1.42229.1.2.10.3", "ntp", 11]
    ]

    def bestMatch = ""
    def bestType = "unknown"
    def bestLen = 0

    patterns.each { item ->
        def pattern = item[0]
        def type = item[1]
        def len = item[2]
        if (oidValue.startsWith(pattern) && pattern.length() > bestMatch.length()) {
            bestMatch = pattern
            bestType = type
            bestLen = len
        }
    }

    return [bestType, bestLen]
}

/**
 * Decodes ASCII characters embedded in an OID string
 */
def decodeAsciiFromOid(String oidValue) {
    if (!oidValue) return null

    def parts = oidValue.split("\\.")
    def allMatches = []

    for (i in 0..<parts.size()) {
        try {
            def possibleLen = parts[i].toInteger()

            if (possibleLen >= 1 && possibleLen <= 50 && (i + possibleLen) < parts.size()) {
                def chars = []
                def valid = true

                for (j in 1..possibleLen) {
                    def code = parts[i + j].toInteger()
                    if (code >= 32 && code <= 126) {
                        chars << (char)code
                    } else {
                        valid = false
                        break
                    }
                }

                if (valid && chars.size() == possibleLen && possibleLen >= 3) {
                    allMatches << chars.join("")
                }
            }
        } catch (Exception e) {
            continue
        }
    }

    def portMatch = allMatches.find { it.contains("/") }
    if (portMatch) return portMatch

    def ipMatch = allMatches.find { it =~ /^\d+\.\d+\.\d+\.\d+$/ }
    if (ipMatch) return ipMatch

    return allMatches.max { it.length() }
}

/**
 * Parses numeric index based on entity type and known table OID length
 * Structure: table.entry.column.columnIndex.INDEX
 * So index starts at tableOidLen + 3
 */
def parseNumericIndex(String oidValue, String entityType, int tableOidLen) {
    if (!oidValue || tableOidLen == 0) return null

    def parts = oidValue.split("\\.").collect {
        try { it.toInteger() } catch (Exception e) { 0 }
    }

    // Index starts after: table + .1.1.1 (entry.column.columnIndex)
    def indexStart = tableOidLen + 3

    if (indexStart >= parts.size()) return null

    def indexParts = parts[indexStart..<parts.size()]

    if (indexParts.size() < 2) return null

    // Format based on entity type
    if (entityType == "pluggable") {
        if (indexParts.size() >= 4) {
            def shelf = indexParts[0]
            def slot = indexParts[1]
            def port = indexParts[3]
            return "${shelf}/${slot}/${port}"
        } else if (indexParts.size() >= 3) {
            return "${indexParts[0]}/${indexParts[1]}/${indexParts[2]}"
        }
    } else if (entityType in ["100gbe", "40gbe", "10gbe"]) {
        if (indexParts.size() >= 4) {
            def shelf = indexParts[0]
            def slot = indexParts[1]
            def port = indexParts[3]
            return "${shelf}/${slot}/${port}"
        } else if (indexParts.size() >= 3) {
            return "${indexParts[0]}/${indexParts[1]}/${indexParts[2]}"
        }
    } else if (entityType == "subcard") {
        if (indexParts.size() >= 3) {
            return "${indexParts[0]}/${indexParts[1]}.${indexParts[2]}"
        }
    } else if (entityType in ["odu", "otu"]) {
        if (indexParts.size() >= 4) {
            def shelf = indexParts[0]
            def slot = indexParts[1]
            def port = indexParts[3]
            return "${shelf}/${slot}/${port}"
        } else if (indexParts.size() >= 3) {
            return "${indexParts[0]}/${indexParts[1]}/${indexParts[2]}"
        }
    } else {
        if (indexParts.size() >= 3) {
            return "${indexParts[0]}/${indexParts[1]}/${indexParts[2]}"
        } else if (indexParts.size() == 2) {
            return "${indexParts[0]}/${indexParts[1]}"
        }
    }

    return null
}

/**
 * Extracts the base port (strips wavelength channel if present)
 */
def getBasePort(String portName) {
    if (!portName) return null
    def matcher = portName =~ /^(.+?)\/(\d{6})$/
    if (matcher.matches()) {
        return matcher[0][1]
    }
    return portName
}

// Track unique alarms
def seenAlarms = [:] as Map

fmEntityData.each { index, value ->
    def description = descriptionData.get(index)?.toString()?.trim() ?: "Unknown Alarm"
    def oidValue = value.toString()

    // Detect entity type from table OID
    def typeInfo = detectEntityType(oidValue)
    def entityType = typeInfo[0]
    def tableOidLen = typeInfo[1]

    // Try ASCII decode first
    def entityName = decodeAsciiFromOid(oidValue)

    // If ASCII decode failed, try numeric parsing
    if (!entityName) {
        def numericPath = parseNumericIndex(oidValue, entityType, tableOidLen)
        if (numericPath && entityType != "unknown") {
            entityName = "${entityType}-${numericPath}"
        } else if (numericPath) {
            entityName = numericPath
        }
    }

    // Get base port (without wavelength)
    def basePort = getBasePort(entityName)

    // Create deduplication key
    def dedupeKey = "${basePort ?: entityName ?: 'unknown'}::${description}"

    if (seenAlarms.containsKey(dedupeKey)) {
        seenAlarms[dedupeKey].suppressedCount++
        return
    }

    seenAlarms[dedupeKey] = [
        index: index,
        basePort: basePort,
        entityName: entityName,
        entityType: entityType,
        description: description,
        suppressedCount: 0
    ]
}

// Output deduplicated alarms
seenAlarms.each { key, alarm ->
    def displayPort = alarm.basePort ?: alarm.entityName ?: "Unknown"
    def displayName = "${displayPort} - ${alarm.description}"

    if (alarm.suppressedCount > 0) {
        displayName = "${displayName} (${alarm.suppressedCount + 1} channels)"
    }

    displayName = displayName.replaceAll("\\s+", " ").trim()

    println "${alarm.index}##${displayName}##${alarm.description}"
}

return 0
```

---

## Collection

**Collection Method:** Direct SNMP (not script-based)

The datapoints use direct SNMP OID queries with `##WILDVALUE##` substitution.

---

## Datapoints

### Normal Datapoints (3)

| Name | Description | Metric Type | OID | Min | Max | Threshold |
|------|-------------|-------------|-----|-----|-----|-----------|
| **ConditionType** | Alarm condition code per CORIANT-GROOVE-MIB | Gauge | `.1.3.6.1.4.1.42229.1.2.1.6.1.1.2.##WILDVALUE##` | 1 | 11100 | - |
| **ServiceAffecting** | Traffic impact: 1=NSA, 2=SA | Gauge | `.1.3.6.1.4.1.42229.1.2.1.6.1.1.6.##WILDVALUE##` | 1 | 2 | `>= 2 2 2` |
| **SeverityLevel** | Severity: 1=cleared to 6=critical | Gauge | `.1.3.6.1.4.1.42229.1.2.1.6.1.1.7.##WILDVALUE##` | 1 | 6 | `>= 4 5 6` |

### Datapoint Configuration Details

#### ConditionType
```json
{
  "name": "ConditionType",
  "description": "Alarm condition code per CORIANT-GROOVE-MIB. Common values: 17=linkdown, 18=los, 19=lol, 20=lofOtu, 100=oog, 106=autoshutoff.",
  "type": "gauge",
  "dataType": 7,
  "min": "1",
  "max": "11100",
  "interpretMethod": "none",
  "config": {
    "oid": ".1.3.6.1.4.1.42229.1.2.1.6.1.1.2.##WILDVALUE##"
  },
  "noData": "Do not trigger an alert"
}
```

#### ServiceAffecting
```json
{
  "name": "ServiceAffecting",
  "description": "Whether alarm impacts traffic: 1=NSA (non-service-affecting), 2=SA (service-affecting)",
  "type": "gauge",
  "dataType": 7,
  "min": "1",
  "max": "2",
  "threshold": ">= 2 2 2",
  "interpretMethod": "none",
  "config": {
    "oid": ".1.3.6.1.4.1.42229.1.2.1.6.1.1.6.##WILDVALUE##"
  },
  "noData": "Do not trigger an alert"
}
```

#### SeverityLevel
```json
{
  "name": "SeverityLevel",
  "description": "Alarm severity: 1=cleared, 2=indeterminate, 3=warning, 4=minor, 5=major, 6=critical",
  "type": "gauge",
  "dataType": 7,
  "min": "1",
  "max": "6",
  "threshold": ">= 4 5 6",
  "interpretMethod": "none",
  "config": {
    "oid": ".1.3.6.1.4.1.42229.1.2.1.6.1.1.7.##WILDVALUE##"
  },
  "noData": "Do not trigger an alert"
}
```

---

## Graphs

No graphs defined for this DataSource.

---

## Alert Thresholds

| Datapoint | Warning | Error | Critical |
|-----------|---------|-------|----------|
| ServiceAffecting | >= 2 | >= 2 | >= 2 |
| SeverityLevel | >= 4 | >= 5 | >= 6 |

---

## Notes

- **Deduplication:** The discovery script deduplicates wavelength-level alarms to port-level to reduce alert storms
- **Entity Detection:** Supports 14 entity types (shelf, card, subcard, pluggable, 100gbe, 40gbe, 10gbe, odu, otu, ots, gopt, nmc, xcon, ntp)
- **ASCII Decoding:** Handles ASCII-encoded port names in OID indices
