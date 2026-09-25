# Trader Stack

Deterministic Binance Futures execution core with an authenticated loopback Execution Service, private FastAPI dashboard origin, and optional Telegram operator worker.

The approved execution mode is **OFFLINE only**. Scanner and strategy loops remain disabled. Telegram may be explicitly enabled as a standalone IPC-backed worker; it does not enable Binance Testnet or LIVE trading.

## Certified Boundary

- Execution Service: `127.0.0.1:50051`
- Web origin: `127.0.0.1:8088`
- Public ingress: Nginx or a private Cloudflare route to the web origin
- Environment: `TRADER_ENVIRONMENT=OFFLINE`, `DRY_RUN=True`, `USE_TESTNET=False`
- Copy trade: `COPYTRADE_ENABLED=False`
- Mutation authority: Execution Service only
- Web, Telegram, and operator tools use unique principal-specific IPC credentials
- Runtime secrets and databases live under ignored, restricted `.runtime/`

Do not expose ports `50051` or `8088` directly. Do not provision Binance credentials for this OFFLINE deployment.

## Requirements

- Python 3.10+
- Virtual environment at `venv`
- Packages from `requirements.txt`
- Windows PowerShell 5.1+ for Windows deployment, or systemd for Linux

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Canonical Windows Flow

```powershell
.\scripts\start_trader_stack.ps1
```

The startup flow:

1. Provisions `.runtime/trader-stack.env` without printing secrets.
2. Restricts `.runtime` ACLs to the operator and `SYSTEM`.
3. Backs up `data/copytrade.db`.
4. Quarantines retired credential fingerprints and any legacy adjacent Fernet key.
5. Creates one explicit administrator when required.
6. Starts Execution Service and waits for authenticated readiness.
7. Starts web and waits for `/health` and `/ready`.
8. Starts Telegram only when `TELEGRAM_ENABLED=True`, then waits for `.runtime/telegram.ready.json`.

Operational commands:

```powershell
.\scripts\status_trader_stack.ps1
.\scripts\stop_trader_stack.ps1
python -B .\scripts\operator_cli.py status
python -B .\scripts\operator_cli.py halt
python -B .\scripts\operator_cli.py resume
```

The operator CLI imports no exchange SDK and supports only authenticated `status`, `halt`, and generation-bound `resume`.

## Supervision

Install the Windows startup task after local validation:

```powershell
.\deploy\windows\install_trader_stack_task.ps1 -StartNow
```

Remove it with:

```powershell
.\deploy\windows\uninstall_trader_stack_task.ps1
```

The supervisor starts dependencies in this order:

1. Execution Service
2. authenticated service readiness
3. web origin and readiness
4. optional Telegram worker readiness

If Execution Service exits, the supervisor stops Telegram and web, retries through the stale leader-lease interval, restores the service, then restores web and Telegram. Graceful shutdown order is Telegram, web, then Execution Service.

## Health Contracts

- `GET /health`: sanitized web-process liveness
- `GET /ready`: database and Execution Service dependency state
- States: `READY`, `HALTED`, `RECOVERY_REQUIRED`, `NOT_READY`
- A reachable `HALTED` service is reported as `HALTED`, not unavailable

```powershell
Invoke-RestMethod http://127.0.0.1:8088/health
Invoke-RestMethod http://127.0.0.1:8088/ready
```

## Authentication And CORS

- No packaged default administrator password exists.
- Bootstrap credentials remain only in the restricted runtime file.
- Desktop/mobile session tokens are memory-only.
- Production CORS permits explicit configured origins only.
- Wildcard CORS is rejected at startup.
- Telegram accepts commands only from configured sender/chat bindings and authenticates to Execution Service as `telegram-client`.

## Environment Isolation

The canonical stack rejects:

- missing or non-OFFLINE `TRADER_ENVIRONMENT`
- `DRY_RUN=False`
- `USE_TESTNET=True`
- enabled copy-trade execution
- Binance API credentials
- non-loopback Execution Service binding
- weak, missing, or duplicate IPC secrets

`MARKET_DATA_ENVIRONMENT` independently selects credential-free public market data (`PRODUCTION` or `TESTNET`). It never grants account or mutation authority.

TESTNET and LIVE are not enabled or certified by this deployment.

## Logs And Data

- Supervisor: `.runtime/logs/supervisor.out.log`
- Execution Service: `.runtime/logs/execution-service.log`
- Web: `.runtime/logs/web.log`
- Optional Telegram: `.runtime/logs/telegram.log`
- PIDs: `.runtime/pids/`
- Telegram readiness: `.runtime/telegram.ready.json`
- Execution state: `.runtime/execution_state.db`
- Copy-trade database: `data/copytrade.db`
- Migration backups: `.runtime/backups/`
- Revoked fingerprints: `.runtime/credential-quarantine.db`

Never copy secret values into logs, tickets, or audit evidence.

## Linux Deployment

`deploy/setup_vps.sh` installs `trader-stack-offline.service` and does not open ports `8088` or `50051`. The checked-in `deploy/binance-bot.service` is a `/opt/trader-stack` template. Configure Nginx or a private tunnel to proxy the public hostname to `127.0.0.1:8088`.

## Verification

```powershell
python -B -m pytest -q -p no:cacheprovider tests\deployment\test_deployment_remediation.py
python -B -m pytest -q -p no:cacheprovider audit\round11_codex_remediation tests\test_system.py tests\round11 tests\round12 tests\round12_1
```

The accepted `core/execution/*` files must remain byte-identical to `audit/deployment_remediation/evidence/core_baseline.json` during deployment work.
