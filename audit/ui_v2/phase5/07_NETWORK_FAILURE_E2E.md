# 07 — NETWORK DEGRADATION & FAILURE HANDLING

## 1. Network Failure Taxonomy & Specifications

| Failure Mode | Client Behavior | UI Presentation | State Guarantee |
|---|---|---|---|
| **Timeout during mutation** | Throws `QuantApiException(code: "UNKNOWN_OUTCOME")` | Warning banner: "Lỗi Timeout (UNKNOWN_OUTCOME): Mất kết nối khi gửi lệnh. Vui lòng kiểm tra trạng thái trước khi thao tác lại." | No automatic re-POST. Fails closed. Operator must inspect out-of-band telemetry. |
| **Connection Refused / Network Drop** | Throws network exception | Displays "Lỗi kết nối mạng", shows last updated timestamp | Retains last known state if available; clearly flags as STALE or DISCONNECTED. |
| **HTTP 503 Service Unavailable** | Catches 503 | Displays "Dịch vụ tạm thời không khả dụng (503)" | Execution Service shown as `UNAVAILABLE` or `UNKNOWN`. Never fakes `HEALTHY`. |
| **Invalid JSON / Malformed Payload** | Catches parse exception | Displays "Phản hồi máy chủ không hợp lệ" | Application does not crash. |
| **Slow Response (> 5s)** | Respects timeout configuration | Spinner with lock prevents user panic click | Request cancelled after timeout deadline, single in-flight lock released safely. |

## 2. Evidence of Implementation

- **Web V2** (`web/static/ui_v2/js/dashboard.js`, `risk.js`):
  - In `fetchJson()`: Wraps fetch with error handling, displays toast on network failure, retains previous state with stale indicator.
  - In `risk.js`: `isActionInFlight` lock is always reset in `finally` block, ensuring UI never becomes permanently frozen.
- **Flutter iOS V2** (`ios-app/lib/ui_v2/services/quant_api_client.dart`):
  - Explicit `TimeoutException` catch block mapping to `UNKNOWN_OUTCOME`.
  - Tested in `ios-app/test/ui_v2_phase4_test.dart::sendHalt throws UNKNOWN_OUTCOME on transport timeout`.
  - Tested in `ios-app/test/ui_v2_phase5_rc_test.dart`.
