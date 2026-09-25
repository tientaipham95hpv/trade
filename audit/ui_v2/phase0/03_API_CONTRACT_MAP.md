# 03 — API CONTRACT MAP

## 1. System Telemetry & Status Contract

### `GET /api/status`
- **Authentication**: Required (`verify_auth` — session cookie, `X-Session-Token`, or `Authorization: Bearer <token>`).
- **Backend Authority**: `ExecutionServiceClient.query_status()`, `query_positions()`, `query_pnl()`.
- **Response Format (HTTP 200 when service reachable, HTTP 503 when unreachable)**:
```json
{
  "status": "HEALTHY",                   // "HEALTHY" | "HALTED" | "UNKNOWN"
  "projection_source": "EXECUTION_SERVICE", // "EXECUTION_SERVICE" | "UNKNOWN"
  "is_paused": false,                    // boolean (global_halt indicator)
  "halt_generation": 3,                  // authoritative integer from Execution Service
  "halt_reason": null,                   // string or null
  "balance": null,                       // strictly null in OFFLINE mode (no fake numbers)
  "initial_balance": null,               // strictly null in OFFLINE mode
  "roi_percent": null,                   // strictly null in OFFLINE mode
  "open_positions_count": 0,             // integer count of open positions
  "positions": [],                       // list of authoritative position objects
  "open_positions": [],                  // alias to positions
  "total_unrealized_pnl": null,          // strictly null if uncalculated
  "realized_pnl": 0.0,                   // float from Execution Service pnl_ledger
  "pnl_state": "KNOWN_VALUE",            // "KNOWN_VALUE" | "UNKNOWN"
  "version": "1.0.0",                    // app version string
  "mode": "SIMULATION",                  // "SIMULATION" (dry_run) | "LIVE"
  "trading_mode": "MARKET_ALL",          // configuration mode
  "max_positions": 5,                    // integer
  "leverage": 5,                         // integer
  "margin_type": "CROSSED",              // "ISOLATED" | "CROSSED"
  "risk_percent": 1.5,                   // float
  "health": {                            // Execution Service dimension projections
    "trading": { "state": "HEALTHY", "reason": null },
    "database": { "state": "HEALTHY", "reason": null },
    "reconciliation": { "state": "HEALTHY", "reason": null }
  },
  "local_diagnostics": {
    "label": "LOCAL_SIMULATION_DIAGNOSTIC_NOT_TRADING_AUTHORITY",
    "controller_available": false
  }
}
```

---

## 2. Positions Contract

Positions are authoritatively queried from Execution Service via `/query/positions`.
- In `GET /api/status`, `positions` contains the current active positions dictionary or list.
- **Position Schema**:
```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "entry_price": 63450.0,
  "current_price": 63820.0,
  "quantity": 0.05,
  "margin": 634.5,
  "leverage": 5,
  "unrealized_pnl": 18.5,
  "pnl_percent": 2.91,
  "stop_loss": 62180.0,
  "take_profit": 65980.0,
  "protection_state": "ACTIVE",
  "entry_time": "2026-09-25T13:00:00Z"
}
```
- **Empty State**: `positions: []`. Never render mock trades.

---

## 3. Risk & Circuit Breaker Contract

Execution Service maintains the authoritative risk state via:
- `/query/circuit_breaker` → `{"success": true, "is_active": false, "cooldown_until": 0.0, "state": "HEALTHY"}`
- `/query/risk` → `{"success": true, "capital_reservations": [...], "symbol_reservations": [...]}`

### Application-Layer Recommendation for Risk Page
In `web/app.py`, the Circuit Breaker and safety flags are currently embedded in `/api/status` under `health`.
To power the dedicated **Risk** views on Web V2 and Flutter V2 without touching the frozen execution core:
- Add an application-level route `GET /api/risk` in `web/app.py` that queries `client.query_circuit_breaker()`, `client.query_risk()`, and `client.query_status()`.
- Return a consolidated safety payload:
```json
{
  "success": true,
  "global_halt": false,
  "halt_generation": 3,
  "halt_reason": null,
  "recovery_required": false,
  "resume_allowed": true,
  "circuit_breaker": {
    "is_active": false,
    "state": "HEALTHY",
    "cooldown_until": 0.0,
    "consecutive_losses": 0,
    "daily_loss": 0.0
  },
  "capital_reservations": [],
  "symbol_reservations": []
}
```

---

## 4. HALT / RESUME Contract

The HALT/RESUME lifecycle is strictly deterministic and bound to CAS generations in the Execution Core:

```text
              ┌──────────────────────────────┐
              │           HEALTHY            │
              └──────────────┬───────────────┘
                             │ Operator HALT (sets generation N+1)
                             ▼
              ┌──────────────────────────────┐
              │            HALTED            │
              │   (Generation = N+1)         │
              └──────────────┬───────────────┘
                             │
            ┌────────────────┴────────────────┐
            │                                 │
     CAS Match (N+1)                   CAS Mismatch (Stale generation M != N+1)
            │                                 │
            ▼                                 ▼
   [ RESUME SUCCESS ]               [ RESUME REJECTED ]
   Generation cleared               HALT preserved at N+1
   System -> HEALTHY                Client must refresh state
```

