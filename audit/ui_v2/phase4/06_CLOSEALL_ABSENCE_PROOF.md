# 06 — CLOSEALL ABSENCE PROOF

## 1. Architectural Mandate

In institutional quant trading architecture, emergency close of all open market positions carries extreme slippage and liquidity risk.
Therefore, `CLOSEALL` was intentionally de-scoped and forbidden from client-layer mutation during Phase 4.

## 2. Web V2 Proof

In `web/static/ui_v2/js/risk.js`:
- The Close All action button has no `addEventListener`.
- The element is marked `opacity-40 pointer-events-none cursor-not-allowed`.
- No HTTP requests to `/api/close_all_positions` or execution service close routes are triggered from Web V2 risk actions.

## 3. Flutter iOS V2 Proof

In `ios-app/lib/ui_v2/screens/risk_tab.dart`:
```dart
QuantButton(
  label: 'ĐÓNG TẤT CẢ VỊ THẾ',
  variant: QuantButtonVariant.danger,
  fullWidth: true,
  onPressed: null, // Strictly disabled in Phase 4; zero endpoint wiring
),
```
- `onPressed: null` guarantees the button cannot be activated.
- `QuantApiClient` contains ZERO methods calling close-all endpoints.
- No network requests are dispatched.
