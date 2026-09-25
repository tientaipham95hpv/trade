# 04 — DATA AUTHORITY & API CLIENT

## 1. Gateway Isolation

The mobile application connects exclusively to the certified Application Gateway:

```text
https://trader.noza.site
```

The app does **NOT**:
- Connect directly to the Binance REST or WebSocket API.
- Connect directly to the internal Execution Service (port 50051).
- Connect directly to SQLite database files.
- Store or accept Binance API Key or Secret.

---

## 2. API Surface Contracts

| Endpoint | Method | Purpose | V2 Client Method |
|---|---|---|---|
| `/api/check_auth` | GET | Verify active session token | `QuantApiClient.checkAuth()` |
| `/api/login` | POST | Authenticate operator with username & password | `QuantApiClient.login()` |
| `/api/logout` | POST | Revoke session and clear cookies/tokens | `QuantApiClient.logout()` |
| `/api/status` | GET | Authoritative Execution Service projection | `QuantApiClient.fetchStatus()` |
| `/api/history` | GET | Closed trade history & performance metrics | `QuantApiClient.fetchHistory()` |
| `/api/logs` | GET | Live supervisor and service logs | `QuantApiClient.fetchLogs()` |

---

## 3. Request Header Specification

Every authenticated request carries both session headers:

```http
Accept: application/json
Content-Type: application/json
X-Session-Token: <token>
Authorization: Bearer <token>
```

Timeouts are strictly capped at 8 seconds to prevent mobile thread blocking.
