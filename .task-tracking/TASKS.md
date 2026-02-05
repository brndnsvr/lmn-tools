# Tasks

## Inbox

*Empty*

---

## Inflight

*Empty*

---

## Next

### T-024: Implement Users/Roles/Admins Service
**Labels:** `feature`, `api-parity`
**Location:** `src/lmn_tools/services/users.py` (new)
**Priority:** High - Essential for admin operations

Implement `UserService` and `RoleService` for managing admin users and RBAC.

**Endpoints already defined:**
- `LMEndpoints.USERS` - `/setting/admins`
- `LMEndpoints.USER_BY_ID` - `/setting/admins/{admin_id}`
- `LMEndpoints.ROLES` - `/setting/roles`
- `LMEndpoints.ROLE_BY_ID` - `/setting/roles/{role_id}`

**UserService Methods:**
- `list()` - List admin users
- `get(user_id)` - Get user details
- `create(username, email, roles)` - Create new admin
- `update(user_id, data)` - Update user info
- `delete(user_id)` - Delete user
- `reset_password(user_id)` - Trigger password reset
- `enable(user_id)` / `disable(user_id)` - Enable/disable account
- `list_tokens(user_id)` - List user's API tokens (delegates to APITokenService)

**RoleService Methods:**
- `list()` - List all roles
- `get(role_id)` - Get role details
- `create(name, privileges)` - Create custom role
- `update(role_id, data)` - Update role
- `delete(role_id)` - Delete custom role
- `get_privileges(role_id)` - Get role permissions

**CLI Commands:**
- `lmn user list` - List users
- `lmn user get <id>` - Get user details
- `lmn user create` - Create new user (interactive)
- `lmn user disable <id>` - Disable user
- `lmn role list` - List roles
- `lmn role get <id>` - Get role permissions

**Tests:**
- Service method tests
- Role privilege validation
- User creation/deletion flows

**Estimated Effort:** 400-500 lines (service + CLI + tests)

---

### T-025: Implement Metrics/Data Service
**Labels:** `feature`, `api-parity`
**Location:** `src/lmn_tools/services/metrics.py` (new)
**Priority:** High - Core value prop for monitoring data

Implement `MetricsService` for fetching time-series data and graphs.

**Endpoints already defined:**
- `LMEndpoints.DEVICE_DATA` - Device instance data
- `LMEndpoints.DEVICE_INSTANCE_DATA` - Instance-level data

**Required Methods:**
- `get_device_data(device_id, datasource_id, instance_id, datapoint, start, end)` - Fetch time-series
- `get_latest_data(device_id, datasource_id, instance_id)` - Get most recent values
- `get_aggregated_data(device_id, datasource_id, aggregate_func)` - Get aggregated metrics
- `get_graph_data(device_id, graph_id, start, end)` - Fetch graph data
- `export_csv(device_id, datasource_id, start, end)` - Export metrics to CSV

**CLI Commands:**
- `lmn metrics get` - Fetch time-series data
- `lmn metrics latest` - Get latest datapoint values
- `lmn metrics export` - Export to CSV/JSON

**Considerations:**
- Handle large datasets with pagination
- Support different time ranges (1h, 1d, 1w, custom)
- Support aggregation functions (avg, min, max, sum)
- Format timestamps consistently

**Tests:**
- Test time range calculations
- Test data aggregation
- Test CSV export formatting

**Estimated Effort:** 350-450 lines (service + CLI + tests)

---

### T-026: Implement Alert Rules Service
**Labels:** `feature`, `api-parity`
**Location:** `src/lmn_tools/services/alerts.py` (extend existing)
**Priority:** Medium - Complete the alerting picture

Extend `AlertService` or create `AlertRuleService` for managing alert threshold rules.

**Endpoints already defined:**
- `LMEndpoints.ALERT_RULES` - `/setting/alert/rules`
- `LMEndpoints.ALERT_RULE_BY_ID` - `/setting/alert/rules/{rule_id}`

**Required Methods:**
- `list_rules()` - List alert rules
- `get_rule(rule_id)` - Get rule details
- `create_rule(name, priority, escalation_chain, conditions)` - Create alert rule
- `update_rule(rule_id, data)` - Update rule
- `delete_rule(rule_id)` - Delete rule
- `enable_rule(rule_id)` / `disable_rule(rule_id)` - Toggle rule

