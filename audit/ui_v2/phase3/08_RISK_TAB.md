# 08 — RISK TAB & CIRCUIT BREAKER TELEMETRY

## 1. Risk Telemetry Panel

The `RiskTab` presents the authoritative risk status derived from `/api/status`:

- **Circuit Breaker Status**: `ARMED` (healthy) or `TRIPPED` (halted).
- **HALT State Machine**: `NORMAL` vs `HALTED`.
- **Generation Token**: Read-only integer token tracking state transitions.
- **Halt Reason**: Reason string for any active or past breaker trigger.
- **Position Limits**: Open positions vs configured concurrency maximum.

---

## 2. Health Dimensions Breakdown

Presents subsystem operational integrity:
- Execution Service (`HEALTHY` / `HALTED` / `UNKNOWN`)
- Web Gateway (`READY`)
- Telegram Message Worker (`READY`)
- SQLite WAL Persistence (`WAL_ACTIVE`)

---

## 3. Operator Safety Actions (Phase 3 Guard)

In Phase 3, operator mutations are intentionally not wired to execution endpoints:

```text
BẢO VỆ GIAI ĐOẠN 3 (PHASE 3 GUARD)
Các thao tác HALT, RESUME, và CLOSEALL chỉ mở giao diện xác nhận mẫu.
Không kích hoạt lệnh đột biến sàn trong Phase 3.
```

Action buttons (`HALT`, `RESUME`, `CLOSE ALL POSITIONS`) open safe, non-mutating instances of `QuantConfirmSheet` to validate UI UX compliance without firing network mutations. Real authenticated execution mutations are reserved for Phase 4.
