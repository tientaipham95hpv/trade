# 12 — PHASE 5 HANDOFF SPECIFICATION

## 1. Readiness State

Phase 4 is complete and fully certified:
- Core integrity: 15/15 match
- Python test suite: 337/337 pass
- Flutter test suite: 48/48 pass
- Flutter static analysis: Clean (0 issues)
- Operator mutation actions: Safely integrated with CAS generation matching and RBAC

## 2. Handoff to Phase 5: Production Staging & VPS Cutover

Phase 5 will cover:
1. End-to-end integration testing of Web V2 and Flutter V2 against offline execution service supervisor.
2. Production bundle packaging for Web V2 static assets and templates.
3. VPS pre-flight validation: hash checking, supervisor status, readiness probe.
4. Coordinated cutover of `trader-stack-offline.service` to serve Web V2 on `https://trader.noza.site`.
5. Post-cutover smoke verification.

## 3. Mandatory Guardrails for Phase 5

1. Execution core (`core/execution/*`) remains permanently frozen.
2. CLOSEALL remains strictly unavailable until certified in a subsequent dedicated risk milestone.
3. Environment must accurately report `OFFLINE` during offline staging cutover.
4. Telegram notifications for HALT and RESUME events must continue functioning seamlessly.