**CLI Commands:**
- `lmn alert-rule list` - List alert rules
- `lmn alert-rule get <id>` - Get rule details
- `lmn alert-rule create` - Create rule (interactive or from file)
- `lmn alert-rule enable/disable <id>` - Toggle rule

**Tests:**
- Rule CRUD operations
- Rule condition validation
- Priority ordering

**Estimated Effort:** 250-300 lines (service + CLI + tests)

---

### T-027: Implement Device Properties Service
**Labels:** `feature`, `api-parity`
**Location:** `src/lmn_tools/services/devices.py` (extend existing)
**Priority:** Medium - Essential for device management

Extend `DeviceService` with property management methods.

**Endpoints already defined:**
- `LMEndpoints.DEVICE_PROPERTIES` - `/device/devices/{device_id}/properties`
- `LMEndpoints.DEVICE_GROUP_PROPERTIES` - `/device/groups/{group_id}/properties`

**Required Methods:**
- `get_properties(device_id)` - Get all device properties
- `set_property(device_id, name, value)` - Set single property
- `set_properties(device_id, properties)` - Bulk set properties
- `delete_property(device_id, name)` - Delete property
- `get_group_properties(group_id)` - Get group-level properties
- `set_group_property(group_id, name, value)` - Set group property

**CLI Commands:**
- `lmn device property list <device_id>` - List device properties
- `lmn device property set <device_id> <name> <value>` - Set property
- `lmn device property delete <device_id> <name>` - Delete property
- `lmn device-group property list <group_id>` - List group properties

**Tests:**
- Property CRUD operations
- Bulk property updates
- Property inheritance (group vs device)

**Estimated Effort:** 200-250 lines (service + CLI + tests)

---

### T-028: Implement Reports Service
**Labels:** `feature`, `api-parity`
**Location:** `src/lmn_tools/services/reports.py` (new)
**Priority:** Low - Commonly used but not critical

Implement `ReportService` for managing scheduled reports.

**Endpoints already defined:**
- `LMEndpoints.REPORTS` - `/report/reports`
- `LMEndpoints.REPORT_BY_ID` - `/report/reports/{report_id}`

**Required Methods:**
- `list()` - List reports
- `get(report_id)` - Get report details
- `create(name, type, schedule, recipients)` - Create scheduled report
- `update(report_id, data)` - Update report config
- `delete(report_id)` - Delete report
- `run_now(report_id)` - Execute report immediately
- `get_executions(report_id)` - Get report execution history

**CLI Commands:**
- `lmn report list` - List reports
- `lmn report get <id>` - Get report details
- `lmn report run <id>` - Execute report now
- `lmn report history <id>` - View execution history

**Tests:**
- Report CRUD operations
- Schedule validation
- Report execution

**Estimated Effort:** 250-300 lines (service + CLI + tests)

---

---

## Backlog

### T-007: Standardize response unwrapping pattern
**Labels:** `refactor`

Mixed patterns for handling API response wrappers:
- Some use `response.get("data", response)`
- Some use `response.get("items", response.get("data", {}).get("items", []))`
- CLI has `unwrap_response()` but services don't use it

**Fix:**
- Document that `LMClient._handle_response()` normalizes responses
- Services should rely on normalized format
- Use `unwrap_response()` consistently in CLI commands

---

### T-008: Use endpoint constants instead of hardcoded strings
**Labels:** `refactor`

`constants.LMEndpoints` defines all API endpoints but services hardcode paths.

**Current:**
```python
@property
def base_path(self) -> str:
    return "/device/devices"
```

**Should be:**
```python
from lmn_tools.constants import LMEndpoints

@property
def base_path(self) -> str:
    return LMEndpoints.DEVICES
```

---

### T-009: Add missing factory functions for services
**Labels:** `refactor`
**Location:** `src/lmn_tools/services/alerts.py`

Some services lack factory functions:
- `EscalationChainService` - missing `escalation_chain_service()`
- `IntegrationService` - missing `integration_service()`
- `WebsiteService` - missing `website_service()`

**Decision:** Either add factory functions for all services OR remove them entirely and use constructors directly. Be consistent.

---

### T-010: Add retry logic for transient failures
**Labels:** `feature`
**Location:** `src/lmn_tools/api/client.py`

