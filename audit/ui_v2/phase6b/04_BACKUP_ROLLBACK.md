# AUDIT REPORT — PHASE 6B: PREDEPLOY BACKUP & ROLLBACK READINESS

## 1. Backup Execution & Location
Prior to any file modifications or package extraction on the VPS, a complete archive of all production files was created:
- **Timestamp**: `2026-09-25T16:59:54Z`
- **Backup Directory**: `/root/deploy-backups/ui-v2-phase6b-20260925T165954Z/`
- **Compressed Archive**: `/root/deploy-backups/ui-v2-phase6b-20260925T165954Z.tar.gz`
- **Archive Size**: `3.5 MB` (38 files)
- **Archive SHA-256 Digest**: `c701227c32a187c92e2853518ea68ed1a4a3d265025b8af345c356800d4647c9`

## 2. Content Inventory
The backup captured:
- Full `web/` directory (FastAPI application, view models, legacy templates, static assets).
- Full `config/` directory.
- Authoritative runtime environment: `/opt/trader-stack/.runtime/trader-stack.env`.

## 3. Verified Rollback Procedures

### 3.1 Fast-Path Feature Flag Rollback:
If an operational regression occurs solely in Web V2 presentation:
```bash
sed -i 's/^UI_V2_ENABLED=.*/UI_V2_ENABLED=false/' /opt/trader-stack/.runtime/trader-stack.env
systemctl restart trader-stack-offline.service
```
This instantly reverts all public routes (`/`, `/portal/dashboard`, `/portal/login`) to the certified legacy dashboard without file mutations.

### 3.2 Full File Rollback:
To restore the pre-deploy binary and source state:
```bash
cp -a /root/deploy-backups/ui-v2-phase6b-20260925T165954Z/web/* /opt/trader-stack/web/
cp -a /root/deploy-backups/ui-v2-phase6b-20260925T165954Z/trader-stack.env /opt/trader-stack/.runtime/trader-stack.env
chown -R trader:trader /opt/trader-stack/web /opt/trader-stack/.runtime/trader-stack.env
systemctl restart trader-stack-offline.service
```

## 4. Verification Check
- Backup directory is confirmed readable, non-empty, and archived outside the public web root.
- The compressed tarball hash has been permanently preserved.
