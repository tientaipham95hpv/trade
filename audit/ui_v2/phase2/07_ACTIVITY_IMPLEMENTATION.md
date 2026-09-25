# 07 — ACTIVITY VIEW & AUDIT STREAM SPECIFICATION

## 1. Event Sources & Processing

The Activity View (`web/static/ui_v2/js/activity.js`) aggregates two backend telemetry streams:
1. `GET /api/history`: Order lifecycle events, executions, and fills.
2. `GET /api/logs?limit=50`: Operational system and execution service logs.

These sources are normalized, merged, and sorted chronologically in descending order.

---

## 2. Table Presentation

Columns:
- `TIME (UTC)`: ISO timestamp formatted via `Formatters.timestamp()`.
- `COMPONENT`: Subsystem tag (`ORDER_LIFECYCLE`, `PROTECTION_ENGINE`, `CIRCUIT_BREAKER`, `SYSTEM_LOG`).
- `SEVERITY`: Semantic color tags (`INFO` in cyan/white, `WARN` in gold, `ERROR` in red).
- `SYMBOL`: Relevant asset symbol or `SYSTEM`.
- `ACTION`: Dispatch action or lifecycle state change.
- `RESULT / DETAILS`: Execution receipt or summary text.

---

## 3. Strict Content Sanitization

Before any log message or event detail is rendered into the DOM, it passes through `Formatters.sanitize()` and `Formatters.escapeHtml()`.

The sanitization engine actively scrubs:
- **Bearer Tokens**: `Bearer [REDACTED]`
- **Session Tokens**: `token=[REDACTED]`
- **API Keys**: `api_key=[REDACTED]`
- **Secrets**: `secret=[REDACTED]`
- **Passwords**: `password=[REDACTED]`
- **HTML Entities**: `&`, `<`, `>`, `"`, `'` are escaped to prevent Cross-Site Scripting (XSS).

Zero credentials, tokens, or raw authorization headers can ever appear in the Activity stream.
