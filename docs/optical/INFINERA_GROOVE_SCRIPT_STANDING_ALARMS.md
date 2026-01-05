# Infinera Groove Standing Alarms - Groovy Discovery Script
## Technical Code Breakdown

---

## Overview

This document provides a detailed walkthrough of the Active Discovery Groovy script used in the Infinera Groove Standing Alarms DataSource. Each section of the script is explained with code snippets and technical rationale.

**Script Purpose:** Discover active alarms from Infinera Groove optical transport devices and translate cryptic SNMP OID values into human-readable instance names.

**Script Version:** v7 (Final)

---

## Table of Contents

1. [Import Statement](#1-import-statement)
2. [Host and OID Configuration](#2-host-and-oid-configuration)
3. [SNMP Data Retrieval](#3-snmp-data-retrieval)
4. [Empty Result Handling](#4-empty-result-handling)
5. [Entity Type Detection Function](#5-entity-type-detection-function)
6. [ASCII Decoding Function](#6-ascii-decoding-function)
7. [Numeric Index Parsing Function](#7-numeric-index-parsing-function)
8. [Base Port Extraction Function](#8-base-port-extraction-function)
9. [Main Processing Loop](#9-main-processing-loop)
10. [Output Generation](#10-output-generation)
11. [Complete Script Reference](#11-complete-script-reference)

---

## 1. Import Statement

```groovy
import com.santaba.agent.groovyapi.snmp.Snmp
```

### Explanation

This imports LogicMonitor's SNMP API class, which provides methods for performing SNMP operations from within Groovy scripts. The `Snmp` class is part of LogicMonitor's collector agent and includes methods like:

- `Snmp.get()` - Retrieve a single OID value
- `Snmp.walk()` - Walk an OID tree and return results as a list
- `Snmp.walkAsMap()` - Walk an OID tree and return results as a key-value map

We use `walkAsMap()` because it returns data in a format that's easy to correlate between multiple OID walks (matching by index).

---

## 2. Host and OID Configuration

```groovy
def host = hostProps.get("system.hostname")

def fmEntityOid = "1.3.6.1.4.1.42229.1.2.1.6.1.1.1"
def descriptionOid = "1.3.6.1.4.1.42229.1.2.1.6.1.1.9"
```

### Explanation

**Host Resolution:**
- `hostProps` is a LogicMonitor-provided object containing device properties
- `system.hostname` returns the device's IP address or hostname used for monitoring
- This is how the script knows which device to query

**OID Definitions:**

| Variable | OID | MIB Object | Purpose |
|----------|-----|------------|---------|
| `fmEntityOid` | .1.3.6.1.4.1.42229.1.2.1.6.1.1.1 | standingConditionFmEntity | Pointer to the alarming object (RowPointer type) |
| `descriptionOid` | .1.3.6.1.4.1.42229.1.2.1.6.1.1.9 | standingConditionConditionDescription | Human-readable alarm description text |

**OID Structure Breakdown:**
```
1.3.6.1.4.1.42229.1.2.1.6.1.1.1
│ │ │ │ │ │     │ │ │ │ │ │ └── Column 1 (fmEntity)
│ │ │ │ │ │     │ │ │ │ │ └──── Entry (.1)
│ │ │ │ │ │     │ │ │ │ └────── Table (.1)
│ │ │ │ │ │     │ │ │ └──────── standingCondition (.6)
│ │ │ │ │ │     │ │ └────────── fm (.1)
│ │ │ │ │ │     │ └──────────── coriantGroove (.2)
│ │ │ │ │ │     └────────────── coriant (.1)
│ │ │ │ │ └──────────────────── Infinera Enterprise (42229)
│ │ │ │ └────────────────────── enterprises (.4)
│ │ │ └──────────────────────── private (.1)
│ │ └────────────────────────── internet (.6)
│ └──────────────────────────── dod (.3)
└────────────────────────────── iso (.1)
```

---

## 3. SNMP Data Retrieval

```groovy
def fmEntityData
def descriptionData

try {
    fmEntityData = Snmp.walkAsMap(host, fmEntityOid, null)
    descriptionData = Snmp.walkAsMap(host, descriptionOid, null)
} catch (Exception e) {
    println "SNMP walk failed: ${e.message}"
    return 1
}
```

### Explanation

**Variable Declaration:**
- `fmEntityData` and `descriptionData` are declared outside the try block so they remain in scope after the block completes
- They will hold Map objects with index → value pairs

**SNMP Walk Calls:**
```groovy
Snmp.walkAsMap(host, fmEntityOid, null)
```

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `host` | Device IP/hostname | Target device to query |
| `fmEntityOid` | OID string | Starting OID for the walk |
| `null` | Credentials | `null` uses the device's configured SNMP credentials in LogicMonitor |

**Return Format:**
The `walkAsMap()` method returns a Map where:
- **Key:** The instance index portion of the OID (everything after the column identifier)
- **Value:** The SNMP value at that OID

Example return data:
```groovy
[
    "17.1.3.6.1.4.1.42229...": "1.3.6.1.4.1.42229.1.2.3.5.1.1.1.1.3.3",
    "18.1.3.6.1.4.1.42229...": "1.3.6.1.4.1.42229.1.2.3.8.1.1.1.1.1.0.10",
    ...
]
```

**Error Handling:**
- The try/catch block captures SNMP failures (timeout, unreachable, auth failure)
- On failure, prints an error message and returns exit code `1` (failure)
- LogicMonitor interprets non-zero return codes as script failures

---

## 4. Empty Result Handling

```groovy
if (!fmEntityData || fmEntityData.isEmpty()) {
    return 0
}
```

### Explanation

This handles the case where no alarms are present on the device:

- `!fmEntityData` - Checks if the variable is null (SNMP returned nothing)
- `fmEntityData.isEmpty()` - Checks if the Map has zero entries

**Return Code 0:**
- Returning `0` indicates successful script execution
- No output lines means no instances discovered
- This is normal behavior for a device with no active alarms

**Why This Matters:**
Without this check, the script would throw a NullPointerException when trying to iterate over a null Map in the main processing loop.

---

## 5. Entity Type Detection Function

```groovy
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
```

### Explanation

**Purpose:**
Determines what type of entity (pluggable, 100gbe, odu, etc.) an alarm is associated with by matching the OID value against known table patterns.

**Pattern Array Structure:**
Each entry is a 3-element array: `[OID pattern, entity type name, OID part count]`

```groovy
["1.3.6.1.4.1.42229.1.2.3.8", "pluggable", 11]
//  └── OID prefix           └── type     └── number of OID parts (dots + 1)
```

**Table Categories in the MIB:**

| OID Branch | Category | Entity Types |
|------------|----------|--------------|
| `.1.2.3.x` | Equipment | shelf, card, subcard, pluggable |
| `.1.2.4.1.x` | OTN Interfaces | 100gbe, 40gbe, 10gbe, odu, otu |
| `.1.2.4.5.x` | Optical Interfaces | ots, gopt, nmc |
| `.1.2.6.x` | Cross-connects | xcon |
| `.1.2.10.x` | System | ntp |

**Pattern Matching Logic:**
```groovy
if (oidValue.startsWith(pattern) && pattern.length() > bestMatch.length())
```

- Uses `startsWith()` to check if the OID value begins with the pattern
- Tracks the longest matching pattern (most specific match wins)
- Example: `.1.2.4.5.12` matches both `.1.2.4.5` and `.1.2.4.5.12`, but the longer pattern wins

**Return Value:**
Returns a 2-element array: `[entityType, patternPartCount]`
- `entityType`: String like "pluggable", "100gbe", "odu"
- `patternPartCount`: Integer used to calculate where the index starts in the OID

**Why Pattern Length Matters:**
The `patternPartCount` (11 or 12) tells us how many OID components make up the table identifier. This is critical for parsing the index portion correctly:

```
OID Value: 1.3.6.1.4.1.42229.1.2.3.8.1.1.1.1.1.0.10
           |-------- 11 parts --------|.|.|.|----------|
           Table OID                   Entry/Column  Index (1.1.0.10)
```

---

## 6. ASCII Decoding Function

```groovy
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
```

### Explanation

**Purpose:**
Some Infinera tables use ASCII-encoded strings as part of their OID index. This function finds and decodes those strings.

**How ASCII Encoding Works in SNMP:**
When a string is used as an SNMP table index, it's encoded as:
```
length.char1.char2.char3...
```

Example: The string `"1/3.1/1"` becomes:
```
7.49.47.51.46.49.47.49
│  │  │  │  │  │  │  └── ASCII 49 = '1'
│  │  │  │  │  │  └───── ASCII 47 = '/'
│  │  │  │  │  └──────── ASCII 49 = '1'
│  │  │  │  └─────────── ASCII 46 = '.'
│  │  │  └────────────── ASCII 51 = '3'
│  │  └───────────────── ASCII 47 = '/'
│  └──────────────────── ASCII 49 = '1'
└─────────────────────── Length = 7 characters
```

**Step-by-Step Algorithm:**

1. **Split OID into parts:**
```groovy
def parts = oidValue.split("\\.")
```
Converts `"1.3.6.1.4.1.42229..."` into array `["1", "3", "6", "1", ...]`

2. **Scan for length-prefixed sequences:**
```groovy
for (i in 0..<parts.size()) {
    def possibleLen = parts[i].toInteger()
```
Each OID part is tested as a potential length byte.

3. **Validate length is reasonable:**
```groovy
if (possibleLen >= 1 && possibleLen <= 50 && (i + possibleLen) < parts.size())
```
- Must be at least 1 character
- Must be at most 50 characters (reasonable string length)
- Must have enough remaining OID parts to satisfy the length

4. **Attempt to decode ASCII characters:**
```groovy
for (j in 1..possibleLen) {
    def code = parts[i + j].toInteger()
    if (code >= 32 && code <= 126) {
        chars << (char)code
    } else {
        valid = false
        break
    }
}
```
- ASCII 32-126 are printable characters (space through tilde)
- If any byte falls outside this range, the sequence isn't a valid ASCII string

5. **Validate and collect matches:**
```groovy
if (valid && chars.size() == possibleLen && possibleLen >= 3) {
    allMatches << chars.join("")
}
```
- Requires minimum 3 characters to avoid false positives
- Stores all valid decoded strings found in the OID

6. **Select best match:**
```groovy
def portMatch = allMatches.find { it.contains("/") }
if (portMatch) return portMatch

def ipMatch = allMatches.find { it =~ /^\d+\.\d+\.\d+\.\d+$/ }
if (ipMatch) return ipMatch

return allMatches.max { it.length() }
```

**Priority order:**
1. Strings containing "/" (port names like `1/3.1/1`)
2. IP addresses (NTP associations like `10.62.4.1`)
3. Longest string found (fallback)

**Real Example:**
```
Input OID: 1.3.6.1.4.1.42229.1.2.4.5.2.1.1.1.7.49.47.51.46.49.47.49
                                          │  └─────────────────────┘
                                          │  ASCII: "1/3.1/1"
                                          └── Length byte: 7

Output: "1/3.1/1"
```

---

## 7. Numeric Index Parsing Function

```groovy
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
        // Index: shelf.slot.subslot.port (e.g., 1.1.0.10 -> 1/1/10)
        if (indexParts.size() >= 4) {
            def shelf = indexParts[0]
            def slot = indexParts[1]
            def port = indexParts[3]
            return "${shelf}/${slot}/${port}"
        } else if (indexParts.size() >= 3) {
            return "${indexParts[0]}/${indexParts[1]}/${indexParts[2]}"
        }
    } else if (entityType in ["100gbe", "40gbe", "10gbe"]) {
        // Index: shelf.slot.subslot.port.subport (e.g., 1.1.0.5.4 -> 1/1/5)
        if (indexParts.size() >= 4) {
            def shelf = indexParts[0]
            def slot = indexParts[1]
            def port = indexParts[3]
            return "${shelf}/${slot}/${port}"
        } else if (indexParts.size() >= 3) {
            return "${indexParts[0]}/${indexParts[1]}/${indexParts[2]}"
        }
    } else if (entityType == "subcard") {
        // Index: shelf.slot.subslot (e.g., 1.3.3 -> 1/3.3)
        if (indexParts.size() >= 3) {
            return "${indexParts[0]}/${indexParts[1]}.${indexParts[2]}"
        }
    } else if (entityType in ["odu", "otu"]) {
        // Index: shelf.slot.subslot.port.subport... (e.g., 1.1.0.4.0 -> 1/1/4)
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
```

### Explanation

**Purpose:**
For tables that use numeric indices (not ASCII-encoded), this function extracts the shelf/slot/port numbers from the OID structure.

**OID Structure for Numeric Tables:**
```
1.3.6.1.4.1.42229.1.2.3.8.1.1.1.1.1.0.10
|-------- table --------|.|.|.|---------|
         11 parts        1 1 1  INDEX
                         │ │ │
                         │ │ └── columnIndex (always 1)
                         │ └──── column (always 1 for first column)
                         └────── entry (always 1)
```

**Key Calculation:**
```groovy
def indexStart = tableOidLen + 3
```
- `tableOidLen`: Number of parts in the table OID (e.g., 11 for pluggable)
- `+ 3`: Skip the `.entry.column.columnIndex` portion (always `.1.1.1`)
- Result: Position where the actual index data begins

**Converting OID Parts to Integers:**
```groovy
def parts = oidValue.split("\\.").collect { 
    try { it.toInteger() } catch (Exception e) { 0 }
}
```
- Splits OID string into array
- Converts each part to integer
- Returns 0 for any non-numeric values (defensive coding)

**Extracting Index Portion:**
```groovy
def indexParts = parts[indexStart..<parts.size()]
```
Uses Groovy's range operator to slice the array from `indexStart` to end.

**Entity-Specific Formatting:**

Each entity type has a different index structure:

| Entity Type | Index Structure | Example Index | Formatted Output |
|-------------|-----------------|---------------|------------------|
| pluggable | shelf.slot.subslot.port | 1.1.0.10 | 1/1/10 |
| 100gbe | shelf.slot.subslot.port.subport | 1.1.0.5.4 | 1/1/5 |
| subcard | shelf.slot.subslot | 1.3.3 | 1/3.3 |
| odu/otu | shelf.slot.subslot.port.subport.container... | 1.1.0.4.0.7.1... | 1/1/4 |

**Why Skip Subslot:**
For most entity types, `indexParts[2]` is the subslot which is typically 0 for standard configurations. The actual port number is at `indexParts[3]`:

```groovy
def shelf = indexParts[0]   // 1
def slot = indexParts[1]    // 1
// indexParts[2] = subslot  // 0 (skipped)
def port = indexParts[3]    // 10
return "${shelf}/${slot}/${port}"  // "1/1/10"
```

**Subcard Special Case:**
Subcards use a different format (`shelf/slot.subslot`) because the subslot IS the identifying element:
```groovy
return "${indexParts[0]}/${indexParts[1]}.${indexParts[2]}"  // "1/3.3"
```

---

## 8. Base Port Extraction Function

```groovy
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
```

### Explanation

**Purpose:**
DWDM wavelength channels are identified by 6-digit frequency values appended to the port name. This function strips the wavelength to get the base port for deduplication.

**Wavelength Encoding:**
Infinera uses ITU-T frequency grid values in units of 0.01 GHz:
- `191400` = 1914.00 GHz ≈ 156.60 nm (C-band)
- `194400` = 1944.00 GHz ≈ 154.21 nm (C-band)

**Example Port Names:**
```
1/3.1/1/191400  →  Base port: 1/3.1/1
1/3.1/1/191500  →  Base port: 1/3.1/1
1/3.1/1/194400  →  Base port: 1/3.1/1
```

**Regex Breakdown:**
```groovy
/^(.+?)\/(\d{6})$/
  │ │   │  │    │
  │ │   │  │    └── End of string
  │ │   │  └─────── Exactly 6 digits (wavelength)
  │ │   └────────── Literal "/" separator
  │ └────────────── Non-greedy capture group (base port)
  └──────────────── Start of string
```

**Matching Logic:**
```groovy
def matcher = portName =~ /^(.+?)\/(\d{6})$/
if (matcher.matches()) {
    return matcher[0][1]  // Return captured group 1 (base port)
}
return portName  // Return original if no wavelength suffix
```

- `matcher[0]` - The full match array
- `matcher[0][0]` - The entire matched string
- `matcher[0][1]` - First capture group (base port)
- `matcher[0][2]` - Second capture group (wavelength)

**Why Non-Greedy (`+?`):**
The `+?` makes the capture non-greedy, ensuring it captures the minimum necessary before the wavelength. This handles nested slashes correctly:
```
1/3.1/1/191400
└──────┘ captured as base port (stops at last /)
```

---

## 9. Main Processing Loop

```groovy
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
```

### Explanation

**Deduplication Map:**
```groovy
def seenAlarms = [:] as Map
```
Creates an empty Map to track unique alarms. The `as Map` cast is explicit for clarity.

**Iterating Over SNMP Results:**
```groovy
fmEntityData.each { index, value ->
```
- `index`: The OID suffix (instance identifier from the SNMP walk)
- `value`: The OID value (RowPointer to the alarming object)

**Fetching Description:**
```groovy
def description = descriptionData.get(index)?.toString()?.trim() ?: "Unknown Alarm"
```
- Uses the same `index` to look up the corresponding description
- Safe navigation (`?.`) handles null values
- Elvis operator (`?:`) provides default if null/empty

**Dual-Strategy Name Resolution:**

1. **Try ASCII decode first:**
```groovy
def entityName = decodeAsciiFromOid(oidValue)
```
Works for: ots, gopt, nmc, ntp, xcon tables

2. **Fall back to numeric parsing:**
```groovy
if (!entityName) {
    def numericPath = parseNumericIndex(oidValue, entityType, tableOidLen)
    if (numericPath && entityType != "unknown") {
        entityName = "${entityType}-${numericPath}"
    } else if (numericPath) {
        entityName = numericPath
    }
}
```
Works for: pluggable, 100gbe, odu, otu, subcard tables

**Prepending Entity Type:**
For numeric tables, we prepend the entity type to match CLI format:
```groovy
entityName = "${entityType}-${numericPath}"  // "pluggable-1/1/10"
```

**Deduplication Logic:**
```groovy
def dedupeKey = "${basePort ?: entityName ?: 'unknown'}::${description}"

if (seenAlarms.containsKey(dedupeKey)) {
    seenAlarms[dedupeKey].suppressedCount++
    return
}
```

**Key format:** `basePort::description`
- Example: `1/3.1/1::Loss Of Signal`

When multiple wavelength channels have the same alarm:
- First occurrence: Stored in map
- Subsequent occurrences: Increment `suppressedCount` and skip

**Storing Alarm Data:**
```groovy
seenAlarms[dedupeKey] = [
    index: index,
    basePort: basePort,
    entityName: entityName,
    entityType: entityType,
    description: description,
    suppressedCount: 0
]
```
Stores all relevant data for output generation.

---

## 10. Output Generation

```groovy
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

### Explanation

**LogicMonitor Discovery Output Format:**
```
wildvalue##wildalias##description
```

| Field | Purpose | Example |
|-------|---------|---------|
| `wildvalue` | Unique instance identifier (used in OID substitution) | `23.1.3.6.1.4.1.42229...` |
| `wildalias` | Human-readable display name | `1/3.1/1 - Loss Of Signal` |
| `description` | Optional description text | `Loss Of Signal` |

**Building Display Name:**
```groovy
def displayPort = alarm.basePort ?: alarm.entityName ?: "Unknown"
def displayName = "${displayPort} - ${alarm.description}"
```
Constructs: `1/3.1/1 - Loss Of Signal`

**Adding Channel Count:**
```groovy
if (alarm.suppressedCount > 0) {
    displayName = "${displayName} (${alarm.suppressedCount + 1} channels)"
}
```
If wavelengths were deduplicated: `1/3.1/1 - Loss Of Signal (42 channels)`

Note: `suppressedCount + 1` because we count the first occurrence plus all suppressed ones.

**Normalizing Whitespace:**
```groovy
displayName = displayName.replaceAll("\\s+", " ").trim()
```
Ensures clean output by:
- Collapsing multiple spaces to single space
- Trimming leading/trailing whitespace

**Output Line:**
```groovy
println "${alarm.index}##${displayName}##${alarm.description}"
```
Prints to stdout in LogicMonitor's expected format.

**Return Code:**
```groovy
return 0
```
Exit code 0 indicates successful execution. LogicMonitor will parse the stdout lines as discovered instances.

---

## 11. Complete Script Reference

```groovy
/*
 * Infinera Groove Standing Alarms - Active Discovery Script v7
 * 
 * Discovers active alarms from the standingConditionTable and creates
 * human-readable instance names. Handles both ASCII-encoded port names
 * and numeric shelf/slot/port indices. Deduplicates wavelength-level
 * alarms to prevent alert storms.
 * 
 * Output format: wildvalue##wildalias##description
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

## Summary

This script demonstrates several advanced LogicMonitor development techniques:

1. **Multi-OID correlation** - Walking two OIDs and correlating by index
2. **Pattern-based entity detection** - Determining object type from OID structure
3. **Dual decoding strategies** - ASCII string extraction and numeric index parsing
4. **Deduplication** - Consolidating related alarms to reduce noise
5. **Defensive coding** - Null checks, try/catch blocks, safe navigation operators
6. **Groovy idioms** - Maps, closures, range operators, regex matching

The result is a robust discovery script that transforms cryptic SNMP data into actionable, human-readable alarm instances.

---

*Document Version: 1.0*
*Script Version: v7*
*Last Updated: December 2024*
