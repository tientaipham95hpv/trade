# AUDIT REPORT — PHASE 6B: PREDEPLOY VPS BASELINE SNAPSHOT

## 1. Authoritative VPS Host Metadata
- **Host IP**: `185.185.80.197`
- **Hostname**: `vmi3562926`
- **Target Deployment Directory**: `/opt/trader-stack`
- **Service Name**: `trader-stack-offline.service`
- **Service User**: `trader`
- **Capture Timestamp**: `2026-09-25T16:57:21Z`

## 2. Predeploy Supervisor Telemetry
- **ActiveState**: `active`
- **SubState**: `running`
- **MainPID**: `3819981`
- **NRestarts**: `0`
- **Managed Children**:
  - `3820002`: Execution Service (`127.0.0.1:50051`, `--dry-run`)
  - `3820011`: Web Origin (`127.0.0.1:8088`, `run_web.py`)
  - `3820232`: Telegram Worker (`scripts/telegram_worker.py`)

## 3. Predeploy Network State
- `127.0.0.1:50051`: Execution Service (LISTEN)
- `127.0.0.1:8088`: Web Origin (LISTEN)
- `0.0.0.0:50051`: Absent
- `0.0.0.0:8088`: Absent

## 4. Predeploy Core Execution Verification
15 of 15 certified execution files under `/opt/trader-stack/core/execution/*` verified matching authorized hash baseline (15/15 MATCH, 0 mismatch).

## 5. Predeploy Public Web Baseline
- `https://trader.noza.site/`: HTTP 200
- `https://trader.noza.site/health`: HTTP 200
- `https://trader.noza.site/ready`: HTTP 200 (`{"status":"READY","service":"trader-web","web_process":"UP","execution_service_reachable":true,"database_access":true,"execution_service_state":"HEALTHY"}`)
