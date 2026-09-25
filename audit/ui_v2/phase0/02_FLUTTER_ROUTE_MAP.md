# 02 — FLUTTER ROUTE MAP & MOBILE INVENTORY

## 1. Inventory of Flutter Codebase (`ios-app/`)

### Project Hierarchy
```text
ios-app/
├── pubspec.yaml                 # Dependencies and asset definitions
├── lib/
│   ├── main.dart               # App entrypoint (initializes ApiService, loads settings)
│   ├── models/
│   │   └── models.dart         # Data transfer models (Position, BotStatus, OrderIntent, etc.)
│   ├── services/
│   │   └── api_service.dart    # Network communication with backend API
│   └── screens/
│       ├── home_screen.dart    # Tab controller & top AppBar
│       ├── dashboard_tab.dart  # Tab 0: Overview & quick metrics
│       ├── positions_tab.dart  # Tab 1: Positions list
│       ├── scanner_tab.dart    # Tab 2: Market scanner (OBSOLETE)
│       ├── history_tab.dart    # Tab 3: Trade history & logs
│       ├── ai_copilot_tab.dart # Tab 4: AI Copilot chat (OBSOLETE)
│       └── settings_dialog.dart# Server URL & settings modal
└── ios/                        # Native iOS Runner project
```

### Dependencies in `pubspec.yaml`
```yaml
dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.8
  http: ^1.2.0
  shared_preferences: ^2.2.2
  intl: ^0.19.0
```

---

## 2. Analysis of Current Flutter Implementation (V1 Deficiencies)

### 2.1 Insecure Authentication Storage
- Currently uses `shared_preferences` (`server_url` stored in plaintext; `auth_token` kept only in volatile memory and removed from preferences).
- Once the app process is terminated, the user must re-enter credentials or falls into an unauthenticated state without persistent secure credentials.
- **Requirement 33**: Auth tokens must be securely stored in the iOS **Keychain** using an established secure storage plugin (such as `flutter_secure_storage`). Plaintext JSON or insecure preferences are prohibited.

### 2.2 Obsolete & Speculative Navigation Tabs
The current `HomeScreen` contains 5 tabs:
1. `DashboardTab`: Displays simulated balance, unrealized PnL, quick action buttons.
2. `PositionsTab`: Displays position cards with emergency close and symbol close.
3. `ScannerTab`: Attempts to poll `/api/radar` (scanner is disabled in OFFLINE mode).
4. `HistoryTab`: Polls `/api/history`.
5. `AiCopilotTab`: Communicates with `/api/ai_chat` (AI is disabled and has zero trading authority).

### 2.3 Fabricated Metric Fallbacks in `models.dart`
- In `BotStatus.fromJson(json)`:
  ```dart
  balance: safeParseDouble(json['balance'], 1000.0),
  ```
  When the backend returns `null` for balance (because OFFLINE mode does not query real Binance balances), Flutter defaults to `$1000.00`.
- **Requirement 9.5 & 36**: Strictly prohibits fabricated performance or fallback financial metrics. If data is `null` or unavailable, the UI must show `—` or `Chưa có dữ liệu`.

### 2.4 Lack of Dedicated Safety / System Surfaces
- No dedicated **Risk** screen exposing the Circuit Breaker, daily loss counter, cooldown timers, or recovery required flags.
- No dedicated **System** screen displaying execution health dimensions, IPC status, and core certification.
- `SettingsDialog` currently allows editing the server URL but lacks institutional system telemetry.

---

## 3. Flutter V2 Navigation & Screen Architecture

The redesigned Flutter iOS V2 operator terminal adopts the canonical Obsidian Quants identity and a focused 4-tab operator model:

```text
┌────────────────────────────────────────────────────────┐
│                   TOP TELEMETRY BAR                    │
│ Binance Quant Pro • [ OFFLINE ] • Execution [ HEALTHY ] │
├────────────────────────────────────────────────────────┤
│                                                        │
│                    ACTIVE TAB VIEW                     │
│                                                        │
├────────────────────────────────────────────────────────┤
│  [ TỔNG QUAN ]    [ VỊ THẾ ]    [ RỦI RO ]    [ HỆ THỐNG ]  │
│  (dashboard)     (layers)      (shield)     (terminal) │
└────────────────────────────────────────────────────────┘
```

