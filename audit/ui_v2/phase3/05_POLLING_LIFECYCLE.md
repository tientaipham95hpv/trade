# 05 — POLLING LIFECYCLE & CONCURRENCY CONTROL

## 1. Cadence Specification

The `PollingController` manages independent periodic timers for distinct data domains:

| Domain | Endpoint | Frequency | Fail-Safe Behavior |
|---|---|---|---|
| System Status & Positions | `/api/status` | **4 seconds** | Fallback to `SystemStatus.unknown()`, retain cached positions |
| Trade History | `/api/history` | **8 seconds** | Retain last known history items |
| Audit Logs | `/api/logs` | **10 seconds** | Retain existing log buffer |

---

## 2. Concurrency Protection (In-Flight Request Lock)

To prevent HTTP request stacking when mobile network latency spikes, `PollingController` implements boolean execution locks:
- `_isStatusUpdating`
- `_isHistoryUpdating`
- `_isLogsUpdating`

If a query is already in flight when a timer fires, the tick is gracefully skipped.

---

## 3. App Lifecycle Observer

`PollingController` registers as a `WidgetsBindingObserver`:

1. **Background Transition** (`AppLifecycleState.paused` or `AppLifecycleState.inactive`):
   - Immediately cancels `_statusTimer`, `_historyTimer`, and `_logsTimer`.
   - Prevents iOS background battery drain and unnecessary network polling.
2. **Foreground Resume** (`AppLifecycleState.resumed`):
   - Restarts periodic timers.
   - Triggers an immediate `refreshAll()` to give the operator an up-to-the-second view of the system.