The client raises `APIRateLimitError` with `retry_after` but doesn't implement automatic retries.

**Tasks:**
- Add optional retry with exponential backoff in `request()` method
- Consider using `tenacity` library or simple retry loop
- Make retry behavior configurable via `LMClientConfig`
- Only retry on rate limits and connection errors, not auth/validation

---

### T-011: Fix hardcoded SDT time calculation
**Labels:** `bug`
**Location:** `src/lmn_tools/services/alerts.py:267-270`

Uses local system time which may be in wrong timezone. LM API expects UTC milliseconds.

**Fix:** Create `src/lmn_tools/utils/time.py`:
```python
from datetime import datetime, timezone

def utc_now_ms() -> int:
    """Return current UTC time as epoch milliseconds."""
    return int(datetime.now(timezone.utc).timestamp() * 1000)

def utc_timestamp_ms(dt: datetime) -> int:
    """Convert datetime to UTC epoch milliseconds."""
    return int(dt.astimezone(timezone.utc).timestamp() * 1000)
```

---

### T-012: Add input validation in CLI commands
**Labels:** `bug`
**Location:** `src/lmn_tools/cli/commands/device.py:318-322`

No validation that JSON properties are actually a dict with string keys/values.

**Fix:**
```python
if not isinstance(props, dict):
    raise typer.BadParameter("Properties must be a JSON object")
if not all(isinstance(k, str) and isinstance(v, str) for k, v in props.items()):
    raise typer.BadParameter("Property keys and values must be strings")
```

---

### T-013: Add CLI test coverage
**Labels:** `infra`
**Location:** `tests/`

No tests for CLI commands. 31 command modules have significant logic.

**Tasks:**
- Create `tests/cli/conftest.py` with common fixtures
- Add smoke tests using `typer.testing.CliRunner`
- Test credential validation paths
- Test error handling for common failures

---

### T-014: Add context manager to LMClient
**Labels:** `feature`
**Location:** `src/lmn_tools/api/client.py`

`LMClient` uses `requests.Session()` but doesn't implement context manager protocol.

**Fix:**
```python
def close(self) -> None:
    """Close the underlying session."""
    self._session.close()

def __enter__(self) -> LMClient:
    return self

def __exit__(self, *args) -> None:
    self.close()
```

---

### T-015: Standardize delete confirmation pattern
**Labels:** `refactor`
**Locations:**
- `src/lmn_tools/cli/commands/device.py:392-397` - fetches resource name before confirmation
- `src/lmn_tools/cli/commands/opsnote.py:213-217` - just uses ID in confirmation

Standardize on fetching resource name/displayName before confirmation for better UX.

---

### T-016: Rename parameter shadowing builtin `filter`
**Labels:** `refactor`, `breaking`
**Location:** `src/lmn_tools/services/base.py:50`, various CLI commands

Parameter shadows builtin `filter()`. Rename to `filter_str` or `query`.

---

### T-017: Rename parameter shadowing builtin `id`
**Labels:** `refactor`, `breaking`
**Location:** `src/lmn_tools/services/base.py:79`

Parameter shadows builtin `id()`. Rename to `resource_id` or `item_id`.

**Note:** Coordinate with T-016 for breaking changes.

---

### T-018: Fix type ignore without explanation
**Labels:** `refactor`
**Location:** `src/lmn_tools/cli/utils/client.py:42`

```python
return LMClient.from_credentials(settings.credentials)  # type: ignore
```

**Fix:**
```python
assert settings.credentials is not None  # Checked by has_credentials
return LMClient.from_credentials(settings.credentials)
```

---

### T-019: Audit unused service exports
**Labels:** `refactor`
**Location:** `src/lmn_tools/services/__init__.py`

Check if all exported services are actually used. Some may have been added speculatively.

---

### T-020: Document dataclass vs Pydantic convention
**Labels:** `docs`
**Location:** `src/lmn_tools/auth/hmac.py:24-47`

Mixing dataclasses and pydantic models requires documentation.

**Guideline:**
- **Dataclasses**: Internal DTOs (like `AuthHeaders`)
- **Pydantic**: Configuration and external data validation (like `LMCredentials`)

Document in CONTRIBUTING.md or architecture docs.

---

