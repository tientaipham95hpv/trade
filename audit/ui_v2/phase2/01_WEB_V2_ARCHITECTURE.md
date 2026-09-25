# 01 — WEB V2 ARCHITECTURE & ASSET PIPELINE

## 1. Architectural Model

Web V2 rejects monolithic inline HTML and sprawling multi-thousand-line script templates in favor of a clean, modular server-rendered template architecture paired with modular client-side ES modules:

```text
web/
├── app.py                       # FastAPI application & route controllers
├── view_models.py               # Sanitized, read-only UI presentation builder
├── templates/
│   └── ui_v2/
│       ├── base.html            # Master HTML5 document shell (zero runtime CDN)
│       ├── dashboard.html       # Terminal layout & script hydrator
│       ├── landing.html         # Institutional landing page
│       ├── login.html           # Obsidian Quants login screen
│       ├── risk_warning.html    # Derivatives risk warning
│       ├── privacy.html         # Privacy policy
│       ├── terms.html           # Terms of service
│       └── partials/
│           ├── telemetry_bar.html # Realtime top status bar
│           └── navigation.html    # 5-tab terminal navigation
└── static/
    └── ui_v2/
        ├── tokens.css           # Obsidian Quants design tokens
        ├── base.css             # Resets & tabular numeric settings
        ├── layout.css           # 12-column Bloomberg-density layout
        ├── components.css       # 13 reusable terminal primitives
        ├── responsive.css       # Breakpoints (>=1440, 1024-1439, <1024, <640)
        ├── obsidian_quants.css  # Bundle stylesheet
        └── js/
            ├── formatters.js    # Data, PnL, latency, currency formatters
            ├── api.js           # Authenticated fetch client (with latency tracking)
            ├── state.js         # Reactive terminal state container
            ├── polling.js       # Background polling with visibility awareness
            ├── overview.js      # Overview tab renderer
            ├── positions.js     # Positions grid & detail drawer renderer
            ├── risk.js          # Risk & circuit breaker renderer
            ├── activity.js      # Audit log & activity stream renderer
            ├── system.js        # Feature matrix & governance renderer
            └── dashboard.js     # Master coordinator & DOM lifecycle manager
```

---

## 2. Server-Side Rendering vs Client Hydration

1. **Initial Server Paint**:
   - `web/app.py` renders `web/templates/ui_v2/dashboard.html` using Jinja2 with autoescaping enabled.
   - The initial response includes the persistent Top Telemetry Bar, Navigation Bar, and loading skeleton placeholders.
   - This delivers sub-50ms First Contentful Paint (FCP) without waiting for client-side bundle execution.

2. **Client-Side Hydration**:
   - `web/static/ui_v2/js/dashboard.js` boots as an ES6 module.
   - It binds event handlers to navigation links, starts a UTC ticker, and launches `PollingManager`.
   - On the first `/api/status` response, the state store updates and renders the active tab instantly without full page reloads.

---

## 3. Strict Zero-CDN Policy

All styles and scripts are served directly from the local FastAPI application server via `app.mount("/static", ...)`:
- **Fonts**: Local institutional font stack (`JetBrains Mono`, `SF Mono`, `Fira Code`, `Inter`, system sans-serif/monospace).
- **Icons**: Inline SVG icons rendered directly into HTML templates.
- **Charts / Visuals**: Pure CSS tabular bars and indicators; no external chart CDN libraries loaded at runtime.
- **Scripts**: 100% native ES6 modules; zero external JS framework CDNs.

This architecture ensures high security, offline viability, zero layout shift (CLS = 0), and immunity to upstream CDN outages.
