# 03 — DATA AUTHORITY & INTEGRITY SPECIFICATION

## 1. Principles of Data Authority

In an institutional trading architecture, the frontend interface must never act as a primary financial or state authority. The Web V2 Operator Terminal strictly enforces the following principles:

1. **Frontend is a Read-Only Projection**: The frontend formats and renders data; it never computes authoritative financial balances, PnL, or state machine transitions.
2. **Zero Fabricated Values**: Missing or unauthoritative values are rendered as institutional em-dash (`—`); no mock `$1000` balance or fake `78.5%` win-rate defaults are tolerated.
3. **Fail-Closed Stale Indication**: If communication with the Execution Service fails, states transition to `UNKNOWN` or `STALE` rather than silently remaining `HEALTHY`.

---

## 2. Telemetry Field Authority Mapping

| Data Field | Source Endpoint | Backend Authority Source | Fallback / Missing State |
|---|---|---|---|
| **System State** | `GET /api/status` | `ExecutionServiceClient.query_status()` | `UNKNOWN` (HTTP 503) |
| **Global HALT** | `GET /api/status` | `service_status["global_halt"]` | `INACTIVE` / `UNKNOWN` |
| **HALT Generation** | `GET /api/status` | `_halt_generation_from(service_status)` | `—` |
| **Active Positions** | `GET /api/status` | `ExecutionServiceClient.query_positions()` | `[]` (Empty state) |
| **Realized PnL** | `GET /api/status` | `ExecutionServiceClient.query_pnl()` | `—` (`pnl_state: UNKNOWN`) |
| **Unrealized PnL** | `GET /api/status` | `positions[sym]["unrealized_pnl"]` | `—` |
| **Circuit Breaker** | `GET /api/status` | `service_status["dimensions"]` | `ARMED` / `UNKNOWN` |
| **Execution Logs** | `GET /api/logs` | Logging buffer / execution service receipts | `[]` |
| **Order History** | `GET /api/history` | `ClientOrderLog` table | `[]` |

---

## 3. Performance Metrics Authority Decision

### A. Win Rate, Total Trades, Max Drawdown
- **Source**: `ClientOrderLog` contains client-side order dispatches. However, it does not record authoritative fill-matching, partial execution slippage, corrected fee deductions, or historical outcome reconciliation from the frozen execution core.
- **Decision**: In Web V2, **Win Rate**, **Total Trades**, and **Max Drawdown** are explicitly displayed as `—` with the caption `Authoritative metric unavailable`.
- **Rationale**: Rendering unproven numbers calculated from raw client logs violates financial integrity standards.

### B. Equity Curve
- **Decision**: No fabricated or interpolated equity curve chart is rendered.
- **Display**: The terminal displays:
  `Chưa có dữ liệu equity được xác nhận.`
- **Rationale**: Displaying an artificially generated upward-sloping equity line creates false confidence and breaches regulatory transparency guidelines.

---

## 4. Reusing `/api/status` vs Adding `/api/risk`

- **Analysis**: Inspection of `/api/status` confirmed that it already projects:
  - System status (`HEALTHY`, `HALTED`, `UNKNOWN`)
  - Global HALT state & generation token
  - Authoritative open positions from the Execution Service
  - Realized PnL from the Execution Service
  - Circuit breaker dimensions (`health`: daily loss, consecutive losses, cooldown)
- **Decision**: **REUSE `/api/status`**. A separate `/api/risk` endpoint is unnecessary, redundant, and would add superfluous IPC traffic between FastAPI and the Execution Service.
