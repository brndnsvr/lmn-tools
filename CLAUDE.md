# lmn-tools

LogicMonitor API client library and CLI tools.

## Project Structure

```
src/lmn_tools/
├── api/          # Low-level API client (LMClient)
├── auth/         # HMAC authentication
├── cli/          # Typer CLI application
│   ├── commands/ # Command modules
│   └── utils/    # CLI utilities
├── core/         # Configuration, exceptions
├── services/     # Service layer (BaseService subclasses)
└── constants.py  # API endpoints, enums
```

## Task Tracking

Tasks are tracked in `.tasks/TASKS.md` using a kanban board.

### Quick Reference

| Action | Location |
|--------|----------|
| View all tasks | `.tasks/TASKS.md` |
| Add new task | Add to **Inbox** section |
| Start work | Move to **Inflight** (max 3) |
| Complete | Move to **Done** |

### Task Format

```markdown
### T-XXX: Task Title
**Labels:** `label1`, `label2`
**Location:** `path/to/file.py:line`

Description...
```

### Labels

- `bug` - Defect or incorrect behavior
- `feature` - New functionality
- `refactor` - Code improvement
- `docs` - Documentation
- `infra` - Testing, CI/CD, tooling
- `breaking` - Breaking changes

## Development

### Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src tests
ruff format src tests
```

### Architecture

- **CLI → Service → Client** layering
- CLI commands should use services, never call LMClient directly
- Services extend `BaseService` for CRUD operations
- Client handles auth, pagination, error normalization

### Conventions

- Type hints on all public functions
- Pydantic for config/external data, dataclasses for internal DTOs
- Use `LMEndpoints` constants for API paths
- Services use template method pattern via `base_path` property

## Commit Messages

Use conventional commits:
- `feat:` new feature
- `fix:` bug fix
- `refactor:` code improvement
- `docs:` documentation
- `test:` test additions
- `chore:` maintenance

## Branch Naming

- `feat/T-XXX-short-description`
- `fix/T-XXX-short-description`
- `refactor/T-XXX-short-description`
