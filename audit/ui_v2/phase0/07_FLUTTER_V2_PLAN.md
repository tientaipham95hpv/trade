# 07 — FLUTTER iOS V2 IMPLEMENTATION PLAN

## 1. Architectural Strategy & Mobile Philosophy

Flutter iOS V2 is built as a **native mobile operator console**:
- **Not a WebView wrapper**: Implements native Flutter widgets optimized for iOS touch ergonomics and high-density performance.
- **Obsidian Quants Visual Language**: Uses identical color tokens (`#051424` background, `#122131` surface, `#1C2E42` border, `#F0B90B` gold, `#00F0FF` cyan, `#0ECB81` green, `#F6465D` red).
- **Tabular Figures**: JetBrains Mono typography with numeric tabular alignments.
- **Origin Target**: Strictly `https://trader.noza.site`. Never connects directly to VPS IP or Binance.
- **Zero Fabricated Values**: Models strictly parse authoritative backend values without fake fallbacks.

---

## 2. Target File Structure (`ios-app/lib/`)

```text
ios-app/lib/
├── main.dart                          # Application entrypoint & dependency injection
├── theme/
│   ├── quant_colors.dart              # Obsidian Quants color palette tokens
│   ├── quant_typography.dart          # Inter and JetBrains Mono text styles
│   └── quant_theme.dart               # Global ThemeData definition
├── models/
│   ├── position.dart                  # Authoritative position model (null-safe)
│   ├── system_status.dart             # Status, health dimensions, and telemetry
│   ├── risk_status.dart               # Circuit breaker, streaks, and safety flags
│   └── activity_event.dart            # Execution order and event log models
├── services/
│   ├── secure_storage_service.dart    # iOS Keychain secure token storage
│   ├── api_service.dart               # Centralized HTTP client with error handling
│   └── polling_coordinator.dart       # Controlled lifecycle polling engine
├── widgets/
│   ├── quant_panel.dart               # Dense card container with subtle border
│   ├── quant_metric.dart              # Key-value metric with tabular formatting
│   ├── quant_status_badge.dart        # Semantic status pill (HEALTHY/HALTED/OFFLINE)
│   ├── quant_section_header.dart      # Clean panel header with action slot
│   ├── quant_risk_banner.dart         # Prominent HALT / recovery warning banner
│   ├── quant_empty_state.dart         # Non-decorative empty placeholder
│   ├── quant_confirm_sheet.dart       # Bottom modal sheet for operator mutations
│   └── environment_badge.dart         # OFFLINE / TESTNET / LIVE mode badge
└── screens/
    ├── login_screen.dart              # Secure institutional login screen
    ├── home_screen.dart               # 4-Tab scaffold with top telemetry bar
    ├── tabs/
    │   ├── overview_tab.dart          # Tab 0: TỔNG QUAN
    │   ├── positions_tab.dart         # Tab 1: VỊ THẾ
    │   ├── risk_tab.dart              # Tab 2: RỦI RO
    │   └── system_tab.dart            # Tab 3: HỆ THỐNG
    └── sheets/
        └── position_detail_sheet.dart # Modal bottom sheet for position inspection
```

---

## 3. Dependency Modernization (`pubspec.yaml`)

```yaml
dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.8
  http: ^1.2.0
  intl: ^0.19.0
  flutter_secure_storage: ^9.2.2       # iOS Keychain secure storage for session token
```

---

## 4. Navigation & Tab Architecture

The bottom navigation bar features exactly four operator tabs:

| Tab Index | Vietnamese Label | English Role | Icon (Default / Active) | Key Content |
| :---: | :--- | :--- | :--- | :--- |
| **0** | **TỔNG QUAN** | Overview | `space_dashboard_outlined` / `space_dashboard` | Top telemetry bar, Realized PnL card, Position count pill, Breaker status, Recent activity list. |
| **1** | **VỊ THẾ** | Positions | `layers_outlined` / `layers` | Active positions cards (Side, Symbol, Qty, Entry, Mark, PnL, SL/TP, Protection badge). Tap opens detail sheet. |
| **2** | **RỦI RO** | Risk & Safety | `shield_outlined` / `shield` | Circuit breaker status, streak losses, daily loss accumulator, cooldown timer, confirmed HALT / generation-bound RESUME controls. |
| **3** | **HỆ THỐNG** | System | `terminal_outlined` / `terminal` | Read-only infrastructure telemetry (Environment, Execution Service, Web, Telegram, IPC, DB, Version, Core certification) and Secure Sign Out. |

---

## 5. Mobile Polling & App Lifecycle Management

Because the server provides no WebSocket endpoint, Flutter utilizes controlled HTTP polling:
1. **Cadence**:
   - Positions & Risk: 3–5 seconds.
   - Status & Activity: 5–10 seconds.
2. **Lifecycle Observer (`WidgetsBindingObserver`)**:
   - `AppLifecycleState.paused` / `inactive`: Immediately cancels polling timers to conserve device battery and eliminate unnecessary VPS requests.
   - `AppLifecycleState.resumed`: Immediately executes a one-shot fetch for all screens and restarts polling timers.
3. **Network Resilience**:
   - Read requests (GET) timeout after 8 seconds and display an offline banner if consecutive failures occur.
   - Mutation requests (POST) require active operator confirmation, have explicit timeouts, and NEVER automatically retry upon failure.
