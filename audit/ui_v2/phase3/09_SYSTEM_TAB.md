# 09 — SYSTEM & GOVERNANCE TAB

## 1. Architecture Governance Matrix

The `SystemTab` displays the operational baseline and hard rules of the system:

| Architectural Surface | Baseline Status | Visual Indication |
|---|---|---|
| Chứng chỉ API giao dịch sàn | `REMOVED (0 credentials)` | Text Secondary |
| ClientApiCredential Model | `REMOVED` | Text Secondary |
| Tính năng Copy-Trade | `DISABLED` | Text Muted |
| Tính năng AI Copilot | `NOT ENABLED` | Text Muted |
| Máy quét tín hiệu (Scanner) | `DISABLED` | Text Muted |
| Môi trường Testnet / Live | `DISABLED` | Gold Accent |
| Đặt lệnh thủ công (Manual Buy/Sell) | `PROHIBITED` | Red Accent |

---

## 2. Core Execution Certification

- **Status**: `OFFLINE EXECUTION CORE ACCEPTED`
- **Integrity**: `15/15 PRESERVED (0 MISMATCH)`
- **Protected Core Path**: `core/execution/*`
- **Supervisor Service**: `trader-stack-offline.service`
- **Database Engine**: `SQLite WAL Active`

---

## 3. Live System Logs Viewer

- Feeds live audit log lines from `/api/logs` via `PollingController`.
- 220px fixed monospaced terminal window with manual refresh button.
- Color-coded log lines: `ERROR` / `CRITICAL` / `HALT` in red, `WARN` in gold, standard info in secondary text.

---

## 4. Operator Session & Logout

- Shows current operator account (`admin`).
- Shows credentials backing: `iOS Keychain (Bảo mật)`.
- Dedicated logout button opens a confirmation dialog, revokes server-side session via `/api/logout`, clears the Keychain token, and redirects immediately to `LoginScreen`.
