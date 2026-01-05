# dx-junos: LogicMonitor Optimization for Juniper Networks

Project for optimizing LogicMonitor monitoring of Juniper Networks devices (SRX, QFX, EX, MX).

## Project Scope

- **Custom DataSources**: Fill gaps in built-in Juniper monitoring
- **Junos Configurations**: Templates for SNMP, SSH, and RPM
- **Device Organization**: Group structure and property inheritance
- **Phased Rollout**: Safe deployment strategy

## Current Environment

| Resource | Count | Details |
|----------|-------|---------|
| Collectors | 45 | 10 data centers + POC |
| Juniper Devices | 60 | EX3400 switches |
| Sites | 10 | DAL1/2, LAX2, ATL1, WDC1, CHI1, PHX1, NYC3, SEA1, BOS1 |

## Custom DataSources

Three custom datasources to address monitoring gaps:

1. **EVPN-VXLAN** - QFX fabric health (VNIs, VTEPs, MAC tables)
2. **Chassis Cluster** - SRX HA status (RG state, failovers, control/fabric links)
3. **Routing Table** - RIB/FIB capacity planning (route counts, FIB utilization)

## Directory Structure

```
dx-junos/
├── README.md                        # This file
├── docs/
│   ├── datasource-specs/           # Custom datasource specifications
│   │   ├── evpn-vxlan.md
│   │   ├── chassis-cluster.md
│   │   └── routing-table.md
│   ├── rollout-plan.md             # Phased deployment strategy
│   ├── device-groups.md            # Group reorganization plan
│   └── runbooks/                   # Alert response procedures
│       ├── evpn-alerts.md
│       ├── cluster-failover.md
│       └── route-table-growth.md
├── configs/
│   ├── junos/                      # Device configuration templates
│   │   ├── snmpv3-config.txt
│   │   ├── ssh-user-config.txt
│   │   └── rpm-probes-config.txt
│   └── logicmonitor/               # Exportable datasource definitions
│       ├── datasource-evpn.json
│       ├── datasource-cluster.json
│       └── datasource-routing.json
└── scripts/                        # Helper utilities
    ├── validate-snmp.py
    └── baseline-routes.py
```

## Rollout Phases

| Phase | Duration | Scope | Risk |
|-------|----------|-------|------|
| 1. POC | Week 1-2 | POC collector only | Minimal |
| 2. Pilot | Week 3-4 | DAL1 (4 devices) | Low |
| 3. Rollout | Week 5-8 | All sites | Medium |
| 4. Hardening | Week 9-10 | Group migration | Low |

## Quick Links

- [Rollout Plan](docs/rollout-plan.md)
- [Device Groups](docs/device-groups.md)
- [EVPN-VXLAN DataSource](docs/datasource-specs/evpn-vxlan.md)
- [Chassis Cluster DataSource](docs/datasource-specs/chassis-cluster.md)
- [Routing Table DataSource](docs/datasource-specs/routing-table.md)

## Prerequisites

- LogicMonitor portal access (evoquedcs)
- SNMPv3 configured on Juniper devices
- Read-only SSH user for ConfigSource
- POC collector available for testing

## Related Documentation

- [LogicMonitor Juniper DataSources](https://www.logicmonitor.com/support/juniper)
- [Juniper SNMP MIBs](https://www.juniper.net/documentation/en_US/junos/topics/reference/general/snmp-mib-explorer.html)
