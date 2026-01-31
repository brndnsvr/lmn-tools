# lmn-tools Architecture & Code Quality TODO

Generated from comprehensive architectural review on 2026-01-31.

---

## Critical - Must Fix

### [ ] 1. Standardize Client Acquisition in CLI Commands
**Location:** `src/lmn_tools/cli/commands/alert.py:24-30`

The `alert.py` command duplicates client creation logic instead of using the shared utility.

**Current (wrong):**
```python
def _get_client() -> LMClient:
    settings = get_settings()
    if not settings.has_credentials:
        console.print("[red]Error: LM credentials not configured[/red]")
        raise typer.Exit(1) from None
    return LMClient.from_credentials(settings.credentials)  # type: ignore
```

**Should be:**
```python
from lmn_tools.cli.utils import get_client

def _get_service() -> AlertService:
    return AlertService(get_client(console))
```

**Impact:** Inconsistent error handling, maintenance burden, violates DRY.

---

### [ ] 2. Move Convenience Methods from LMClient to Services
**Location:** `src/lmn_tools/api/client.py:293-361`

These methods belong in the service layer, not the API client:
- `find_device_by_hostname()` → `DeviceService`
- `get_device_datasources()` → `DeviceService`
- `get_datasource_instances()` → `DeviceService`

**Impact:** Violates single responsibility principle, makes testing harder.

---

### [ ] 3. Split alerts.py into Separate Service Files
**Location:** `src/lmn_tools/services/alerts.py`

Contains 6 unrelated service classes in one file:
- `AlertService` - keep in `alerts.py`
- `AlertRuleService` - keep in `alerts.py`
- `SDTService` → move to `services/sdt.py`
- `EscalationChainService` → move to `services/escalation.py`
- `IntegrationService` → move to `services/integrations.py`
- `WebsiteService` → move to `services/websites.py`

**Impact:** Violates single responsibility, harder to navigate codebase.

---

### [ ] 4. Fix Broad Exception Handler in BaseService.exists()
**Location:** `src/lmn_tools/services/base.py:181-185`

Currently swallows all exceptions including network errors, auth failures, rate limits.

**Current:**
```python
def exists(self, id: int) -> bool:
    try:
        self.get(id)
        return True
    except Exception:
        return False
```

**Fix:**
```python
from lmn_tools.core.exceptions import APINotFoundError

def exists(self, id: int) -> bool:
    try:
        self.get(id)
        return True
    except APINotFoundError:
        return False
    # Let other exceptions propagate
```

---

### [ ] 5. Add Test Coverage for Core Modules
**Location:** `tests/`

The API client and authentication modules have zero unit tests.

**Tasks:**
- [ ] Create `tests/api/test_client.py`
  - Test `LMClient.request()` with mocked responses
  - Test `LMClient.paginate()` edge cases
  - Test error handling paths (`_handle_response`)
- [ ] Create `tests/auth/test_hmac.py`
  - Test `generate_lmv1_signature()` with known test vectors
  - Test `AuthHeaders` dataclass

---

## Suggestions - Should Fix

### [ ] 6. Extract Duplicate _format_timestamp() to Utility
**Locations:**
- `src/lmn_tools/cli/commands/alert.py:38-47`
- `src/lmn_tools/cli/commands/token.py:28-36`
- `src/lmn_tools/cli/commands/opsnote.py:28-36`

**Fix:** Create shared function in `src/lmn_tools/cli/utils/helpers.py`:
```python
def format_timestamp(epoch_ms: int | None) -> str:
    """Format epoch milliseconds to human-readable datetime."""
    if not epoch_ms:
        return "N/A"
    dt = datetime.fromtimestamp(epoch_ms / 1000)
    return dt.strftime("%Y-%m-%d %H:%M:%S")
```

---

### [ ] 7. Standardize Response Unwrapping Pattern
**Locations:** Various services and CLI commands

**Problem:** Mixed patterns for handling API response wrappers:
- Some use `response.get("data", response)`
- Some use `response.get("items", response.get("data", {}).get("items", []))`
- CLI has `unwrap_response()` but services don't use it

**Fix:**
- Document that `LMClient._handle_response()` normalizes responses
- Services should rely on normalized format
- Use `unwrap_response()` consistently in CLI commands

---

### [ ] 8. Use Endpoint Constants Instead of Hardcoded Strings
**Location:** Various services

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

### [ ] 9. Add Missing Factory Functions for Services
**Location:** `src/lmn_tools/services/alerts.py`

Some services lack factory functions:
- `EscalationChainService` - missing `escalation_chain_service()`
- `IntegrationService` - missing `integration_service()`
- `WebsiteService` - missing `website_service()`

