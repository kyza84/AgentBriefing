# ARCHITECTURE

## 1) Product architecture overview

This repository designs an Operating-Pack Platform with two core modes:
- Initial Build (one-time generation)
- Continuous Maintenance (ongoing freshness)

V3 adds governance controls on top of those two.

## 2) Core system layers

### 2.1 Discovery layer (Repository Scanner)
- Input:
  - file tree
  - manifests/configs
  - scripts/tests/infra files
  - existing docs
- Output:
  - Project Fact Model
  - unknown zones
  - confidence score

### 2.2 Human policy layer (Adaptive Questionnaire)
- Input:
  - unknown zones from scanner
  - policy templates
- Output:
  - Policy/Workflow Model:
    - agent behavior boundaries
    - handoff protocol preferences
    - context update rules
    - escalation behavior

### 2.3 Composition layer (Operating-Pack Generator)
- Input:
  - Fact Model + Policy Model
- Output:
  - V1 operating-pack artifact set:
    - project architecture
    - project state
    - first-message instructions
    - handoff protocol
    - behavior rules
    - context update policy
    - task tracking protocol
    - manifest
    - validation report

### 2.4 Quality layer (Validator)
- Input:
  - generated pack + source models
- Checks:
  - completeness
  - consistency
  - operational applicability
- Output:
  - severity-ranked validation report

### 2.5 Freshness layer (V2 Maintainer)
- Input:
  - repository deltas over time
  - dependency/config changes
  - history of pack versions
- Output:
  - drift events
  - patch proposals
  - micro-questionnaires

### 2.6 Governance layer (V3)
- Ownership of sections
- approval workflows
- audit trail
- policy compliance reporting

## 3) Data contracts (logical)
- `FactModel`
- `PolicyModel`
- `OperatingPackManifest`
- `ValidationReport`
- `DriftEvent` (V2+)
- `GovernanceRecord` (V3+)

## 4) V1 non-goals
- No automated continuous drift engine.
- No auto-generated PR merge pipeline.
- No organization-level governance/RBAC.

## 5) Primary references
- `MAIN_PLAN.txt`
- `V1_APPROVAL_PLAN.txt`
