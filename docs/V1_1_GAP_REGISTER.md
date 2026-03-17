# V1.1 Gap Register

## Status
- Date: 2026-03-17
- Stage: A0 (in progress)
- Purpose: capture concrete quality gaps before implementation

## Classification model
1. Determined correctly
2. Missed
3. Convenient but inaccurate
4. Validator should have warned but was silent

## Gap table

| ID | Class | Area | Observation | Impact | Priority | Candidate fix |
|---|---|---|---|---|---|---|
| G-001 | missed | tests_map | Not filled yet | TBD | TBD | TBD |

## Initial seed topics (approved scope)
- tests layout + canonical post-change command
- ci pipeline map (trigger -> jobs -> critical steps)
- critical file map (risk/hot paths)
- module dependency map
- hypothesis-based unknown flow (confirm/edit/reject)

## Acceptance rule for A0
- At least top-10 P0/P1 gaps recorded with owner-approved priorities.
