# Metrics Reference

Complete reference for all metrics collected from optical transport devices.

---

## Coriant Optical Interfaces

### OTS (Optical Transport Section)

| Metric | Unit | Description |
|--------|------|-------------|
| admin_status | 0/1 | Administrative state (1=up, 0=down) |
| oper_status | 0/1 | Operational state (1=up, 0=down) |
| external_tx_attenuation | dB | TX attenuation |
| fiber_length_tx_derived | km | Derived fiber length |
| span_degrade_enable | 0/1 | Span degradation monitoring enabled |
| span_degrade_loss | dB | Span loss threshold |
| span_degrade_hysteresis | dB | Hysteresis value |

### OMS (Optical Multiplex Section)

| Metric | Unit | Description |
|--------|------|-------------|
| admin_status | 0/1 | Administrative state |
| oper_status | 0/1 | Operational state |
| rx_optical_power | dBm | Received optical power |
| tx_optical_power | dBm | Transmitted optical power |
| in_optical_power_instant | dBm | Instantaneous input power |
| out_optical_power_instant | dBm | Instantaneous output power |
| statistics_last_clear | epoch | Last statistics reset time |

### OSC (Optical Supervisory Channel)

| Metric | Unit | Description |
|--------|------|-------------|
| admin_status | 0/1 | Administrative state |
| oper_status | 0/1 | Operational state |
| osc_wavelength | nm | OSC wavelength |
| osc_data_communication | 0/1 | Data communication enabled |
| rx_optical_power | dBm | Received optical power |
| tx_optical_power | dBm | Transmitted optical power |

### GOPT (Generic Optical)

| Metric | Unit | Description |
|--------|------|-------------|
| admin_status | 0/1 | Administrative state |
| oper_status | 0/1 | Operational state |
| rx_optical_power | dBm | Received optical power |
| tx_optical_power | dBm | Transmitted optical power |
| loss_tx | dB | TX loss |
| loss_rx | dB | RX loss |
| protection_switch_duration | sec | Protection switch time |
| protection_switch_count | count | Number of protection switches |

---

## Coriant Chassis

| Metric | Unit | Description |
|--------|------|-------------|
| ne_temperature | °C | Network element temperature |
| ne_altitude | m | Network element altitude |
| swload_active | 0/1 | Active software load (1=active, 0=none) |

---

## Ciena WaveServer Interfaces

### PTPs (Physical Termination Points)

| Metric | Unit | Description |
|--------|------|-------------|
| admin_status | 0/1 | Administrative state |
| oper_status | 0/1 | Operational state |
| transmitter_power | dBm | Transmitter optical power |
| transmitter_state | 0/1 | Transmitter enabled state |
| transmitter_wavelength | nm | Transmitter wavelength |
| transmitter_frequency | GHz | Transmitter frequency |
| baud_rate | GBd | Baud rate |
| actual_reach | km | Actual reach |
| estimated_fiber_length | km | Estimated fiber length |
| tx_span_loss | dB | TX span loss |
| rx_span_loss | dB | RX span loss |
| optical_return_loss | dB | Optical return loss |

### Ports (Client-side)

| Metric | Unit | Description |
|--------|------|-------------|
| admin_status | 0/1 | Administrative state |
| oper_status | 0/1 | Operational state |
| speed | Gbps | Port speed |
| oper_state_duration | sec | Time in current operational state |

---

## Ciena Chassis

| Metric | Unit | Description |
|--------|------|-------------|
| software_oper_state | 0/1 | Software operational state |

---

## Alert Recommendations

### Optical Power

| Condition | Level | Threshold | Notes |
|-----------|-------|-----------|-------|
| Low RX power | Warning | < -20 dBm | Signal getting weak |
| Low RX power | Error | < -25 dBm | Signal degraded |
| Low RX power | Critical | < -30 dBm | Signal critical/failing |
| High RX power | Warning | > 3 dBm | Signal too strong (saturation risk) |
| No signal | Info | = -99 dBm | Indicates disconnected/no signal |

### Interface Status

| Condition | Level | Threshold |
|-----------|-------|-----------|
| Interface down | Critical | oper_status == 0 |
| Admin disabled | Warning | admin_status == 0 |

### Span Loss (OTS/GOPT)

| Condition | Level | Threshold |
|-----------|-------|-----------|
| Elevated span loss | Warning | > 25 dB |
| High span loss | Error | > 30 dB |
| Critical span loss | Critical | > 35 dB |

### Chassis

| Condition | Level | Threshold |
|-----------|-------|-----------|
| High temperature | Warning | > 40°C |
| High temperature | Critical | > 50°C |
| Software not active | Critical | swload_active == 0 |

---

## Special Values

### -99 dBm (No Signal)

A value of -99 dBm indicates no optical signal is present. This is not an error condition but indicates:
- Fiber disconnected
- Remote end not transmitting
- Severe fiber break

**Recommendation**: Create a separate alert for `rx_optical_power == -99` with informational severity, distinct from "low power" alerts.

### 0000-01-01 Timestamps

Timestamps with value "0000-01-01T00:00:00.000Z" represent unset/null values. These are silently skipped during parsing and return `None` rather than logging warnings.

---

## Discovery Properties

Properties automatically discovered and available in LogicMonitor as `auto.*`:

### Coriant OTS
- `auto.interface_type` = "ots"
- `auto.fiber_type` (e.g., "SSMF")
- `auto.fiber_spectral_attenuation_tilt`

### Coriant OMS
- `auto.interface_type` = "oms"
- `auto.grid_mode` (e.g., "fixed_100G_48ch")

### Coriant OSC
- `auto.interface_type` = "osc"
- `auto.osc_mode` (e.g., "155M52")

### Coriant GOPT
- `auto.interface_type` = "gopt"

### Ciena PTP
- `auto.interface_type` = "ptp"
- `auto.xcvr_type` (transceiver type)

### Ciena Port
- `auto.interface_type` = "port"
- `auto.port_type`

---

## Output Format Examples

### Discovery Output
```
ots-1/3.1/1##ots-1/3.1/1##1/3.1/1####auto.fiber_type=SSMF&auto.interface_type=ots
oms-1/3.1/1##oms-1/3.1/1##1/3.1/1####auto.grid_mode=fixed_100G_48ch&auto.interface_type=oms
```

### Collection Output
```
ots-1/3.1/1.admin_status=1.0
ots-1/3.1/1.oper_status=0.0
ots-1/3.1/1.fiber_length_tx_derived=107.619
oms-1/3.1/1.rx_optical_power=-48.3
oms-1/3.1/1.tx_optical_power=-40.2
```

### Chassis Output
```
ne_temperature=18.3
ne_altitude=0.0
swload_active=1
```
