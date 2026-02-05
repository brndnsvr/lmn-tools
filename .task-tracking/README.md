# Task Tracking System

This directory contains the project's task tracking system using a markdown-based kanban board.

## Files

- `TASKS.md` - Main kanban board with all tasks
- `archive/` - Completed tasks moved here monthly

## Task ID Format

Tasks use the format `T-XXX` where XXX is a zero-padded sequential number:
- `T-001`, `T-002`, ... `T-999`

The **Next ID** is tracked at the bottom of `TASKS.md`.

## Lanes

| Lane | Purpose | WIP Limit |
|------|---------|-----------|
| **Inbox** | New tasks, unsorted | - |
| **Inflight** | Actively being worked on | 3 |
| **Next** | Prioritized, ready to start | 5 |
| **Backlog** | Planned but not prioritized | - |
| **Done** | Completed this cycle | - |

Tasks in **Done** are archived monthly to `archive/YYYY-MM.md`.

## Task Format

```markdown
### T-XXX: Task Title
**Labels:** `label1`, `label2`
**Location:** `path/to/file.py:line` (optional)

Description of what needs to be done.

**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2
```

## Labels

| Label | Meaning |
|-------|---------|
| `bug` | Defect or incorrect behavior |
| `feature` | New functionality |
| `refactor` | Code improvement without behavior change |
| `docs` | Documentation only |
| `infra` | Testing, CI/CD, tooling |
| `breaking` | Introduces breaking changes |

## Workflow

1. **New tasks** go to Inbox
2. **Triage** moves tasks to Backlog with labels
3. **Prioritization** moves tasks to Next
4. **Starting work** moves task to Inflight
5. **Completion** moves task to Done
6. **Monthly** archive Done tasks

## Conventions

- One task per discrete change (can be split if too large)
- Include file locations when relevant
- Link related tasks with "Related: T-XXX"
- Use acceptance criteria for non-trivial tasks