**Decision:** Either add factory functions for all services OR remove them entirely and use constructors directly. Be consistent.

---

### [ ] 10. Add Retry Logic for Transient Failures
**Location:** `src/lmn_tools/api/client.py`

The client raises `APIRateLimitError` with `retry_after` but doesn't implement automatic retries.

**Tasks:**
- [ ] Add optional retry with exponential backoff in `request()` method
- [ ] Consider using `tenacity` library or simple retry loop
- [ ] Make retry behavior configurable via `LMClientConfig`
- [ ] Only retry on rate limits and connection errors, not auth/validation

---

### [ ] 11. Fix Hardcoded SDT Time Calculation
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

### [ ] 12. Add Input Validation in CLI Commands
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

### [ ] 13. Add CLI Test Coverage
**Location:** `tests/`

No tests for CLI commands. 31 command modules have significant logic.

**Tasks:**
- [ ] Create `tests/cli/conftest.py` with common fixtures
- [ ] Add smoke tests using `typer.testing.CliRunner`
- [ ] Test credential validation paths
- [ ] Test error handling for common failures

**Example:**
```python
from typer.testing import CliRunner
from lmn_tools.cli.main import app

def test_device_list_requires_credentials():
    runner = CliRunner()
    result = runner.invoke(app, ["device", "list"])
    assert "credentials not configured" in result.output.lower()
```

---

### [ ] 14. Add Context Manager to LMClient
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

### [ ] 15. Standardize Delete Confirmation Pattern
**Locations:**
- `src/lmn_tools/cli/commands/device.py:392-397` - fetches resource name before confirmation
- `src/lmn_tools/cli/commands/opsnote.py:213-217` - just uses ID in confirmation

**Fix:** Standardize on fetching resource name/displayName before confirmation for better UX.

---

## Nitpicks - Optional

### [ ] 16. Rename Parameter Shadowing Builtin `filter`
**Location:** `src/lmn_tools/services/base.py:50`, various CLI commands

Parameter shadows builtin `filter()`.

**Fix:** Rename to `filter_str` or `query`.

**Note:** Breaking change for programmatic users.

---

### [ ] 17. Rename Parameter Shadowing Builtin `id`
**Location:** `src/lmn_tools/services/base.py:79`

Parameter shadows builtin `id()`.

**Fix:** Rename to `resource_id` or `item_id`.

**Note:** Breaking change - coordinate with filter rename.

---

### [ ] 18. Fix Type Ignore Without Explanation
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

### [ ] 19. Audit Unused Service Exports
**Location:** `src/lmn_tools/services/__init__.py`

Check if all exported services are actually used. Some may have been added speculatively.

---

### [ ] 20. Document Dataclass vs Pydantic Convention
**Location:** `src/lmn_tools/auth/hmac.py:24-47`

Mixing dataclasses and pydantic models requires documentation.

**Guideline:**
- **Dataclasses**: Internal DTOs (like `AuthHeaders`)
- **Pydantic**: Configuration and external data validation (like `LMCredentials`)

Document in CONTRIBUTING.md or README.md.

---

## Documentation Tasks

### [ ] 21. Document Settings Singleton Behavior
**Location:** `src/lmn_tools/core/config.py:137-138`

`Path.home()` is evaluated at import time inside the lambda. Cached `_settings` won't reflect `$HOME` changes.

**Tasks:**
- [ ] Document singleton caching behavior in `get_settings()` docstring
- [ ] Note when settings are evaluated
- [ ] Document `reset_settings()` for testing

---

### [ ] 22. Create Architecture Decision Records (ADRs)

Recommended ADRs to document:

- [ ] **ADR-001**: Service Layer Pattern - Template Method via `BaseService`
- [ ] **ADR-002**: CLI-Service-Client Layering - CLI never calls `LMClient` directly
- [ ] **ADR-003**: Response Normalization Contract - where unwrapping happens
- [ ] **ADR-004**: Dataclass vs Pydantic usage guidelines

---

## Summary

| Category | Count | Priority |
|----------|-------|----------|
| Critical | 5 | Must fix before next release |
| Suggestions | 10 | Should fix for maintainability |
| Nitpicks | 5 | Optional improvements |
| Documentation | 2 | Capture decisions |

**Recommended Priority Order:**
1. #5 - Add tests for `LMClient` and HMAC auth (enables safe refactoring)
2. #1 - Standardize client acquisition (quick win)
3. #4 - Fix broad exception in `exists()` (one-line fix)
4. #3 - Split alerts.py (improves navigability)
5. #2 - Move convenience methods to services
6. #14 - Add context manager to LMClient
7. #10 - Add retry logic for rate limits
8. #13 - Add CLI smoke tests