### 3.1 Screen Specifications

#### 1. TỔNG QUAN (`OverviewScreen` — Tab 0)
- **Top Bar**: System title, OFFLINE cyan environment badge, Execution Service health badge.
- **Metric Cards**:
  - Net Realized PnL (JetBrains Mono tabular figures, `#0ECB81` / `#F6465D`).
  - Open Positions count badge.
  - Risk / Circuit Breaker quick status.
  - Latency indicator (ping to `trader.noza.site`).
- **Recent Activity**: Last 5 execution and safety events with severity tags (`INFO`, `WARN`, `HALT`).

#### 2. VỊ THẾ (`PositionsScreen` — Tab 1)
- **Position Cards**:
  - Symbol & Side (`LONG` in green `#0ECB81`, `SHORT` in red `#F6465D`).
  - Qty, Entry Price, Mark Price.
  - Unrealized PnL (USDT & %).
  - SL / TP and Protection State (authoritative from backend truth).
- **Position Detail Sheet**: Modal bottom sheet on tap:
  - Lifecycle state and entry timestamp.
  - Margin & leverage.
  - Protective order IDs and reconciliation status.
  - Safe close action (requires explicit confirmation dialog).

#### 3. RỦI RO (`RiskScreen` — Tab 2)
- **Safety Status Overview**:
  - Global HALT state (Active / Inactive).
  - Current HALT Generation (authoritative integer).
  - HALT Reason (sanitized backend string).
  - Recovery Required indicator (`CLEAR` or `RECOVERY_REQUIRED`).
- **Breaker Telemetry**:
  - Consecutive losses counter.
  - Daily loss accumulator vs limit.
  - Cooldown timer countdown.
- **Operator Actions**:
  - **HALT Button**: Stops new trading activity; requires confirmation dialog.
  - **RESUME Button**: Only visible/enabled when `global_halt == true` AND `resume_allowed == true`. Submits `RESUME(expected_halt_generation=current_generation)`. Stale generation rejection handled with automatic state refresh.

#### 4. HỆ THỐNG (`SystemScreen` — Tab 3)
- **System Telemetry Grid**:
  - Environment: `OFFLINE` (cyan badge).
  - Execution Service: `HEALTHY` (green badge).
  - Web Application: `READY` (green badge).
  - Telegram Bot: `READY` (green badge).
  - IPC Connection: Loopback `127.0.0.1:50051`.
  - Database Access: `OK`.
  - Client Trading: `DISABLED`.
  - Copy-Trade: `DISABLED`.
  - AI System: `NOT ENABLED`.
  - Core Certification: `OFFLINE EXECUTION CORE ACCEPTED`.
  - App Version & Build number.
- **Session Controls**:
  - Secure Logout button (clears Keychain token and navigates to Login).

#### 5. ĐĂNG NHẬP (`LoginScreen` — Modal / Route)
- Dark minimal security panel.
- Username and password fields.
- Keychain persistence for session token upon successful authentication.
- Centralized error notification on invalid credentials.

---

## 4. Flutter Networking & Polling Lifecycle

- **Origin URL**: Strictly `https://trader.noza.site`. Direct VPS IPs and exchange URLs are strictly prohibited.
- **Centralized Client**: Single HTTP client handling headers (`X-Session-Token`, `Authorization: Bearer <token>`), 8-second timeouts, and automatic 401 token invalidation.
- **Controlled Polling Strategy**:
  - Positions & Risk: 3–5 seconds.
  - Status & System: 5–10 seconds.
  - Activity / Logs: 5–10 seconds.
- **Lifecycle Management**:
  - Automatically pause polling when application enters background (`AppLifecycleState.paused` / `inactive`).
  - Resume polling immediately upon returning to foreground (`AppLifecycleState.resumed`).
- **No Uncontrolled Mutation Retries**: Read queries (GET) may safely retry on transient network errors; mutations (POST HALT/RESUME/Close) MUST NOT automatically retry without fresh authoritative confirmation.
