# 05 — OBSOLETE FEATURES & REMOVAL CATALOG

## 1. Overview & Authority Grounding

The Stitch design specification and earlier product iterations contained several concepts that have been formally deprecated, removed, or prohibited under the certified execution core architecture (`OFFLINE EXECUTION CORE ACCEPTED`). 

This catalog documents every obsolete feature, explains the authoritative reason for its exclusion, and defines the exact handling in **Web V2** and **Flutter iOS V2**.

---

## 2. Catalog of Prohibited & Obsolete Features

### 2.1 Binance API Key & Secret Management
- **Original Concept**: "API Setup", "Binance API Key", "Binance API Secret", client AES credential storage, and connection verification buttons.
- **Authoritative Status**: **PERMANENTLY REMOVED**. Application trading credentials were completely eliminated. The Execution Service operates in an isolated environment; the application layer holds zero exchange credentials.
- **Web V2 Action**: Remove `API Setup` / `API Settings` from all navigation menus. Replace route with `/portal/system` ("SYSTEM & SECURITY"), displaying only read-only infrastructure health. The retired endpoint `/portal/api-settings` retains its fail-closed static "Feature disabled" page for backward compatibility.
- **Flutter V2 Action**: Eliminate all API key input forms, credentials dialogs, or secret storage fields.

### 2.2 Copy-Trade System
- **Original Concept**: Multi-client copy trading, leader-follower ratio settings, follower allocation, High-Water Mark profit settlements.
- **Authoritative Status**: **UNAVAILABLE / DISABLED**. All copy-trading endpoints fail closed with HTTP 503 `FEATURE_DISABLED`:
  ```json
  {
    "success": false,
    "ok": false,
    "state": "DISABLED",
    "code": "FEATURE_DISABLED",
    "feature": "client_account_trading"
  }
  ```
- **Web V2 Action**: Remove `Copy Trade` from main navigation. Do not provide buttons to enable or configure copy trading. If mentioned in system telemetry, render explicitly as:
  ```text
  Copy Trading: Unavailable / Not certified
  ```
- **Flutter V2 Action**: Zero copy-trade screens or toggles.

### 2.3 AI Trading & Autonomous Gatekeeper
- **Original Concept**: "Dual AI Copilot", "AI Gatekeeper Pre-Trade Approval", "AI Strategy Synthesizer", interactive AI chat directing trades.
- **Authoritative Status**: **DISABLED / ZERO AUTHORITY**. The AI models in the codebase are uncertified speculative prototypes with zero execution authority.
- **Web V2 Action**: Exclude AI chat popups, mascot commentary bars, and AI gatekeeper checkboxes. If system telemetry mentions AI, state:
  ```text
  AI System: Not enabled / Disabled
  ```
- **Flutter V2 Action**: Delete the obsolete `AiCopilotTab` and related `askAiCopilot` network calls from Flutter navigation.

### 2.4 Arbitrary Manual Order Entry
- **Original Concept**: Binance-style manual BUY/SELL forms allowing operators to enter symbol, side, order type, leverage, and quantity to open arbitrary trades.
- **Authoritative Status**: **PROHIBITED**. The terminal is strictly an **observability and safety control surface**.
- **Web V2 & Flutter V2 Action**: Zero manual order entry widgets. The only permitted actions are safety controls:
  - Generation-bound `RESUME`
  - Explicit confirmed `HALT`
  - Position-specific `CLOSE` (where permitted by backend authority)
  - Emergency `PANIC_CLOSE` (all positions)

### 2.5 Fabricated Track Record & Marketing KPIs
- **Original Concept**: Hardcoded promotional figures in the Stitch document (e.g., "70 trades", "71.4% win rate", "Sharpe 2.92", "Max Drawdown 4.10%").
- **Authoritative Status**: **PROHIBITED**. Fabricating financial metrics violates core verification rules.
- **Web V2 & Flutter V2 Action**: All displayed metrics (Realized PnL, Win Rate, Total Trades) MUST originate from actual database rows (`ClientOrderLog`) or Execution Service ledger (`pnl_ledger`). If no data exists, display:
  ```text
  — (or "Chưa có dữ liệu")
  ```

### 2.6 Strategy / 3-Stage Take-Profit Modification
- **Original Concept**: Modifying TP stages, setting custom trailing triggers, or dynamically reprogramming strategy execution from the frontend.
- **Authoritative Status**: **PROHIBITED**. The execution core manages position lifecycle and protection deterministically. UI cannot mutate execution strategy parameters.
- **Web V2 & Flutter V2 Action**: Display existing SL/TP levels as read-only telemetry from backend truth.

### 2.7 Environment Mode Toggle from UI
- **Original Concept**: Buttons allowing users to toggle between OFFLINE, TESTNET, and LIVE.
- **Authoritative Status**: **PROHIBITED**. Runtime environment is controlled exclusively by deployment supervisor configuration (`scripts/provision_trader_runtime.py` and `trader-stack.env`).
- **Web V2 & Flutter V2 Action**: The UI displays the authoritative environment mode prominently as a read-only pill (`OFFLINE` in cyan `#00F0FF`). No controls exist to alter it.

---

## 3. Removal Verification Gate

| Prohibited Feature | Planned UI Element | Verification Status |
| :--- | :---: | :--- |
| Binance API Key inputs | **0** | PASS — Replaced by System & Security |
| Binance Secret inputs | **0** | PASS — Zero secret storage |
| Copy-Trade enablement | **0** | PASS — Explicitly marked Disabled |
| AI Gatekeeper authority | **0** | PASS — Zero authority |
| Manual BUY/SELL forms | **0** | PASS — Observability only |
| Fabricated KPI numbers | **0** | PASS — Backend truth only |
| Environment switcher | **0** | PASS — Read-only telemetry |
