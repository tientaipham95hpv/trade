# 09 — PHASED IMPLEMENTATION PLAN & GATING MATRIX

## 1. Master Implementation Roadmap

```text
┌──────────────────────────────────────────────────────────────────────────┐
│  PHASE 0: Discovery & Contract Freeze                 [ COMPLETE ]       │
├──────────────────────────────────────────────────────────────────────────┤
│  PHASE 1: Design Foundation (Web & Flutter Tokens)    [ GATED ]          │
├──────────────────────────────────────────────────────────────────────────┤
│  PHASE 2: Web V2 Implementation (Modular & CDN-Free)  [ GATED ]          │
├──────────────────────────────────────────────────────────────────────────┤
│  PHASE 3: Flutter iOS V2 Implementation (Keychain)    [ GATED ]          │
├──────────────────────────────────────────────────────────────────────────┤
│  PHASE 4: Operator Action Integration (CAS RESUME)    [ GATED ]          │
├──────────────────────────────────────────────────────────────────────────┤
│  PHASE 5: Cross-Platform Regression & Acceptance      [ GATED ]          │
├──────────────────────────────────────────────────────────────────────────┤
│  PHASE 6: VPS Deployment & Verification               [ GATED ]          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Detailed Phase Specifications

### Phase 0: Discovery & Contract Freeze (Current Phase — Complete)
- **Objectives**: Map entire architecture, inventory active routes, identify dead code and obsolete features, hash and freeze execution core, produce formal baseline reports.
- **Outputs**: `audit/ui_v2/phase0/00_CURRENT_ARCHITECTURE.md` through `09_IMPLEMENTATION_PLAN.md`.
- **Hard Gate Verification**:
  - `core/execution/*` planned modifications = **0**
  - Binance credential UI planned = **0**
  - Direct Binance API from UI = **0**
  - Copy-trade enablement = **0**
  - Manual arbitrary order UI = **0**
  - Fabricated performance metrics = **0**
  - Web & Flutter routes mapped = **100%**
  - Backend contracts mapped = **100%**
  - **Verdict**: **PASS — READY FOR PHASE 1**

---

### Phase 1: Design Foundation (Next Step)
- **Web Deliverables**:
  - Construct `web/static/css/obsidian_quants.css` incorporating the canonical color system, Inter / JetBrains Mono font declarations with tabular figures (`tnum`, `zero`), compact spacing rhythm (2px/4px/8px/12px/16px), 4px default radius, and 1px borders.
  - Bundle local WOFF2 font files in `web/static/fonts/` (Inter and JetBrains Mono).
  - Build shared HTML/CSS component primitives (`TerminalPanel`, `MetricCard`, `TelemetryBadge`, `StatusBadge`, `DenseTable`, `RiskAlert`, `ConfirmDialog`, `EnvironmentBadge`).
  - Zero external CDN dependencies (completely eliminates `cdn.tailwindcss.com` and FontAwesome CDN).
- **Flutter Deliverables**:
  - Implement `lib/theme/quant_colors.dart`, `quant_typography.dart`, and `quant_theme.dart`.
  - Build shared Flutter widget primitives (`QuantPanel`, `QuantMetric`, `QuantStatusBadge`, `QuantSectionHeader`, `QuantRiskBanner`, `QuantEmptyState`, `QuantConfirmSheet`, `EnvironmentBadge`).
- **Phase 1 Hard Gate**:
  - Design tokens strictly match Obsidian Quants specification.
  - Zero business logic changes.
  - Core SHA-256 hash re-verification: 15/15 match, 0 mismatches.

---

### Phase 2: Web V2 Implementation
- **Deliverables**:
  - Rebuild public routes: `/` (institutional landing & telemetry), `/risk-warning`, `/privacy`, `/terms`.
  - Rebuild `/portal/login` with dark minimalist security panel.
  - Rebuild `/portal/dashboard` using the 12-column Bloomberg-density layout and 5 primary views (`OVERVIEW`, `POSITIONS`, `RISK`, `ACTIVITY`, `SYSTEM`).
  - Extract the 5,470-line inline HTML string from `web/app.py` into clean, maintainable, modular templates and static scripts.
  - Remove all obsolete API settings and copy-trade controls from navigation.
- **Phase 2 Hard Gate**:
  - All Web routes functional and authenticated.
  - No external CDN loaded in network inspection.
  - Zero secrets exposed in HTML/JS.
  - Core SHA-256 hash re-verification: 15/15 match, 0 mismatches.

---

### Phase 3: Flutter iOS V2 Implementation
- **Deliverables**:
  - Integrate `flutter_secure_storage` for iOS Keychain token persistence.
  - Implement centralized `ApiService` targeting `https://trader.noza.site` with timeout handling and 401 token revocation.
  - Rebuild navigation to 4 tabs (`TỔNG QUAN`, `VỊ THẾ`, `RỦI RO`, `HỆ THỐNG`).
  - Delete obsolete `ScannerTab` and `AiCopilotTab`.
  - Implement `PositionDetailSheet` for comprehensive lifecycle inspection.
  - Implement controlled lifecycle polling (3–5s positions/risk, 5–10s status/activity; paused on background, resumed on foreground).
  - Eliminate all fallback financial mock values in `models.dart`.
- **Phase 3 Hard Gate**:
  - iOS app builds cleanly without compilation errors or obsolete tab references.
  - Auth token securely stored in Keychain; logout deletes token.
  - Authoritative data only; empty states render gracefully.
  - Core SHA-256 hash re-verification: 15/15 match, 0 mismatches.

---

### Phase 4: Operator Action Integration
- **Deliverables**:
  - Implement generation-bound `RESUME` modal on Web and Flutter:
    - Pre-fetches authoritative state (`global_halt`, `halt_generation`, `halt_reason`, `recovery_required`).
    - Enforces CAS check: submits `RESUME(expected_halt_generation=current_generation)`.
    - Handles stale generation rejection safely with state refresh (no automatic blind retry).
  - Implement confirmed `HALT` modal with explicit operator warning.
  - Implement confirmed single-position close and panic close controls where backend permissions permit.
- **Phase 4 Hard Gate**:
  - HALT / RESUME adhere 100% to Execution Service CAS authority contract.
  - Core SHA-256 hash re-verification: 15/15 match, 0 mismatches.

---

### Phase 5: Cross-Platform Regression & Acceptance
- **Deliverables**:
  - Comprehensive verification of Web and Flutter across all operational scenarios:
    - Normal OFFLINE monitoring
    - Active HALT state
    - Recovery required state
    - Service disconnect / UNKNOWN state
    - Invalid credentials / session expiration
    - Desktop and mobile viewport responsiveness
- **Phase 5 Hard Gate**:
  - All acceptance test cases pass across Web and mobile.
  - Core SHA-256 hash re-verification: 15/15 match, 0 mismatches.

---

### Phase 6: VPS Deployment & Operational Verification
- **Deliverables**:
  - Backup existing `web/` tree on the VPS.
  - Deploy Web V2 templates, static CSS, fonts, and application updates.
  - Restart supervisor service (`sudo systemctl restart trader-stack-offline.service`).
  - Verify public contracts:
    - `https://trader.noza.site/` → HTTP 200
    - `https://trader.noza.site/health` → HTTP 200
    - `https://trader.noza.site/ready` → HTTP 200 (`READY`)
    - `https://trader.noza.site/openapi.json` → HTTP 404
  - Execute full operational re-audit against frozen execution core.
- **Phase 6 Hard Gate**:
  - VPS deployment verified live.
  - Zero exchange mutations.
  - Core SHA-256 hash unchanged.