### T-021: Document Settings singleton behavior
**Labels:** `docs`
**Location:** `src/lmn_tools/core/config.py:137-138`

`Path.home()` is evaluated at import time inside the lambda. Cached `_settings` won't reflect `$HOME` changes.

**Tasks:**
- Document singleton caching behavior in `get_settings()` docstring
- Note when settings are evaluated
- Document `reset_settings()` for testing

---

### T-022: Create Architecture Decision Records (ADRs)
**Labels:** `docs`

Recommended ADRs to document:
- **ADR-001**: Service Layer Pattern - Template Method via `BaseService`
- **ADR-002**: CLI-Service-Client Layering - CLI never calls `LMClient` directly
- **ADR-003**: Response Normalization Contract - where unwrapping happens
- **ADR-004**: Dataclass vs Pydantic usage guidelines

---

## Done

### T-023: Implement Collectors Service ✓
**Labels:** `feature`, `api-parity`
Implemented `CollectorService` and `CollectorGroupService` with comprehensive CRUD operations and specialized methods.

**New Files:**
- `src/lmn_tools/services/collectors.py` (167 lines) - Service classes with CollectorStatus enum
- `tests/services/test_collectors.py` (175 lines) - Comprehensive test coverage (13 tests)

**Modified Files:**
- `src/lmn_tools/cli/commands/collector.py` - Refactored to use service module, added 4 new commands
- `src/lmn_tools/services/__init__.py` - Added exports for new services

**Implemented Methods:**
- `list_by_group(group_id)` - Filter collectors by group
- `list_by_status(status)` - Filter by CollectorStatus enum
- `list_down()` - Convenience for down collectors
- `get_status(collector_id)` - Health metrics extraction
- `get_installer_url(platform, version)` - Download URLs
- `escalate_to_version(collector_id, version)` - Version upgrades

**New CLI Commands:**
- `lmn collector update` - Update collector configuration
- `lmn collector download` - Get installer download URL
- `lmn collector upgrade` - Upgrade collector to specific version
- `lmn collector delete` - Delete a collector

**Results:**
- All 222 tests pass (209 existing + 13 new)
- Zero linting errors
- >90% test coverage on new code
- Uses LMEndpoints constants (not hardcoded paths)

---

### T-006: Extract duplicate _format_timestamp() to utility ✓
**Labels:** `refactor`
Created `src/lmn_tools/cli/utils/time.py` with three time formatting utilities:
- `format_timestamp(ts, format)` - Handles both standard and seconds format, auto-detects ms/sec precision
- `format_duration(start, end)` - Formats time spans between two timestamps
- `format_duration_from_now(start)` - Calculates duration from timestamp to now

Migrated 7 command files (alert, audit, batch, netscan, opsnote, sdt, token) to use shared utilities.
Eliminated ~258 lines of duplicate code. Added comprehensive test suite (25 tests, 100% coverage).

---

### T-003: Split alerts.py into separate service files ✓
**Labels:** `refactor`
Split monolithic alerts.py (422 lines) into focused service modules:
- alerts.py (234 lines): AlertService, AlertRuleService
- sdt.py (171 lines): SDTService, SDTType enum
- escalation.py (23 lines): EscalationChainService
- integrations.py (23 lines): IntegrationService
- websites.py (36 lines): WebsiteService

Updated all imports in CLI commands and tests. All 190 tests pass.

---

### T-001: Standardize client acquisition in CLI commands ✓
**Labels:** `refactor`
Removed duplicate `_get_client()` from alert.py, now uses shared `get_client(console)`.

---

### T-004: Fix broad exception handler in BaseService.exists() ✓
**Labels:** `bug`
Now catches only `APINotFoundError` instead of swallowing all exceptions.

---

### T-005: Add test coverage for core modules ✓
**Labels:** `infra`
Added 67 unit tests for `api/client.py` (88% coverage) and `auth/hmac.py` (100% coverage).
Total coverage: 91% for both modules.

---

### T-002: Remove redundant convenience methods from LMClient ✓
**Labels:** `refactor`
Removed `find_device_by_hostname()`, `get_device_datasources()`, and `get_datasource_instances()`
from LMClient. DeviceService already provides equivalent functionality with `find_by_hostname()`,
`get_datasources()`, and `get_instances()`.

---

**Next ID:** T-029
