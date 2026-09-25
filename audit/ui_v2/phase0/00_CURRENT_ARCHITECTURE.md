# 00 — CURRENT ARCHITECTURE

## 1. Executive Summary & Canonical Baseline

This document establishes the authoritative operational baseline for the **Binance Quant Pro — Obsidian Quants UI Redesign (Web V2 + Flutter iOS V2)** as of September 25, 2026.

- **Repository Root**: `C:\Users\Administrator\Downloads\project\bot binance`
- **Git HEAD Commit**: `07a69b5022800bb03ce7ba009c08ed9cb8ab2208`
- **Execution Core Status**: `GPT-6 Astra: OFFLINE EXECUTION CORE ACCEPTED`
- **Execution Core Freeze**: `core/execution/*` is strictly frozen (15/15 files verified, 0 mismatches, 0 planned modifications).
- **Current VPS Runtime**: `OPERATIONAL_OFFLINE`
- **Supervisor Service**: `trader-stack-offline.service`
- **Public Domain**: `https://trader.noza.site` (via private Cloudflare Tunnel)

---

## 2. System Architecture & Authority Boundaries

The system strictly enforces process-level isolation and fail-closed authority boundaries:

```text
[ Web V2 (Browser) ]       [ Flutter iOS V2 App ]
        │                            │
        │ HTTPS                      │ HTTPS
        └──────────────┬─────────────┘
                       ▼
         Cloudflare Tunnel (trader.noza.site)
                       ▼
       ┌───────────────────────────────┐
       │   FastAPI Web Application     │
       │   127.0.0.1:8088              │
       │   (run_web.py / web/app.py)   │
       └──────────────┬────────────────┘
                      │
                      │ Authenticated Loopback IPC
                      │ (Bearer IPC_TOKEN_WEB / IPC_TOKEN_OPERATOR)
                      ▼
       ┌───────────────────────────────┐
       │   Authoritative Execution     │
       │   Service (127.0.0.1:50051)   │
       │   (core/execution_service)    │
       └──────────────┬────────────────┘
                      │
                      │ Internal deterministic dispatch
                      ▼
       ┌───────────────────────────────┐
       │   [FROZEN EXECUTION CORE]     │
       │   core/execution/*            │
       │   • State Store (SQLite)      │
       │   • Protection Engine         │
       │   • Risk Ledger & Breaker     │
       │   • Reconciliation Engine     │
       └──────────────┬────────────────┘
                      │
                      │ Venue mutations (Service PID only)
                      ▼
            [ Fake / Mock Venue ]
          (Offline sandbox mode)
```

### Absolute Architecture Rules
1. **Zero Direct Exchange Mutation**: Neither Web nor Flutter ever touches Binance REST/WebSocket directly. All trading intents and lifecycle mutations MUST flow through `ExecutionServiceClient`.
2. **Zero Direct Execution DB Access**: Web and Flutter do not connect to the execution SQLite database directly. Web only queries Execution Service via authenticated loopback IPC (`/query/*`).
3. **Black-Box Execution Core**: `core/execution/*` is treated as an immutable black box. Fencing semantics, CAS generations, and risk outboxes remain authoritative within the core.
4. **Application Trading Credentials Removed**: `ClientApiCredential` is completely decommissioned. The application does not store or accept Binance API keys or secrets.
5. **Fail-Closed Features**:
   - Client account trading: `DISABLED` (returns HTTP 503 `FEATURE_DISABLED`)
   - Copy-trading: `UNAVAILABLE_DISABLED`
   - AI trading / Gatekeeper: `NOT_ENABLED` (zero authority)
   - Testnet / LIVE trading: `DISABLED`

---

## 3. Supervised Processes & Runtime Topology

The VPS runs under `scripts/trader_stack_supervisor.py` managing three distinct processes:

| Component | Entrypoint | Host/Port | Access / Protocol | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Execution Service** | `core.execution_service.service` | `127.0.0.1:50051` | Loopback HTTP + IPC Bearer Token | `HEALTHY` (offline) |
| **Web / Application API** | `run_web.py` (`web/app.py`) | `127.0.0.1:8088` | Loopback HTTP (Ingress via Cloudflare) | `READY` |
| **Telegram Worker** | `notifier/telegram_bot.py` | Standalone worker | Long-polling / IPC to Execution Service | `READY` |

### Verified Public Ingress Contracts
- `GET https://trader.noza.site/` → HTTP 200 (Institutional landing / dashboard)
- `GET https://trader.noza.site/health` → HTTP 200 (`{"status":"ok","service":"trader-web"}`)
- `GET https://trader.noza.site/ready` → HTTP 200 (`{"status":"READY", ...}`)
- `GET https://trader.noza.site/openapi.json` → HTTP 404 (Intentionally disabled in production)

---

## 4. UI V2 Role & Transformation Boundary

The Web and Flutter V2 projects are strictly **observability and operator control surfaces**:
- **Monitoring-First**: Live telemetry, risk posture, open position lifecycle, execution log stream, and system health.
- **Operator Safety Controls**: Generation-bound `RESUME`, explicit confirmed `HALT`, and emergency position close where authorized.
- **No Manual Trading**: No Binance-style BUY/SELL order entry forms.
- **No Fabricated Performance**: Authoritative data only; empty/unavailable states rendered as `—` or `No data`.
- **Obsidian Quants Design**: High-density Technical Minimalist, dark mode, compact layout, Inter + JetBrains Mono typography.
