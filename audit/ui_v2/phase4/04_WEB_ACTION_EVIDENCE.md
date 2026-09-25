# 04 — WEB V2 OPERATOR ACTION EVIDENCE

## 1. Web Architecture

- **Templates**: `web/templates/ui_v2/dashboard.html` and `web/templates/ui_v2/partials/telemetry_bar.html`.
- **Scripts**: `web/static/ui_v2/js/risk.js` and `web/static/ui_v2/js/dashboard.js`.

## 2. Web Implementation Details

### HALT Action
- Triggers standard confirmation prompt explaining the system will pause new position entries.
- Checks `isActionInFlight` lock.
- Posts to `/api/pause` with `{ reason: 'Web operator emergency halt', source: 'web' }`.
- On success: updates local state, shows success notification, triggers immediate `fetchStatus()`.
- On failure: unlocks and shows error notification.

### RESUME Action with CAS
- Gated: Button is enabled ONLY if `status.resume_allowed === true` (derived by backend as `is_paused && !recovery_required`).
- Triggers confirmation prompt explicitly displaying current HALT generation:
  `"Xác nhận RESUME từ thế hệ HALT #{haltGen}?"`
- Posts to `/api/resume` with `{ expected_halt_generation: haltGen, source: 'web' }`.
- On 409 Conflict: alerts operator to generation mismatch or recovery block, triggers immediate `fetchStatus()` refresh.
- On success: resets generation, triggers immediate `fetchStatus()`.

### CLOSE ALL Action
- Rendered as disabled: `class="btn btn-secondary opacity-40 pointer-events-none cursor-not-allowed"`
- Label: `[ĐÓNG TẤT CẢ — VÔ HIỆU HÓA]`
- Click handler is completely absent. Zero network traffic produced.
