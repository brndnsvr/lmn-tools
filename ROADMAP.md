# lmn-tools Roadmap

Project direction and completed milestones.

> **Note:** Detailed technical tasks and code quality improvements are tracked in [TODO.md](./TODO.md).

---

## Current Focus

### Architecture & Quality
- Maintain pure API wrapper design (no direct device connections)
- Ensure consistent patterns across all services and CLI commands
- Improve test coverage for core modules

### Planned Features
- Retry logic for rate-limited API requests
- Context manager support for `LMClient`
- CLI smoke tests for regression prevention

See [TODO.md](./TODO.md) for detailed implementation tasks.

---

## Completed

### [x] Remove Local Collectors - Make Pure API Wrapper
**Completed:** 2026-01-31

Removed all local device connection code (NETCONF, SNMP, optical collectors) to make `lmn` a pure LogicMonitor API wrapper. The tool no longer makes direct connections to network devices.

**Changes:**
- Deleted `collectors/` directory (~3,600 lines)
- Deleted `discover` and `collect` CLI commands (~590 lines)
- Deleted collector tests (~1,500 lines)
- Removed `netconf`, `snmp`, and `all` optional dependencies
- Removed unused credential classes and formatters

**Alternative Commands:**
| Old Command | New API-Based Alternative |
|-------------|---------------------------|
| `lmn discover snmp <host>` | `lmn netscan run <id>` (for device discovery) |
| `lmn discover netconf <host>` | `lmn ds test <ds-id> --device <id>` (for AD testing) |
| `lmn collect snmp <host>` | `lmn ds test <ds-id> --device <id>` (for collection testing) |

---

### [x] Comprehensive Architectural Review
**Completed:** 2026-01-31

Conducted full architectural review with multiple specialized agents:
- Identified core pattern: Layered Service Architecture with Template Method
- Documented 22 improvement items in TODO.md
- Verified all planned work aligns with existing patterns
- Architecture score: 8/10

**Key Patterns Established:**
1. **Service Layer**: `BaseService` with abstract `base_path` property
2. **CLI Pattern**: Typer apps with `_get_service()` helpers using `get_client(console)`
3. **Exception Hierarchy**: Typed exceptions with context in `core/exceptions.py`
4. **Configuration**: Pydantic Settings with `LM_` prefix environment variables

---

## Architecture Decisions

### Pure API Wrapper
- lmn-tools interacts exclusively with LogicMonitor REST API
- No direct device connections (NETCONF, SNMP, SSH)
- Device discovery via `lmn netscan` API commands
- DataSource testing via `lmn ds test` API commands

### Layered Architecture
```
CLI Commands → Services → API Client → Auth/HMAC
```
- CLI never calls `LMClient` directly
- Services encapsulate business logic
- API client handles HTTP, pagination, error normalization

### Adding New API Resources
1. Create service in `services/{resource}.py` extending `BaseService`
2. Add factory function and export in `services/__init__.py`
3. Create CLI commands in `cli/commands/{resource}.py`
4. Register in `cli/main.py`
