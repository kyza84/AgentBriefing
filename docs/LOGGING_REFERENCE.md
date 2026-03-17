# LOGGING_REFERENCE

## Purpose
Unified reference for evidence and decision logging in this planning repository.

## 1) Primary evidence locations

- Strategic baseline:
  - `MAIN_PLAN.txt`
- V1 execution contract:
  - `V1_APPROVAL_PLAN.txt`
- Current state:
  - `docs/PROJECT_STATE.md`
- Phase and task progression:
  - `docs/MASTER_PLAN_TRACKER.md`
- Next-session handoff:
  - `docs/NEXT_CHAT_CONTEXT.md`

## 2) Recommended decision log channels

- Major scope decision:
  - record in `docs/PROJECT_STATE.md` and `docs/MASTER_PLAN_TRACKER.md`
- Phase/task status change:
  - record in `docs/MASTER_PLAN_TRACKER.md`
- Session handoff update:
  - record in `docs/NEXT_CHAT_CONTEXT.md`
- Rule/protocol change:
  - update corresponding rule file in `docs/`

## 3) Event types (logical taxonomy)

- `scope_change`
- `phase_status_change`
- `risk_update`
- `validation_policy_update`
- `handoff_update`
- `operator_protocol_update`

## 4) Optional structured logging format (future)

If structured logs are introduced, use JSONL with this minimal schema:

```json
{
  "ts_utc": "2026-03-17T10:30:00Z",
  "event_type": "scope_change",
  "phase": "A",
  "summary": "Confirmed V1 out-of-scope boundaries",
  "evidence_paths": ["V1_APPROVAL_PLAN.txt", "docs/MASTER_PLAN_TRACKER.md"],
  "author": "owner_or_agent"
}
```

## 5) Logging quality rules
- Every major decision must have:
  - what changed,
  - why it changed,
  - impact on current phase,
  - evidence path.
- No critical decision should exist only in chat transcript.
