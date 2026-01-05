# Infinera Groove G30 - LogicMonitor DataSource Development

## Overview

This project contains LogicMonitor DataSource (LogicModule) definitions for monitoring Infinera Groove G30 optical transport equipment via SNMP.

## Device Information

- **Vendor:** Infinera / Coriant
- **Model:** Groove G30
- **Enterprise OID:** `.1.3.6.1.4.1.42229` (Infinera)
- **Product OID:** `.1.3.6.1.4.1.42229.1.2` (Groove platform)
- **MIB Reference:** Coriant-Groove.mib (G30 Release 4.6.2)

## Test Device

- **Name:** LAB OEN NODE 5
- **IP:** 10.62.4.125
- **SNMP:** v1, community=public

---

## LogicModules

| Module | Display Name | Status | Documentation |
|--------|--------------|--------|---------------|
| Infinera_Groove_StandingAlarms | Standing Alarms | Complete | [LogicModule_Infinera_Groove_StandingAlarms.md](LogicModule_Infinera_Groove_StandingAlarms.md) |
| Infinera_Port_Status | **Client Port Health** | Complete | [LogicModule_Infinera_Port_Status.md](LogicModule_Infinera_Port_Status.md) |
| Infinera_Line_Port_Health | **Line Port Health** | Complete | [LogicModule_Infinera_Line_Port_Health.md](LogicModule_Infinera_Line_Port_Health.md) |
| Infinera_Chassis_Health | **Chassis Health** | Complete | [LogicModule_Infinera_Chassis_Health.md](LogicModule_Infinera_Chassis_Health.md) |

**Note:** Client Port Health excludes line ports (portType=2), which are monitored by Line Port Health with additional coherent DSP metrics.

---

## Common OID Reference

### Port Table
**Base OID:** `1.3.6.1.4.1.42229.1.2.3.6.1.1`
**Index:** `shelf.slot.subslot.port`

| Column | OID Suffix | Field | Description |
|--------|------------|-------|-------------|
| 4 | .4 | portRxOpticalPower | Received optical power (dBm) |
| 5 | .5 | portTxOpticalPower | Transmitted optical power (dBm) |
| 16 | .16 | portName | Port name |
| 17 | .17 | portType | Port type code |
| 18 | .18 | portMode | Port speed/mode code |
| 19 | .19 | portAdminStatus | 1=up, 2=down, 3=upNoAlm |
| 20 | .20 | portOperStatus | 1=up, 2=down |
| 23 | .23 | portServiceLabel | Circuit/service description |

### Subport Table
**Base OID:** `1.3.6.1.4.1.42229.1.2.3.7.1.1`
**Index:** `shelf.slot.subslot.port.subport`

| Column | OID Suffix | Field | Description |
|--------|------------|-------|-------------|
| 2 | .2 | subportPortName | Subport name |
| 5 | .5 | subportAdminStatus | 1=up, 2=down |
| 6 | .6 | subportOperStatus | 1=up, 2=down |
| 16 | .16 | subportRxOpticalPower | Rx power (dBm) |
| 17 | .17 | subportTxOpticalPower | Tx power (dBm) |

### Standing Condition Table (Alarms)
**Base OID:** `1.3.6.1.4.1.42229.1.2.1.6.1.1`

| Column | OID Suffix | Field | Description |
|--------|------------|-------|-------------|
| 1 | .1 | standingConditionFmEntity | Entity reference |
| 2 | .2 | conditionType | Alarm condition code |
| 3 | .3 | severityLevel | 1-6 severity scale |
| 5 | .5 | serviceAffecting | 1=no, 2=yes |
| 9 | .9 | conditionDescription | Alarm description |

### ochOs Table (Coherent DSP)
**Base OID:** `1.3.6.1.4.1.42229.1.2.4.1.19.1.1`
**Index:** `shelf.slot.subslot.port`

