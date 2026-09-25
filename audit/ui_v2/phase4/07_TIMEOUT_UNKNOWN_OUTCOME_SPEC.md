# 07 — TRANSPORT TIMEOUT & UNKNOWN_OUTCOME SPECIFICATION

## 1. Problem Statement

When a client sends an emergency operator command (such as `HALT` or `RESUME`) over a network connection, a socket timeout, drop, or TLS disconnection may occur after the backend accepted or executed the command.
Treating this failure as a negative outcome ("FAILED") or automatically retrying could cause unintended duplicate executions or mask an authoritative state change.

## 2. Specification

Upon transport timeout or unexpected transport termination:
1. The client must NOT assume the command was rejected.
2. The client must throw / enter `UNKNOWN_OUTCOME`:
   - `code: "UNKNOWN_OUTCOME"`
   - `message: "Mất kết nối khi gửi lệnh [ACTION]. Vui lòng kiểm tra trạng thái trước khi thao tác lại."`
3. Single-submit lock is released only after error handling presents the state.
4. The client initiates an out-of-band authoritative telemetry fetch (`fetchStatus()`) to determine whether the generation changed or pause state shifted.

## 3. Implementation Evidence

In `ios-app/lib/ui_v2/services/quant_api_client.dart`:
```dart
} on TimeoutException {
  throw QuantApiException(
    message: 'Lỗi Timeout (UNKNOWN_OUTCOME): Mất kết nối khi gửi lệnh HALT. Vui lòng kiểm tra trạng thái trước khi thao tác lại.',
    code: 'UNKNOWN_OUTCOME',
  );
} catch (e) {
  throw QuantApiException(
    message: 'Lỗi mạng khi gửi lệnh HALT (UNKNOWN_OUTCOME): $e',
    code: 'UNKNOWN_OUTCOME',
  );
}
```

Tested in `ios-app/test/ui_v2_phase4_test.dart`:
- `sendHalt throws UNKNOWN_OUTCOME on transport timeout`: Verified PASS.
