# Tasks

## Inbox

*Empty*

---

## Inflight

*Empty*

---

## Next

### T-002: Move convenience methods from LMClient to services
**Labels:** `refactor`
**Location:** `src/lmn_tools/api/client.py:293-361`

These methods belong in the service layer, not the API client:
- `find_device_by_hostname()` → `DeviceService`
- `get_device_datasources()` → `DeviceService`
- `get_datasource_instances()` → `DeviceService`

**Acceptance Criteria:**
- [ ] Move methods to DeviceService
- [ ] Add deprecation warnings to LMClient methods
- [ ] Update any callers to use DeviceService

---

### T-003: Split alerts.py into separate service files
**Labels:** `refactor`
**Location:** `src/lmn_tools/services/alerts.py`

Contains 6 unrelated service classes in one file:
- `AlertService` - keep in `alerts.py`
- `AlertRuleService` - keep in `alerts.py`
- `SDTService` → move to `services/sdt.py`
- `EscalationChainService` → move to `services/escalation.py`
- `IntegrationService` → move to `services/integrations.py`
- `WebsiteService` → move to `services/websites.py`

**Acceptance Criteria:**
- [ ] Create new service files for SDT, Escalation, Integration, Website
- [ ] Move classes to appropriate files
- [ ] Update `__init__.py` exports
- [ ] Verify no import cycles

---

### T-005: Add test coverage for core modules
**Labels:** `infra`
**Location:** `tests/`

The API client and authentication modules have zero unit tests.

**Tasks:**
- Create `tests/api/test_client.py`
  - Test `LMClient.request()` with mocked responses
  - Test `LMClient.paginate()` edge cases
  - Test error handling paths (`_handle_response`)
- Create `tests/auth/test_hmac.py`
  - Test `generate_lmv1_signature()` with known test vectors
  - Test `AuthHeaders` dataclass

**Acceptance Criteria:**
- [ ] test_client.py with request/paginate/error tests
- [ ] test_hmac.py with signature verification tests
- [ ] Coverage report shows >80% for client.py and hmac.py

---

## Backlog

### T-006: Extract duplicate _format_timestamp() to utility
**Labels:** `refactor`
**Locations:**
- `src/lmn_tools/cli/commands/alert.py:38-47`
- `src/lmn_tools/cli/commands/token.py:28-36`
- `src/lmn_tools/cli/commands/opsnote.py:28-36`

Create shared function in `src/lmn_tools/cli/utils/helpers.py`:
```python
def format_timestamp(epoch_ms: int | None) -> str:
    """Format epoch milliseconds to human-readable datetime."""
    if not epoch_ms:
        return "N/A"
    dt = datetime.fromtimestamp(epoch_ms / 1000)
    return dt.strftime("%Y-%m-%d %H:%M:%S")
```

---

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

### T-001: Standardize client acquisition in CLI commands ✓
**Labels:** `refactor`
Removed duplicate `_get_client()` from alert.py, now uses shared `get_client(console)`.

---

### T-004: Fix broad exception handler in BaseService.exists() ✓
**Labels:** `bug`
Now catches only `APINotFoundError` instead of swallowing all exceptions.

---

**Next ID:** T-023