| Column | OID Suffix | Field | Description |
|--------|------------|-------|-------------|
| 24 | .24 | ochOsOSNR | Optical SNR (dB) |
| 25 | .25 | ochOsQFactor | Q-Factor |
| 26 | .26 | ochOsPreFecBer | Pre-FEC BER |

### Post-FEC BER Table
**Base OID:** `1.3.6.1.4.1.42229.1.2.13.2.1.1`
**Index:** `shelf.slot.subslot.port.subport`

| Column | OID Suffix | Field | Description |
|--------|------------|-------|-------------|
| 1 | .1 | bitErrorRatePostFecInstant | Current Post-FEC BER |

### Chassis Health OIDs

#### CPU State Table
**Base OID:** `1.3.6.1.4.1.42229.1.2.3.35`
**Index:** `shelf.slot` (virtual slot 99 for management)

| Column | OID Suffix | Field | Description |
|--------|------------|-------|-------------|
| 1 | .1.1 | cpuStateCpuTotalUtilization | Total CPU % |

#### Memory State Table
**Base OID:** `1.3.6.1.4.1.42229.1.2.3.37`
**Index:** `shelf.slot` (virtual slot 99)

| Column | OID Suffix | Field | Description |
|--------|------------|-------|-------------|
| 1 | .1.1 | memoryStateAvailable | Total memory (bytes) |
| 2 | .1.2 | memoryStateUtilized | Used memory (bytes) |

#### Shelf Table (Temperature)
**Base OID:** `1.3.6.1.4.1.42229.1.2.3.1`
**Index:** `shelf`

| Column | OID Suffix | Field | Description |
|--------|------------|-------|-------------|
| 3 | .1.1.3 | shelfInletTemperature | Inlet temp (°C) |
| 4 | .1.1.4 | shelfOutletTemperature | Outlet temp (°C) |

#### Card Table (Fan Speed)
**Base OID:** `1.3.6.1.4.1.42229.1.2.3.3`
**Index:** `shelf.slot`

| Column | OID Suffix | Field | Description |
|--------|------------|-------|-------------|
| 7 | .1.1.7 | cardFanSpeedRate | Fan speed % (FAN cards only) |

---

## Enumeration Tables

### Port Type (portType)

| Value | Type | Description |
|-------|------|-------------|
| 1 | client | Client-facing port |
| 2 | line | Line/trunk port |
| 3 | client-subport | 10G subport of 40G breakout |
| 4 | optical | Optical port |
| 5 | otdr | OTDR port |
| 6 | optical-nomon | Optical (no monitoring) |
| 7 | ocm | Optical Channel Monitor |
| 8 | osc | Optical Supervisory Channel |
| 9 | mgmt-eth | Management Ethernet |

### Port Mode / Speed (portMode)

| Value | Mode | Speed (bps) |
|-------|------|-------------|
| 0 | notApplicable | 0 |
| 1 | t10gbe | 10,000,000,000 |
| 2 | t40gbe | 40,000,000,000 |
| 3 | t100gbe | 100,000,000,000 |
| 5 | qpsk100g | 100,000,000,000 |
| 6 | t8qam300g | 300,000,000,000 |
| 7 | t16qam200g | 200,000,000,000 |
| 10 | otu4 | 112,000,000,000 |
| 22 | t400gbe | 400,000,000,000 |
| 45 | t1gbe | 1,000,000,000 |

### Alarm Severity Levels

| Value | Severity |
|-------|----------|
| 1 | Cleared |
| 2 | Indeterminate |
| 3 | Warning |
| 4 | Minor |
| 5 | Major |
| 6 | Critical |

---

## Files

| File | Description |
|------|-------------|
| `Coriant-Groove.mib` | MIB file for Infinera Groove G30 |
| `Infinera_Groove_StandingAlarms.json` | Exported DataSource from LogicMonitor |
| `Infinera_Port_Status.json` | Exported DataSource (Client Port Health) |
| `Infinera_Line_Port_Health.json` | Exported DataSource (Line Port Health) |
| `Infinera_Chassis_Health.json` | Exported DataSource (Chassis Health) |
