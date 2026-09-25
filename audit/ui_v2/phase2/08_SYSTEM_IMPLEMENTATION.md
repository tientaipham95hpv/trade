# 08 — SYSTEM & GOVERNANCE VIEW SPECIFICATION

## 1. Architectural Purpose

The System View (`web/static/ui_v2/js/system.js`) completely replaces the legacy "API Settings" screen. Instead of providing credential inputs or mutation switches, it serves as a **read-only governance and runtime architecture disclosure**.

It informs operators and auditors of the active boundaries, process isolation parameters, and feature availability states.

---

## 2. Key Sections

### A. Core Certification & Runtime
- **Execution Core Status**: `OFFLINE EXECUTION CORE ACCEPTED`
- **Core Integrity Checksum**: `15/15 PRESERVED (0 MISMATCH)`
- **Runtime Mode**: `OPERATIONAL_OFFLINE`
- **Venue Mutation Target**: `OFFLINE_MOCK_VENUE (ZERO EXCHANGE CALLS)`
- **Supervisor**: `trader-stack-offline.service`

### B. Authority Boundaries
- **Web IPC Authority**: Bearer Loopback (`127.0.0.1:50051`)
- **Direct Exchange Calls from Web**: `ZERO (PROHIBITED)`
- **Direct DB Trade Mutations**: `ZERO (SERVICE PID ONLY)`
- **Client Credentials**: `REMOVED / NON-EXTRACTABLE`
- **Browser Transport**: `HttpOnly SameSite Cookie`

### C. Feature Governance Matrix
Exposes clear, unequivocal status of all system subsystems:
- **Client Credential Authority**: `REMOVED` (Keys permanently purged; no storage or UI forms).
- **Copy-Trade Engine**: `DISABLED` (Endpoints return `FEATURE_DISABLED` with HTTP 503).
- **AI Copilot**: `NOT ENABLED` (Advisory only; zero order placement authority).
- **Market Scanner**: `DISABLED` (Inactive in offline mode).
- **Binance Testnet**: `DISABLED` (Isolated).
- **Binance Live**: `DISABLED` (Prohibited).
- **Manual Trading**: `PROHIBITED` (Zero BUY/SELL controls).
- **Circuit Breaker**: `ACTIVE` (Loss threshold, consecutive failure, and cooldown triggers armed).

Zero editable input fields or toggle switches exist on this page.
