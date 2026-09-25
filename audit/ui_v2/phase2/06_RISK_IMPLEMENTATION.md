# 06 — RISK VIEW & CIRCUIT BREAKER MONITORING SPECIFICATION

## 1. Safety Monitoring Architecture

The Risk View (`web/static/ui_v2/js/risk.js`) exposes the deterministic protection mechanics of the frozen execution core:

```text
┌──────────────────────────────────────────────────────────────┐
│ [TOP ALERT BANNER] (Rendered only when HALT or Breaker Trip) │
├──────────────────────────────┬───────────────────────────────┤
│ CIRCUIT BREAKER STATUS       │ HALT & RECOVERY MACHINE       │
│ (Daily loss, consec, cool)   │ (Gate, generation, reason)    │
├──────────────────────────────┴───────────────────────────────┤
│ OPERATOR CONTROL GUARDS (Read-only Phase 4 slot notices)     │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Telemetry Cards

### A. Circuit Breaker Telemetry
- **Operational Mode**: `ARMED_MONITORING` (green) or `TRIPPED_FAIL_CLOSED` (red).
- **Daily Loss**: Realtime drawdown vs max daily loss limit.
- **Consecutive Losses**: Current consecutive loss tally vs limit.
- **Cooldown Expiry**: Absolute timestamp when entries may resume, or `CLEAR (NO COOLDOWN)`.
- **Baseline Reference**: Source of daily baseline capital calculation.

### B. HALT & Recovery State Machine
- **Global HALT Gate**: `INACTIVE (PERMITTED)` or `ACTIVE (ENTRY BLOCKED)`.
- **Halt Generation**: Authoritative `#<int>` generation token used for Compare-And-Swap (CAS) validation.
- **Recovery Required**: Flags whether unconfirmed stops or orphaned orders require cleanup before reopening.
- **Resume Pre-condition**: Requires exact CAS generation match from the operator.
- **Fee Conflict**: `CLEAR (NO CONFLICT)`.
- **Equity Authority**: `EXECUTION_SERVICE_ONLY`.

---

## 3. Operator Mutation Policy in Phase 2

In strict adherence to the Phase 2 boundary instructions:
- **No Active Mutation Triggers**: Buttons for `EMERGENCY HALT`, `RESUME`, or `PANIC CLOSE ALL` are **not wired** to API calls.
- **Presentation**: They are displayed in a dedicated `OPERATOR CONTROL GUARDS` panel as disabled, read-only placeholders labeled `[PHASE 4 TARGET]`.
- **Wiring Scheduled**: Full wiring with CAS token validation modals is explicitly scheduled for **UI Phase 4: Operator Action Integration**.
