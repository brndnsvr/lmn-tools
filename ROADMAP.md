# lmn-tools Roadmap

Tracking code quality improvements and technical debt from code reviews.

---

## Critical - Must Fix

### [ ] 1. Missing Test Coverage for Core Modules
**Location:** `tests/`

The API client (`api/client.py`) and authentication (`auth/hmac.py`) have zero unit tests.

**Tasks:**
- [ ] Add tests for `LMClient.request()` with mocked responses
- [ ] Add tests for `LMClient.paginate()` edge cases
- [ ] Add tests for `generate_lmv1_signature()` with known test vectors
- [ ] Add tests for error handling paths (`_handle_response`)

---

### [ ] 2. Credential Exposure Risk in Debug Output
**Location:** `src/lmn_tools/collectors/netconf/client.py:125-126`

The `_debug_print` pattern bypasses structured logging and could expose sensitive data.

**Tasks:**
- [ ] Review all `_debug_print` calls for sensitive data
- [ ] Use structured logging with level controls consistently
- [ ] Consider adding a log filter for sensitive data patterns

---

### [ ] 3. Broad Exception Handler in BaseService.exists()
**Location:** `src/lmn_tools/services/base.py:181-185`

Swallows all exceptions including network errors, auth failures, and rate limits.

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

## Suggestions - Should Fix

### [ ] 4. No Retry Logic for Transient Failures
**Location:** `src/lmn_tools/api/client.py`

The client raises `APIRateLimitError` with `retry_after` but doesn't implement automatic retries.

**Tasks:**
- [ ] Add optional retry with exponential backoff
- [ ] Consider using `tenacity` library or implement simple retry in `request()` method
- [ ] Make retry behavior configurable

---

### [ ] 5. Hardcoded SDT Time Calculation
**Location:** `src/lmn_tools/services/alerts.py:267-270`

Uses local system time which may drift or be in wrong timezone. LM API expects UTC milliseconds.

**Tasks:**
- [ ] Use `datetime.utcnow()` for time calculations
- [ ] Document that all times are UTC
- [ ] Consider adding timezone-aware helpers

---

### [ ] 6. Missing Input Validation in CLI Commands
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

### [ ] 7. Inconsistent Response Unwrapping
**Location:** Multiple service files

Some services manually unwrap `data` wrapper, but `LMClient._handle_response()` already normalizes responses. Creates confusion about where normalization happens.

**Tasks:**
- [ ] Audit all service files for manual response unwrapping
- [ ] Standardize response handling in one place (client)
- [ ] Document the response contract

---

### [ ] 8. Document Settings Singleton Behavior
**Location:** `src/lmn_tools/core/config.py:137-138`

`Path.home()` is evaluated at import time inside the lambda. Cached `_settings` won't reflect `$HOME` changes.

**Tasks:**
- [ ] Document singleton caching behavior
- [ ] Add note about when settings are evaluated

---

### [ ] 9. Missing CLI Test Coverage
**Location:** `tests/`

No tests for CLI commands. 31 command modules have significant logic that could break silently.

**Tasks:**
- [ ] Add smoke tests for critical commands using `typer.testing.CliRunner`
- [ ] Test credential validation paths
- [ ] Test error handling for common failures

**Example:**
```python
from typer.testing import CliRunner
from lmn_tools.cli.main import app

def test_device_list_requires_credentials():
    runner = CliRunner()
    result = runner.invoke(app, ["device", "list"])
    assert "credentials not configured" in result.output
```

---

### [ ] 10. Session Not Closed on Context Exit
**Location:** `src/lmn_tools/api/client.py`

`LMClient` uses `requests.Session()` but doesn't implement context manager protocol.

**Fix:**
```python
def close(self) -> None:
    self._session.close()

def __enter__(self) -> LMClient:
    return self

def __exit__(self, *args) -> None:
    self.close()
```

---

## Nitpicks - Optional

### [ ] 11. Shadow Builtin `filter`
**Location:** `src/lmn_tools/services/base.py:50`, CLI commands

Parameter shadows builtin `filter()`. Consider renaming to `filter_str` or `query`.

---

### [ ] 12. Shadow Builtin `id`
**Location:** `src/lmn_tools/services/base.py:79`

Parameter shadows builtin `id()`. Consider renaming to `resource_id` or `item_id`.

---

### [ ] 13. Type Ignore Without Explanation
**Location:** `src/lmn_tools/cli/utils/client.py:42`

```python
return LMClient.from_credentials(settings.credentials)  # type: ignore
```

**Fix:** Add explanation or use assertion:
```python
assert settings.credentials is not None  # Checked by has_credentials
return LMClient.from_credentials(settings.credentials)
```

---

### [ ] 14. Audit Unused Exports
**Location:** `src/lmn_tools/services/__init__.py`

Check if all exported services are actually used. Some may have been added speculatively.

---

### [ ] 15. Document Dataclass vs Pydantic Convention
**Location:** `src/lmn_tools/auth/hmac.py:24-47`

Mixing dataclasses and pydantic models requires developers to know which to use when.

**Tasks:**
- [ ] Document when to use dataclass vs pydantic
- [ ] Add to contributing guidelines

---

## Summary

| Category | Count | Completed |
|----------|-------|-----------|
| Critical | 3 | 0 |
| Suggestions | 7 | 0 |
| Nitpicks | 5 | 0 |

**Priority Order:**
1. Add tests for `LMClient` and HMAC auth (#1)
2. Fix broad exception handling in `BaseService.exists()` (#3)
3. Add CLI smoke tests (#9)
4. Implement retry logic for rate limits (#4)
5. Add context manager to LMClient (#10)

---

## Completed

_Items will be moved here when done._