### HALT Contract
- **Endpoint**: `POST /api/pause`
- **Payload**: None required (source defaults to `"web"` or `"operator"`).
- **Behavior**: Calls `client.set_halt(reason="Operator manual pause", source="web")`. Increments `halt_generation`.
- **Response**:
```json
{
  "success": true,
  "is_paused": true,
  "halt_generation": 4,
  "authoritative_state": "HALTED",
  "message": "Execution Service đã xác nhận trạng thái bền vững"
}
```

### RESUME Contract
- **Endpoint**: `POST /api/resume`
- **Authoritative Preconditions**:
  1. System must be in `HALTED` state (`global_halt == true`). If not halted, return informational: `"Hệ thống hiện không ở trạng thái HALT. Không cần RESUME."`
  2. `recovery_required` must be `false`. If recovery is required, RESUME is blocked.
  3. Client MUST provide the expected generation: `expected_halt_generation`.
- **Application-Layer Enhancement**:
  Currently, `_set_durable_web_pause(False)` fetches the generation server-side. To enforce strict client-side CAS verification, `POST /api/resume` should accept an optional/required JSON body:
  ```json
  { "expected_halt_generation": 4 }
  ```
  If the provided generation does not match the active service generation, the command is rejected with HTTP 409: `"Cannot RESUME: generation changed or safety remains active"`.
- **Response**:
```json
{
  "success": true,
  "is_paused": false,
  "halt_generation": null,
  "authoritative_state": "RESUMED",
  "message": "Execution Service đã xác nhận trạng thái bền vững"
}
```

---

## 5. Position Close & Emergency Contracts

### `POST /api/close_position`
- **Params**: Query param `?symbol=BTCUSDT` or JSON body `{"symbol": "BTCUSDT"}`.
- **Backend Dispatch**: `client.close_position(symbol=symbol, reason="Manual operator close", source="web")`.
- **Response**:
```json
{
  "success": true,
  "message": "Đã đóng BTCUSDT qua Execution Service",
  "receipt": "receipt_uuid..."
}
```

### `POST /api/panic_close` / `POST /api/close_all_positions`
- **Payload**: None.
- **Backend Dispatch**: `client.emergency_close_all(reason="Emergency close all", source="web")`.
- **Response**:
```json
{
  "success": true,
  "message": "Đã thực thi panic close qua Execution Service",
  "receipt": "receipt_uuid..."
}
```

---

## 6. Activity & Audit History Contracts

### `GET /api/history`
- **Authentication**: Required (`verify_auth`).
- **Data Source**: SQLite `ClientOrderLog` table via SQLAlchemy ORM.
- **Response Schema**:
```json
{
  "success": true,
  "orders": [
    {
      "id": 101,
      "symbol": "BTCUSDT",
      "action": "CLOSE",
      "side": "SELL",
      "price": 63800.0,
      "quantity": 0.05,
      "status": "FILLED",
      "created_at": "2026-09-25 12:45:00",
      "error_message": "pnl=+18.50"
    }
  ],
  "total_orders": 1,
  "win_rate": 100.0,
  "profit_factor": 99.0
}
```

### `GET /api/logs`
- **Authentication**: Required (`verify_auth`).
- **Response Schema**:
```json
{
  "success": true,
  "lines": [
    "[2026-09-25 13:00:00] [INFO] [ExecutionService] Health check OK",
    "[2026-09-25 13:05:22] [WARN] [CircuitBreaker] Streak check verified"
  ]
}
```

---

## 7. Authentication Contracts

### `POST /api/login` (Admin / Operator Session)
- **Request Body**:
```json
{ "username": "admin", "password": "..." }
```
- **Verification**: Checks `Client` database table for `role == "admin"`, `is_active == True`, and matching bcrypt password hash.
- **Response**:
```json
{
  "success": true,
  "username": "admin",
  "token": "64_char_hex_session_token",
  "message": "Đăng nhập thành công!"
}
```
- **Side Effect**: Sets HttpOnly, Secure cookie `session_token` with 30-day expiry.

### `GET /api/check_auth`
- **Verification**: Validates cookie `session_token` or header `X-Session-Token` against in-memory `_active_sessions` cache and database.
- **Response**: `{"authenticated": true, "username": "admin"}` or `{"authenticated": false}`.

### `POST /api/logout`
- **Behavior**: Invalidates active session from `_active_sessions` and database revoked tokens.
- **Response**: `{"success": true, "message": "Đã đăng xuất thành công!"}`.

---

## 8. Health & Readiness Contracts

### `GET /health` (Public Tunnel Probe)
- **Response**: `{"status": "ok", "service": "trader-web"}` (HTTP 200).

### `GET /ready` (Public Operational Probe)
- **Checks**: Database access + Execution Service loopback reachability + recovery required state + service state (`HEALTHY`/`HALTED`).
- **Response States**:
  - `READY` (HTTP 200): DB connected, Execution Service reachable and `HEALTHY`.
  - `HALTED` (HTTP 200): DB connected, Execution Service reachable and `HALTED` (operational halt, not outage).
  - `RECOVERY_REQUIRED` (HTTP 200): Recovery flag active.
  - `NOT_READY` (HTTP 503): DB unreachable or Execution Service completely unreachable.
