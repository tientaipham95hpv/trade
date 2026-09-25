# AUDIT REPORT — PHASE 6C: WEB V2 REDESIGN SPECIFICATION

## 1. Architectural Transformation
Web V2 was fundamentally re-architected from a generic card-based layout to a high-density, professional institutional workstation layout inspired by Binance Pro, Linear, and Bloomberg Terminal density.

### Key Architectural Changes:
1. **Master 48px Top Navigation Bar**:
   - Left: Brand Logo + `TRADER` + subtle vertical divider `|` + Environment Badge (`OFFLINE`) + Execution Badge (`HEALTHY`) + HALT Badge (`INACTIVE`).
   - Right: IPC Latency (`18 ms`), live UTC clock, Operator identity (`admin`), and minimal `LOGOUT` button.
2. **Left Navigation Sidebar (210px Fixed Desktop Width)**:
   - 5 Views: `Overview`, `Positions`, `Risk`, `Activity`, `System`.
   - SVG line icons (no filled emojis or glowing buttons).
   - Active state: Subtle cyan left indicator (`border-left: 3px solid var(--accent-cyan)`), raised surface `#171E2B`, brighter text `#E8EDF5`.
   - Footer: Small neutral certification badge: `CORE 15/15 MATCH`.
3. **Overview Information Architecture (3 Horizontal Bands)**:
   - **Band 1 (System Strip - 5 Columns)**:
     - `EXECUTION: HEALTHY`
     - `ENVIRONMENT: OFFLINE`
     - `BREAKER: ARMED`
     - `HALT: INACTIVE`
     - `LATENCY: 18 ms`
   - **Band 2 (Financial Telemetry - 5 Columns)**:
     - `REALIZED PNL: +124.50 USDT` (or `—`)
     - `UNREALIZED PNL: +42.50 USDT` (or `—`)
     - `OPEN POSITIONS: 2 / 3`
     - `DAILY LOSS: $0.00`
     - `LOSS STREAK: 0`
   - **Band 3 (Main Work Area)**:
     - Left 65%: Active Positions Table Preview.
     - Right 35%: Risk & Circuit Breaker Summary.
4. **Positions Page**:
   - Dense table-first presentation (36–40px rows, sticky `#070B12` header, monospace tabular numbers).
   - Columns: `SYMBOL | SIDE | QTY | ENTRY | MARK | PNL | SL | TP | PROTECTION | STATE`.
   - Slide-over detail drawer (380–440px) with 5 structured sections: `Position`, `Pricing`, `PnL`, `Protection`, `Execution Metadata`.
   - Zero mutation controls.
5. **Risk Page**:
   - Header: `RISK STATUS` with compact state indicator.
   - 2-Column Grid:
     - Left: Circuit Breaker, Daily Loss, Consecutive Losses, Cooldown, Max Positions.
     - Right: HALT state, CAS generation, reason, recovery, resume allowed.
   - Actions: Dark red outline `HALT` button, neutral/cyan outline `RESUME` button.
   - Emergency close: Minimal non-interactive muted line `Emergency close: Unavailable in this console`.
6. **Activity Page**:
   - Audit console layout with top filter strip (`ALL`, `INFO`, `WARNING`, `ERROR`, `OPERATOR`, `EXECUTION`).
   - Columns: `TIME | SOURCE | EVENT | DETAIL | STATE`.
7. **System Page**:
   - Grouped concise sections: `Runtime`, `Services`, `Authority`, `Certification`, `Features`, `Build`.
   - Compact neutral block: `CORE CERTIFICATION 15 / 15 verified OFFLINE EXECUTION CORE ACCEPTED`.
